import logging
from colorama import Fore, Style, init as colorama_init
colorama_init(autoreset=True)


NOTICE_LEVEL_NUM = 25 # Between INFO (20) and WARNING (30)
logging.addLevelName(NOTICE_LEVEL_NUM, "NOTICE")

def notice(self, message, *args, **kwargs):
    if self.isEnabledFor(NOTICE_LEVEL_NUM):
        self._log(NOTICE_LEVEL_NUM, message, args, **kwargs)

logging.Logger.notice = notice 

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.INFO: Fore.CYAN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
        logging.DEBUG: Fore.GREEN,
        NOTICE_LEVEL_NUM: Fore.GREEN
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

logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s]: %(message)s')
logger = logging.getLogger(__name__)

# The entry point for the Currently Data Server
# We load these dependencies after logging config to ensure uniform log format
from lib.reporting import report_bus_voltages, report_line_loadings
from network import *
from pprint import pprint
from drivers import database
import pandapower as pp
import time
from scipy.io import savemat

GLOBAL_SCALING_FACTOR = 1
NETWORK_CONFIGURATION_DIRTY = False

cable_types = load_cable_types("cables.csv")
nodes = load_nodes_from_disk("nodes.csv")
lines = load_lines_from_disk("links.csv")
pprint(lines)
net, total_rating = build_network(nodes, lines, cable_types)
logger.notice(net)

for reading_set in database.fetch_batches("../sensitive/modbus_data.db", "2023-12-29 04:45:00"):

    # If the underlying configuration has changed, rebuild the whole network
    # otherwise used the cached networks structure and simply drop the loads
    if NETWORK_CONFIGURATION_DIRTY:
        net, total_rating = build_network(nodes, lines, cable_types)
    else:
        clear_network_loads(net)

    site_totals = reading_set.pop() #TODO: Make this more resilient


    loaded_subs = []
    allocated_q = 0
    allocated_p = 0
    for i, reading in enumerate(reading_set):
        # If we have unreliable data we should skip this sub and simulate it instead
        try:
            p = reading["power_active"]/1000
            q = reading["power_reactive"]/1000
        except TypeError:
            continue

        loaded_subs.append(int(reading["device_name"]))

        allocated_p += p
        allocated_q += q
        pp.create_load(
            net, 
            nodes[int(reading["device_name"])].node_object, 
            p_mw=p, 
            q_mvar=q, 
            scaling=GLOBAL_SCALING_FACTOR,
            name=nodes[int(reading["device_name"])].name
        )

        logger.debug(f"Loaded {int(reading['device_name'])} with P={reading['power_active']/1000}, Q={reading['power_reactive']/1000}")

    logger.info(f"Added {i+1} loads from timestamp: {site_totals['timestamp']}")
    logger.debug(f"Loaded: {loaded_subs}")

    remaining_p = (site_totals['ansto_total_kw']/1000) - allocated_p
    remaining_q = (site_totals['ansto_total_kvar']/1000) - allocated_q
    logger.debug(f"Calculating remaining load as: P={remaining_p:.4f} MW, Q={remaining_q:.4f} MVAr")


    simulated_subs = []
    for id, node in nodes.items():
        # We need to create loads for any that do not have readings
        # The act of creating a load should invalidate the online status of a substation
        # We also skip the slack bus
        if id not in loaded_subs or id == 0:
            pp.create_load(
                net, 
                node.node_object, 
                p_mw= remaining_q * node.rating/total_rating, 
                q_mvar=q, 
                scaling=GLOBAL_SCALING_FACTOR,
                name=node.name
            )
            simulated_subs.append(id)
    logger.info(f"Created {len(simulated_subs)} loads from site-wide scaling.")
    logger.debug(f"Loaded: {simulated_subs}")
    logger.notice(f"Processing load flow for timestamp: {Fore.LIGHTGREEN_EX}{site_totals['timestamp']}{Fore.RESET}")
    start = time.time()
    pp.runpp(net)
    stop = time.time()


    update_lines_from_results(lines, net.res_line)
    update_nodes_from_results(nodes, net.res_bus)

    exec_time = stop - start

    if exec_time > 0.7:
        logger.warning(f"Main load flow evaluation time = {Fore.LIGHTRED_EX}{exec_time:.3f}{Fore.RESET} seconds.")
    else:
        logger.notice(f"Main load flow evaluation time = {exec_time:.3f} seconds.")
    # report_bus_voltages(net, 3)
    # report_line_loadings(net, 3)

    time.sleep(5 - exec_time)