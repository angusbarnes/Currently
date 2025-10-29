import logging
from colorama import Fore, Style, init as colorama_init

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
# The entry point for the Currently Data Server
# We load these dependencies after logging config to ensure uniform log format
from lib.reporting import report_bus_voltages, report_line_loadings
import json
from network import *
from pprint import pprint
from drivers import database
import pandapower as pp
import time
from scipy.io import savemat
import asyncio
import websockets
import tracemalloc
from plugin_host import PluginHost

GLOBAL_SCALING_FACTOR = 5
NETWORK_CONFIGURATION_DIRTY = False


async def stream_modbus_logs(websocket):
    try:
        cable_types = load_cable_types("./data/config/cables.csv")
        nodes = load_nodes_from_disk("./data/config/nodes.csv")
        lines = load_lines_from_disk("./data/config/links.csv")

        net, total_rating = build_network(nodes, lines, cable_types)

        tracemalloc.start()
        snapshot1 = tracemalloc.take_snapshot()
        peaks = []
        try:
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

                exec_time = evaluate_load_flow_with_known_loads(
                    nodes, lines, net, reading_set, site_totals, total_rating
                )

                if exec_time > 0.7:
                    logger.warning(
                        f"Main load flow evaluation time = {Fore.LIGHTRED_EX}{exec_time:.3f}{Fore.RESET} seconds."
                    )
                else:
                    logger.notice(
                        f"Main load flow evaluation time = {exec_time:.3f} seconds."
                    )

                current, peak = tracemalloc.get_traced_memory()
                peaks.append(current)
                if len(peaks) == 100:
                    print(f"Average: {sum(peaks)/100} MB")
                print(
                    f"Memory usage: {current/1024/1024:.1f} MB; Peak: {peak/1024/1024:.1f} MB"
                )

                data = {}

                data["line_data"] = serialise_list(list(lines.values()))
                data["node_data"] = serialise_list(list(nodes.values()))
                data["site_totals"] = site_totals

                packet = json.dumps(data, default=str)
                print(f"Preparing to send a packet with size: {len(packet)/1024:.1f} kB")
                await websocket.send(packet)
                await asyncio.sleep(max(0, 2 - exec_time))

        except websockets.exceptions.ConnectionClosed:
            print("Client disconnected")
        tracemalloc.stop()
    except Exception as e:
        print(e)



def evaluate_load_flow_with_known_loads(
    nodes, lines, net, reading_set, site_totals, total_rating
):
    remaining_rating = total_rating
    loaded_subs = []
    allocated_q = 0
    allocated_p = 0
    for i, reading in enumerate(reading_set):
        # If we have unreliable data we should skip this sub and simulate it instead
        try:
            p = reading["power_active"] / 1000
            q = reading["power_reactive"] / 1000
        except TypeError:
            continue

        NODE = nodes[int(reading["device_name"])]
        NODE.phase_data = [
            reading["voltage_an"],
            reading["voltage_bn"],
            reading["voltage_cn"],
            reading["current_a"],
            reading["current_b"],
            reading["current_c"]
        ]

        loaded_subs.append(int(reading["device_name"]))

        allocated_p += p
        allocated_q += q
        remaining_rating -= NODE.rating
        pp.create_load(
            net,
            NODE.node_object,
            p_mw=p,
            q_mvar=q,
            scaling=GLOBAL_SCALING_FACTOR * NODE.load_scale_factor,
            name=NODE.name,
        )

        NODE.is_online = True

        logger.debug(
            f"Loaded {int(reading['device_name'])} with P={reading['power_active']/1000}, Q={reading['power_reactive']/1000}"
        )

    logger.info(f"Added {i+1} loads from timestamp: {site_totals['timestamp']}")
    logger.debug(f"Loaded: {loaded_subs}")

    remaining_p = (site_totals["ansto_total_kw"] / 1000) - allocated_p
    remaining_q = (site_totals["ansto_total_kvar"] / 1000) - allocated_q
    logger.debug(
        f"Calculating remaining load as: P={remaining_p:.4f} MW, Q={remaining_q:.4f} MVAr"
    )

    simulated_subs = []
    for id, node in nodes.items():
        # We need to create loads for any that do not have readings
        # The act of creating a load should invalidate the online status of a substation
        # We also skip the slack bus
        if id not in loaded_subs and id != 0:
            pp.create_load(
                net,
                node.node_object,
                p_mw=remaining_p * node.rating / remaining_rating,
                q_mvar=remaining_q * node.rating / remaining_rating,
                scaling=GLOBAL_SCALING_FACTOR * node.load_scale_factor,
                name=node.name,
            )
            simulated_subs.append(id)

            node.is_online = False
    logger.info(f"Created {len(simulated_subs)} loads from site-wide scaling.")
    logger.debug(f"Loaded: {simulated_subs}")
    logger.notice(
        f"Processing load flow for timestamp: {Fore.LIGHTGREEN_EX}{site_totals['timestamp']}{Fore.RESET}"
    )
    start = time.time()
    pp.runpp(net)
    stop = time.time()

    update_lines_from_results(lines, net.res_line)
    update_nodes_from_results(nodes, net.res_bus)

    exec_time = stop - start
    return exec_time


async def main():
    host = PluginHost("plugins")
    host.start_watcher()

    server = await websockets.serve(stream_modbus_logs, "127.0.0.1", 8080)
    print("Server started on ws://127.0.0.1:8080")
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
