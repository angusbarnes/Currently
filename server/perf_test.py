from main import evaluate_load_flow_with_known_loads
from network import *
from drivers import database
import itertools
import random
from tqdm import tqdm
import itertools
import random
import csv
import time
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = ["Times New Roman", "serif"]
plt.rcParams["font.size"] = 12

SAMPLES = 100
TOTAL_NODES = 37
LOG_FILE = "experiment_results.csv"

if __name__ == "__main__":

    cable_types = load_cable_types("cables.csv")
    nodes = load_nodes_from_disk("nodes.csv")
    lines = load_lines_from_disk("links.csv")
    net, total_rating = build_network(nodes, lines, cable_types)

    readings = list(
        itertools.islice(
            database.fetch_batches(
                "../sensitive/modbus_data.db", "2023-12-29 04:45:00"
            ),
            100,
        )
    )

    results = []

    with open(LOG_FILE, mode="w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "sample",
                "reading_set",
                "simulated_nodes",
                "real_nodes",
                "exec_time",
            ],
        )
        writer.writeheader()

        # Repeat to reduce random variance
        for i in tqdm(range(SAMPLES)):
            for j, reading_set in enumerate(readings):

                site_totals = reading_set[-1]  # TODO: Make this more resilient

                # Select our random readings
                # This introduces some variance in data consistency which is a worst case scenario
                # for the CPU.
                chosen_readings = random.sample(
                    reading_set[:-1], k=random.randint(1, len(reading_set) - 1)
                )

                real_nodes = len(chosen_readings)
                simulated_nodes = TOTAL_NODES - real_nodes

                start = (
                    time.perf_counter()
                )  # The perf counter provides better consistency for benchmarking
                evaluate_load_flow_with_known_loads(
                    nodes, lines, net, chosen_readings, site_totals, total_rating
                )
                elapsed = time.perf_counter() - start

                clear_network_loads(net)

                row = {
                    "sample": i,
                    "reading_set": j,
                    "simulated_nodes": simulated_nodes,
                    "real_nodes": real_nodes,
                    "exec_time": elapsed,
                }

                writer.writerow(row)
                results.append(row)

    simulated_nodes = [r["simulated_nodes"] for r in results[1:]]
    exec_times = [r["exec_time"] for r in results[1:]]

    plt.figure(figsize=(8, 6))
    plt.scatter(simulated_nodes, exec_times, alpha=0.6, edgecolor="k")
    plt.xlabel("Number of Simulated Nodes")
    plt.ylabel("Execution Time (s)")
    plt.title("Correlation Between Simulated Nodes and Execution Time")
    plt.grid(True)

    if len(simulated_nodes) > 1:
        import numpy as np

        # Perform some basic regression to test for linearity
        # the hope is to see constant time performance (flat line)
        coeffs = np.polyfit(simulated_nodes, exec_times, 1)
        poly = np.poly1d(coeffs)
        xs = np.linspace(min(simulated_nodes), max(simulated_nodes), 100)
        plt.plot(
            xs, poly(xs), "r--", label=f"Trend: y={coeffs[0]:.4f}x+{coeffs[1]:.4f}"
        )
        plt.legend()
        plt.grid(True, linestyle="--", alpha=0.6)

    plt.savefig("graphs/perf_test.png", dpi=300)
