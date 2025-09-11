# File to test the accuracy of various load interpolation techniques


import sqlite3
import pandas as pd
import datetime
import random
import math
import csv

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


def process_batch(NETWORK_RELIABILITY_FACTOR, EXPECTED_DELTA, BATCH_LENGTH, data):
    remaining_indexes = len(data)
    current_index = 0

    continuity_errors = 0
    dumped_segment_errors = 0
    batches = 0

    batch_stats = []
    global_predictions = []
      #timestamp, predicted, actual, error
    while remaining_indexes >= BATCH_LENGTH:
        predictions = [] 
        subset = data[current_index:current_index+BATCH_LENGTH]  # Slice is more performant
        current_index += BATCH_LENGTH
        remaining_indexes -= BATCH_LENGTH
        batches += 1

        contiguous = True
        for i in range(1, len(subset)):
            prev_ts = subset[i-1][0]
            curr_ts = subset[i][0]
            if (curr_ts - prev_ts) != EXPECTED_DELTA or math.isnan(subset[i][1]):
                contiguous = False
                continuity_errors += 1

        if not contiguous:
            dumped_segment_errors += 1
            continue

        
        filled_series = [] # Fields: timestamp, reading, is_real
        last_real_index = None

        for i, (timestamp, reading) in enumerate(subset):
            # First reading is never dropped
            if i == 0 or random.random() < NETWORK_RELIABILITY_FACTOR:
                if last_real_index is not None and last_real_index != i - 1:
                    last_timestamp, last_value, _ = filled_series[last_real_index]
                    slope = (reading - last_value) / (i - last_real_index)
                    for j in range(last_real_index + 1, i):
                        ts, _, _ = filled_series[j]
                        filled_series[j] = (ts, filled_series[j - 1][1] + slope, True)

                filled_series.append((timestamp, reading, True))
                last_real_index = i

            elif len(filled_series) < 2:
                fill_in = (timestamp, filled_series[-1][1], False)
                filled_series.append(fill_in)
                predictions.append((timestamp, fill_in[1], reading, abs(reading - fill_in[1])))

            else:
                _, penultimate_reading, _ = filled_series[-2]
                _, ultimate_reading, _ = filled_series[-1]
                slope = ultimate_reading - penultimate_reading  # step size
                estimated_reading = ultimate_reading + slope
                filled_series.append((timestamp, estimated_reading, False))
                predictions.append((timestamp, estimated_reading, reading, abs(reading - estimated_reading)))

        if predictions:
            preds = [pred for (_, pred, _, _) in predictions]
            reals = [real for (_,_, real, _) in predictions]
            errors = [err for (_, _, _, err) in predictions]
            mae = sum(errors) / len(errors)
            rmse = math.sqrt(sum(e**2 for e in errors) / len(errors))
            w_mape = wmape(reals, preds)
            batch_stats.append([len(subset), len(predictions), mae, rmse, w_mape])
            global_predictions.extend(predictions)

    summary_stats = []
    if global_predictions:
        preds = [pred for (_, pred, _, _) in global_predictions]
        reals = [real for (_,_, real, _) in global_predictions]
        errors = [err for (_, _, _, err) in global_predictions]
        mae = sum(errors) / len(errors)
        rmse = math.sqrt(sum(e**2 for e in errors) / len(errors))
        w_mape = wmape(reals, preds)
        summary_stats = [len(reals) + len(preds), len(preds), mae, rmse, w_mape]

    return continuity_errors,dumped_segment_errors, batches,batch_stats, summary_stats

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

    with open(f"global_results.csv", 'w', newline='') as global_results_file:
        global_writer = csv.writer(global_results_file)
        global_writer.writerow(["SUB","BATCH SIZE", "SAMPLES", "PREDICTIONS", "MAE", "RMSE", "WMAPE"])
        for sub in subs_to_test:
            SUBSTATION = sub
            total_row_count = 0
            total_continuity_error = 0
            substastion_stats = []
            data = load_timeseries(SUBSTATION, "power_active", DB_PATH)
            print(f"Loaded {len(data)} data points for substation: {SUBSTATION}")
            for i in [5, 10, 20, 30, 50, 75, 100, 150, 200]:
                BATCH_LENGTH = i

                results_row = [SUBSTATION, BATCH_LENGTH]

                continuity_errors, dumped_segment_errors, batches, batch_stats, summary_stats = process_batch(NETWORK_RELIABILITY_FACTOR, EXPECTED_DELTA, BATCH_LENGTH, data)
                total_row_count += batches * BATCH_LENGTH
                total_continuity_error += continuity_errors
                substastion_stats.extend(batch_stats)
                results_row.extend(summary_stats)
                global_writer.writerow(results_row)

            print(f"Substation reliability is found to be {(1 - total_continuity_error/total_row_count) * 100:.2f}% from {total_row_count} intervals")
            with open(f"{SUBSTATION}_results.csv", 'w', newline='') as results_file:
                writer = csv.writer(results_file)
                writer.writerow(["Subset Length", "Num. Predictions", "MAE", "RMSE", "wMAPE"])
                writer.writerows(substastion_stats)

