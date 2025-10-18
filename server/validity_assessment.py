import logging
from colorama import Fore, Style, init as colorama_init
import numpy as np
from network_utils import serialise_list

colorama_init(autoreset=True)


NOTICE_LEVEL_NUM = 25  # Between INFO (20) and WARNING (30)
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
        NOTICE_LEVEL_NUM: Fore.GREEN,
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

logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s]: %(message)s")
logger = logging.getLogger(__name__)

from network import *
from drivers import database
import pandapower as pp
from scipy.io import savemat

GLOBAL_SCALING_FACTOR = 10
NETWORK_CONFIGURATION_DIRTY = False


def test_modbus_logs():
    cable_types = load_cable_types("./data/config/cables.csv")
    nodes = load_nodes_from_disk("./data/config/nodes.csv")
    lines = load_lines_from_disk("./data/config/links.csv")
    net, total_rating = build_network(nodes, lines, cable_types)

    with open("./data/results/validity_results.csv", "w", newline="") as outfile:
        writer = csv.writer(outfile)

        writer.writerow(
            [
                "timestamp",
                "node_name",
                "ref_v",
                "verify_v",
                "simulated_v",
                "ref_i",
                "verify_i",
                "simulated_i",
            ]
        )
        for reading_set in database.fetch_batches(
            "../sensitive/modbus_data.db", "2023-12-29 04:45:00"
        ):

            # If the underlying configuration has changed, rebuild the whole network
            # otherwise used the cached networks structure and simply drop the loads
            if NETWORK_CONFIGURATION_DIRTY:
                net, total_rating = build_network(nodes, lines, cable_types)
            else:
                clear_network_loads(net)

            site_totals = reading_set.pop()  # TODO: Make this more resilient

            # We must ensure to reset network state between simulations
            reference_line, reference_bus = evaluate_load_flow_with_known_loads(
                nodes, lines, net, reading_set, site_totals, total_rating
            )
            clear_network_loads(net)
            verify_line, verify_bus = evaluate_load_flow_with_known_loads(
                nodes, lines, net, reading_set, site_totals, total_rating
            )
            clear_network_loads(net)
            network_sim_line, network_sim_bus = evaluate_load_flow_with_known_loads(
                nodes,
                lines,
                net,
                reading_set,
                site_totals,
                total_rating,
                simulate_network=True,
                batch_allocate=False,
            )

            timestamp = site_totals["timestamp"]

            for bus_idx, ref_row in reference_bus.iterrows():
                node_name = ref_row["bus"] if "bus" in ref_row else bus_idx

                ref_v = ref_row.get("vm_pu", None)
                verify_v = verify_bus.loc[bus_idx].get("vm_pu", None)
                sim_v = network_sim_bus.loc[bus_idx].get("vm_pu", None)

                ref_i = None
                verify_i = None
                sim_i = None
                batch_i = None
                if "from_bus" in reference_line.columns:
                    ref_lines = reference_line[reference_line["from_bus"] == bus_idx]
                    if not ref_lines.empty:
                        ref_i = ref_lines["i_ka"].max()

                    verify_lines = verify_line[verify_line["from_bus"] == bus_idx]
                    if not verify_lines.empty:
                        verify_i = verify_lines["i_ka"].max()

                    sim_lines = network_sim_line[
                        network_sim_line["from_bus"] == bus_idx
                    ]
                    if not sim_lines.empty:
                        sim_i = sim_lines["i_ka"].max()

                writer.writerow(
                    [
                        timestamp,
                        node_name,
                        ref_v,
                        verify_v,
                        sim_v,
                        ref_i,
                        verify_i,
                        sim_i,
                    ]
                )


def evaluate_load_flow_with_known_loads(
    nodes,
    lines,
    net,
    reading_set,
    site_totals,
    total_rating,
    simulate_network=False,
    batch_allocate=False,
):

    remaining_rating = total_rating
    loaded_subs = []
    allocated_q = 0
    allocated_p = 0
    for reading in reading_set:
        node: ActiveNode = nodes[int(reading["device_name"])]

        try:
            p = reading["power_active"] / 1000
            q = reading["power_reactive"] / 1000
        except TypeError:
            continue

        if simulate_network and node.should_drop_current_reading():
            logger.debug(f"DROPPED reading for {node.id}, using predictive model...")

            # Simulate replacing our reading with a prediction as we "lost" this one
            p, q = node.predict_next()

            # Force the naive estimation method
            if batch_allocate:
                p, q = 0, 0

        elif simulate_network:
            # We only both adding "valid" readings if we are in a mode to simulate invalid ones
            node.add_valid_reading(p, q)

        loaded_subs.append(int(reading["device_name"]))

        allocated_p += p
        allocated_q += q
        remaining_rating -= node.rating
        pp.create_load(
            net,
            nodes[int(reading["device_name"])].node_object,
            p_mw=p,
            q_mvar=q,
            scaling=GLOBAL_SCALING_FACTOR,
            name=node.name,
        )

    remaining_p = (site_totals["ansto_total_kw"] / 1000) - allocated_p
    remaining_q = (site_totals["ansto_total_kvar"] / 1000) - allocated_q

    for id, node in nodes.items():
        if id not in loaded_subs and id != 0:
            pp.create_load(
                net,
                node.node_object,
                p_mw=remaining_p * node.rating / remaining_rating,
                q_mvar=remaining_q * node.rating / remaining_rating,
                scaling=GLOBAL_SCALING_FACTOR,
                name=node.name,
            )
    pp.runpp(net)
    return net.res_line, net.res_bus


if __name__ == "__main__":
    test_modbus_logs()
