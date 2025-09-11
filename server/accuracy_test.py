# File to test the accuracy of various load interpolation techniques
import sqlite3
import pandas as pd
import numpy as np
import datetime
import random
import math
import csv
from tqdm import tqdm

DB_PATH = "../sensitive/modbus_data.db"

def load_timeseries(device_name: str, column: str, db_path: str = DB_PATH):
    valid_columns = {
        "id","timestamp","device_name","current_a","current_b","current_c",
        "power_active","power_reactive","power_apparent","power_factor",
        "voltage_an","voltage_bn","voltage_cn","voltage_ab","voltage_bc",
        "voltage_ca","cumulative_active_energy"
    }
    if column not in valid_columns:
        raise ValueError(f"Invalid column name: {column}")

    conn = sqlite3.connect(db_path)
    query = f"""
        SELECT timestamp, {column}
        FROM modbus_logs
        WHERE device_name = ?
        ORDER BY timestamp ASC
    """
    df = pd.read_sql_query(query, conn, params=(device_name,))
    conn.close()

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    return list(df.itertuples(index=False, name=None))



# Transformer Rating Allocation
# This is used for completely offline substations
# Low accuracy, kicks in after 96 consecutive outages


# Intermittent Outage Compensation
# Use ML method to fill longer lasting data outages
# After 5 consecutive missing values, use this method
# This will  just repeat a weekly, context invariant prediction



# Direct linear extrapolation with retrospective corrective interpolation
# Short term method
# Where data is patchy, this is likely to be the most accurate method
# Consider last 5 data points, project out to 5 data points


def wmape(actual, predicted):
    if len(actual) != len(predicted):
        raise ValueError("Actual and predicted must have the same length")

    total_abs_error = sum(abs(a - p) for a, p in zip(actual, predicted))
    total_actual = sum(abs(a) for a in actual)

    if total_actual == 0:
        return float("nan") 

    return (total_abs_error / total_actual) * 100

def count_continuity_errors(data, expected_delta):
    continuity_errors = 0
    for i in range(1, len(data)):
        prev_ts = data[i-1][0]
        curr_ts = data[i][0]
        if (curr_ts - prev_ts) != expected_delta or math.isnan(data[i][1]):
            continuity_errors += 1

    return continuity_errors


def process_batch(data, n_values=(3, 5, 10), out_file="results_summary.csv"):
    values = [v for _, v in data if not math.isnan(v)]

    rows = []

    for n in n_values:
        abs_errors_ma = []
        actuals_ma = []

        abs_errors_lin = []
        actuals_lin = []

        abs_errors_quad = []
        actuals_quad = []

        for i in range(n, len(values) - 1):
            window = values[i-n:i]
            actual_next = values[i]

            # Moving average prediction
            ma_pred = np.mean(window)

            # Linear prediction
            x = np.arange(n)
            y = np.array(window)
            b, a = np.polyfit(x, y, 1)
            lin_pred = a + b * n

            # Quadratic prediction
            if n >= 3:
                coeffs = np.polyfit(x, y, 2)  # coeffs = [c2, c1, c0]
                quad_pred = coeffs[0]*n**2 + coeffs[1]*n + coeffs[2]
                abs_errors_quad.append(abs(actual_next - quad_pred))
                actuals_quad.append(abs(actual_next))

            abs_errors_ma.append(abs(actual_next - ma_pred))
            abs_errors_lin.append(abs(actual_next - lin_pred))
            actuals_ma.append(abs(actual_next))
            actuals_lin.append(abs(actual_next))

        def safe_wmape(errors, actuals):
            return sum(errors) / sum(actuals) if sum(actuals) > 0 else np.nan

        wMAPE_ma = safe_wmape(abs_errors_ma, actuals_ma)
        wMAPE_lin = safe_wmape(abs_errors_lin, actuals_lin)
        wMAPE_quad = safe_wmape(abs_errors_quad, actuals_quad) if n >= 3 else np.nan

        avg_error_ma = np.mean(abs_errors_ma) if abs_errors_ma else np.nan
        avg_error_lin = np.mean(abs_errors_lin) if abs_errors_lin else np.nan
        avg_error_quad = np.mean(abs_errors_quad) if abs_errors_quad else np.nan

        rows.append([
            n,
            wMAPE_ma, wMAPE_lin, wMAPE_quad,
            avg_error_ma, avg_error_lin, avg_error_quad
        ])

    with open(out_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "n", 
            "wMAPE_MA", "wMAPE_Lin", "wMAPE_Quad",
            "AvgError_MA", "AvgError_Lin", "AvgError_Quad"
        ])
        writer.writerows(rows)

    return rows

import concurrent.futures

def process_substation(SUBSTATION, DB_PATH, EXPECTED_DELTA):
    data = load_timeseries(SUBSTATION, "power_active", DB_PATH)
    data_points = len(data)
    print(f"Loaded {data_points} data points for substation: {SUBSTATION}")
    continuity_errors = count_continuity_errors(data, EXPECTED_DELTA)

    results = process_batch(
        data,
        n_values=range(2, 151),
        out_file=f"{SUBSTATION}_results.csv"
    )

    print(f"Substation reliability is found to be "
          f"{(1.0 - continuity_errors/data_points) * 100:.2f}% "
          f"from {data_points} intervals")

    return results

def run_all(subs_to_test, DB_PATH, EXPECTED_DELTA):
    global_results = []

    # We must use the ProcessPool executor as it gets us around the pesky GIL
    # Launch new process per substations.
    # I think this is ok because in theory all these operations should be entirely independent
    # FUTURE REFERENCE: https://docs.python.org/3/library/concurrent.futures.html
    # https://www.geeksforgeeks.org/python/processpoolexecutor-class-in-python/
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = {
            executor.submit(process_substation, sub, DB_PATH, EXPECTED_DELTA): sub
            for sub in subs_to_test
        }

        for future in concurrent.futures.as_completed(futures):
            substation = futures[future]
            try:
                results = future.result()
                global_results.extend(results)
            except Exception as e:
                print(f"Substation {substation} failed: {e}")

    with open("global_results.csv", "w", newline="") as results_file:
        writer = csv.writer(results_file)
        writer.writerow([
            "n",
            "wMAPE_MA", "wMAPE_Lin", "wMAPE_Quad",
            "AvgError_MA", "AvgError_Lin", "AvgError_Quad"
        ])
        writer.writerows(global_results)

if __name__ == "__main__":

    # Every sample has a chance of being dropped or lost in the network
    ## WE ONLY TRACK A SHORT TERM CONTEXT WINDOW SO WE ARE ONLY TESTING ON SHORT DISCRETE WINDOWS
    NETWORK_RELIABILITY_FACTOR = 0.80
    EXPECTED_DELTA = datetime.timedelta(minutes=15)
    subs_to_test = [
        "100800", 
        "100900", 
        "101000", 
        "101500", 
        "101700", 
        "101800", 
        "101901", 
        "101902",
        "102000", 
        "102101", 
        "102102", 
        "102300", 
        "102701", 
        "102702", 
        "102901", 
        "102902"
    ]
    run_all(subs_to_test, DB_PATH, EXPECTED_DELTA)

