import logging
from colorama import Fore, Style, init as colorama_init
colorama_init(autoreset=True)

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.INFO: Fore.CYAN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
        logging.DEBUG: Fore.GREEN,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
        record.levelname = levelname
        return super().format(record)

def setup_colored_logging(level=logging.INFO):
    handler = logging.StreamHandler()
    formatter = ColorFormatter("[%(levelname)s]: %(message)s")
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(level)
    logger.handlers.clear()
    logger.addHandler(handler)

setup_colored_logging()

import csv
import pandapower as pp
from typing import Optional

import pandas as pd
from server.lib.data_types import FeederDefinition
from server.lib.data_types import BusNode
from server.lib.display import run_visualization
from server.lib.utils import string_to_bool, safe_str_to_float, resolve_relative_path_from_config
from server.lib.config import CONFIG
from load_classifier import get_characterised_loads
import time
from server.lib.reporting import report_loading_conditions, report_bus_voltages, report_line_loadings

#TODO: Implement this feature correctly
# lib.config.SetPathParamResolvers(
#     {
#         "cable-file": '__FILE__',
#         "network-file": '__FILE__'
#     }
# )

logging.basicConfig(level=logging.INFO, format='[%(levelname)s]: %(message)s')
logging.debug(f"Final Config: {CONFIG}")

loading_percents, site_maximums = get_characterised_loads()

cable_file = resolve_relative_path_from_config(CONFIG["cable-file"], "./config/base_scenario.toml")
custom_line_types = []
with open(cable_file, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        custom_line_types.append(row)

net = pp.create_empty_network()

known_cables = []

for cable in custom_line_types:
    try:
        pp.create_std_type(net, {
            "c_nf_per_km": float(cable["C (nF/km)"]),
            "r_ohm_per_km": float(cable["R (Ohm/km)"]),
            "x_ohm_per_km": float(cable["X (j Ohm/km)"]),
            "max_i_ka": float(cable["Max I (kA)"]),
            "type": "cs",
            "q_mm2": float(cable["Q (mm2)"]),
            "alpha": float(cable["Alpha"])
        }, name=cable["Cable Name"], element="line")
        known_cables.append(cable["Cable Name"])
    except Exception as e:
        logging.warning(f"Could not register cable type '{cable['Cable Name']}': {e}")

logging.info(f"{len(known_cables)} cable types registered successfully.")

# Load CSV
bus_nodes: dict[str, BusNode] = {}

accounted_p_kw = 0
accounted_q_kvar = 0

cumulative_rating = 0

with open(resolve_relative_path_from_config(CONFIG["network-file"], "./config/base_scenario.toml"), newline='') as csvfile:
    reader = csv.reader(csvfile)
    next(reader)  # Skip header
    

    for bus, feeder, feeder_length, feeder_type, rating, substation_key, active, p, q, _ in reader:
        feeder_def = FeederDefinition(
            feeder_bus=feeder,
            feeder_length=float(feeder_length) / 1000,
            feeder_type=feeder_type,
            active=string_to_bool(active)
        )

        if CONFIG["force-active"]:
            feeder_def.active = True
        
        _p = safe_str_to_float(p)
        _q = safe_str_to_float(q)
        _characterised = False

        # We must have both values defined for it to be valid
        assert (not _p) == (not _q)

        if bus not in bus_nodes:

            # We only use loads for the first definition of a bus
            if not substation_key:
                cumulative_rating += safe_str_to_float(rating)
            else:

                if substation_key not in loading_percents:
                    logging.error(f"Unknown substation key provided for {bus}. DATA_LINK_KEY={substation_key}. Defaulting to defined P,Q load from file.")
                else:
                    if CONFIG["use-traditional"]:
                        _p = loading_percents[substation_key][2]
                        _q = loading_percents[substation_key][3]
                    else:
                        _p = site_maximums[0] * loading_percents[substation_key][0]
                        _q = site_maximums[1] * loading_percents[substation_key][1]
                    logging.info(f"Linked {bus} with load characterisation. DATA_LINK_KEY={substation_key}. Characterised load: P={site_maximums[0] * loading_percents[substation_key][0]/1000:.5f} kW, Q={site_maximums[1] * loading_percents[substation_key][1]/1000:.5f} kVAr")
                    accounted_p_kw += _p
                    accounted_q_kvar += _q
                    _characterised = True


            bus_nodes[bus] = BusNode(
                name=bus,
                rating=safe_str_to_float(rating),
                substation=substation_key,
                characterised_load_kw=_p,
                characterised_load_kvar=_q,
                characterised=_characterised
            )

        bus_nodes[bus].feeders.append(feeder_def)

logging.info(f"{len(bus_nodes)} unique buses loaded from network definition.")

# Create pandapower bus for each node
for i, node in enumerate(bus_nodes.values()):
    node.pp_bus = pp.create_bus(net, vn_kv=11.0, name=node.name, index=i+1)

if "slack" not in bus_nodes:
    slack_node = BusNode("slack", rating=0.0, substation="slack")
    slack_node.pp_bus = pp.create_bus(net, vn_kv=11.0, name="slack", index=0)
    pp.create_ext_grid(net, bus=slack_node.pp_bus)
    bus_nodes["slack"] = slack_node
    logging.info("Slack bus created and set as external grid.")
else:
    pp.create_ext_grid(net, bus=bus_nodes["slack"].pp_bus)
    logging.info("Slack bus already defined and set as external grid.")

lines_created = 0
loads_created = 0

# Fallback to worst case cable for conservative results
fallback_cable = "3C_70mm2_PILC_SWA"

unaccounted_load_kw = site_maximums[0] - accounted_p_kw
unaccounted_load_kvar = site_maximums[1] - accounted_q_kvar

for node in bus_nodes.values():
    for feeder in node.feeders:
        if feeder.feeder_bus not in bus_nodes:
            raise Exception(f"Feeder bus '{feeder.feeder_bus}' not defined for bus '{node.name}'")
        feeder_node = bus_nodes[feeder.feeder_bus]

        line_type = feeder.feeder_type if feeder.feeder_type in known_cables else fallback_cable
        if feeder.feeder_type not in known_cables:
            logging.warning(f"Feeder type '{feeder.feeder_type}' not found. Using fallback '{fallback_cable}'.")


        # We should only modify the pp model if the feeder is involved in this simulation
        # TODO: Change this to use inbuilt pandapower features for this
        if feeder.active:
            pp.create_line(
                net,
                from_bus=feeder_node.pp_bus,
                to_bus=node.pp_bus,
                length_km=feeder.feeder_length,
                std_type=line_type,
                name=f"FROM: {feeder_node.name}, TO: {node.name}"
            )
        lines_created += 1
        feeder_node.add_child(node)

    # We do not attach loads directly to slack
    if node.name == "slack": continue

    if node.rating > 0:

        if node.characterised:
            #pp.create_load(net, name=node.name, bus=node.pp_bus, p_mw=node.characterised_load_kw/1000, q_mvar=node.characterised_load_kvar/1000)
            pp.create_load(net, name=node.name, bus=node.pp_bus, p_mw=0.2, q_mvar=0.2)
        else:
            pass
            #pp.create_load(net, name=node.name, bus=node.pp_bus, p_mw=unaccounted_load_kw/1000 * node.rating/cumulative_rating, q_mvar=unaccounted_load_kvar/1000 * node.rating/cumulative_rating)
        loads_created += 1
    else:
        raise Exception(f"Undefined transformer rating for: {node.name}")

tree_elements = {name: node for name, node in bus_nodes.items()}

logging.info(f"{lines_created} lines and {loads_created} loads added to the network.")

logging.info(net)

print(net.line)

start = time.time()
pp.runpp(net)
stop = time.time()

report_loading_conditions(site_maximums, loading_percents)
report_bus_voltages(net, 3)
report_line_loadings(net, 3)


bus_results = net.res_bus.copy()
bus_results["bus_name"] = net.bus["name"]
bus_results["voltage"] = bus_results["vm_pu"] * CONFIG["target-voltage"]
bus_results["drop"] = CONFIG["target-voltage"] - bus_results["voltage"]

line_results: pd.DataFrame = net.res_line.copy()
line_results["line_name"] = net.line["name"]
line_results["from_bus_name"] = net.line["from_bus"].map(net.bus["name"])
line_results["to_bus_name"] = net.line["to_bus"].map(net.bus["name"])

line_results.to_csv('out/line_results.csv')
bus_results.to_csv('out/bus_results.csv')

from scipy.io import savemat

# Convert pandapower net to MATPOWER case
mpc = pp.converter.to_mpc(net)

# Save as .mat file compatible with MATPOWER
savemat("out/matpower_case.mat", {"mpc": mpc})

if CONFIG["show"]:
    run_visualization(tree_elements['slack'])

print(f"Main load flow evaluation time = {stop-start:.3f} seconds.")