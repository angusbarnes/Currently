# File to test the accuracy of various load interpolation techniques
import sqlite3
import pandas as pd
import numpy as np
import datetime
import random
import math
import csv
from tqdm import tqdm
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import acf
from sklearn.linear_model import LinearRegression
import matplotlib.ticker as ticker
import concurrent.futures
import calendar
import numpy as np
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = ["Times New Roman", "serif"]
plt.rcParams["font.size"] = 12

DB_PATH = "../sensitive/modbus_data.db"


def load_timeseries(device_name: str, column: str, db_path: str = DB_PATH, start_date="2022-01-01 00:00:00", end_date="2025-02-25 10:30:00"):
    valid_columns = {
        "id",
        "timestamp",
        "device_name",
        "current_a",
        "current_b",
        "current_c",
        "power_active",
        "power_reactive",
        "power_apparent",
        "power_factor",
        "voltage_an",
        "voltage_bn",
        "voltage_cn",
        "voltage_ab",
        "voltage_bc",
        "voltage_ca",
        "cumulative_active_energy",
    }
    if column not in valid_columns:
        raise ValueError(f"Invalid column name: {column}")

    conn = sqlite3.connect(db_path)
    query = f"""
        SELECT timestamp, {column}
        FROM modbus_logs
        WHERE device_name = ?
        AND timestamp >= ?
        AND timestamp <= ?
        ORDER BY timestamp ASC
    """
    df = pd.read_sql_query(query, conn, params=(device_name,start_date,end_date))
    conn.close()

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    return list(df.itertuples(index=False, name=None))


# Please forgive me programming overlords, for this function is a true
# spaghetti code abomination (As data science code often is)
def analyze_weekly_load(data_tuples, substation):

    df = pd.DataFrame(data_tuples, columns=["timestamp", "load"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    df["load"] = df["load"].interpolate(method="linear")
    df = df.dropna(subset=["load"])

    intervals_per_hour = 4  # 15-minute intervals
    max_lag = 14 * 24 * intervals_per_hour

    acf_vals = acf(df["load"], nlags=max_lag, fft=True)

    # plt.figure(figsize=(12,5))
    fig, ax = plt.subplots(1, 1)
    fig.set_figwidth(12)
    fig.set_figheight(5)
    ax.plot(
        np.arange(max_lag + 1) / intervals_per_hour,
        acf_vals,
        color="0.2",
        linewidth=0.8,
    )
    plt.axvline(24, color="red", linestyle="--", label="1 Day")
    plt.axvline(7 * 24, color="green", linestyle="--", label="7 days")
    plt.xlabel("Lag (hours)")
    plt.ylabel("Autocorrelation")
    plt.title("Autocorrelation of Load")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend()
    loc = ticker.MultipleLocator(base=12)
    ax.xaxis.set_major_locator(loc)
    ax.set_xlim(0, 335)
    plt.savefig(f"graphs/{substation}_acf.png", dpi=300)
    plt.close()
    # plt.show()

    df["day_of_week"] = df["timestamp"].dt.dayofweek  # 0=Monday
    df["time_of_day"] = df["timestamp"].dt.hour + df["timestamp"].dt.minute / 60

    weekly_stats = (
        df.groupby(["day_of_week", "time_of_day"])["load"]
        .agg(
            avg="mean",
            p10=lambda x: np.percentile(x, 10),
            p90=lambda x: np.percentile(x, 90),
        )
        .reset_index()
    )

    # # Plot average weekly profile
    # weekly_stats['avg'].plot(figsize=(12,6))
    # plt.title('Baseline Weekly Profile (Average Load by Day & Time)')
    # plt.xlabel('Day of Week')
    # plt.ylabel('Load')
    # plt.show()

    # Returning function duplicates might get a bit cooked
    # May need to rethink this approach
    def typical_load_for_timestamps(timestamps):
        ts_df = pd.DataFrame({"timestamp": pd.to_datetime(timestamps)})
        ts_df["day_of_week"] = ts_df["timestamp"].dt.dayofweek
        ts_df["time_of_day"] = (
            ts_df["timestamp"].dt.hour + ts_df["timestamp"].dt.minute / 60
        )

        merged = ts_df.merge(
            weekly_stats.reset_index(), how="left", on=["day_of_week", "time_of_day"]
        )

        return merged[["timestamp", "avg", "p10", "p90"]]

    return {
        "df": df,
        "weekly_stats": weekly_stats,
        "typical_load_fn": typical_load_for_timestamps,
        "24h_autocorrelation": acf_vals[24 * 4],
        "7d_autocorrelation": acf_vals[24 * 4 * 7],
    }


# Transformer Rating Allocation
# This is used for completely offline substations
# Low accuracy, kicks in after 96 consecutive outages


# Intermittent Outage Compensation
# Use ML method to fill longer lasting data outages
# After 5 consecutive missing values, use this method
# This will  just repeat a weekly, context invariant prediction
# Use a cyclic mean baseline + time local adjustment


# Direct linear extrapolation with retrospective corrective interpolation
# Short term method
# Where data is patchy, this is likely to be the most accurate method
# Consider last 5 data points, project out to 5 data points


def wMAPE(actual, predicted):
    actual = np.array(actual)
    predicted = np.array(predicted)
    mask = (actual != 0) & (~np.isnan(actual))
    return np.sum(np.abs(actual[mask] - predicted[mask])) / np.sum(np.abs(actual[mask]))


def count_continuity_errors(data, expected_delta):
    continuity_errors = 0
    for i in range(1, len(data)):
        prev_ts = data[i - 1][0]
        curr_ts = data[i][0]
        if (curr_ts - prev_ts) != expected_delta:
            continuity_errors += 1
            print("The forbidden case fired")
        elif math.isnan(data[i][1]) or data[i][1] is None:
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
            window = values[i - n : i]
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
                coeffs = np.polyfit(x, y, 2)
                quad_pred = coeffs[0] * n**2 + coeffs[1] * n + coeffs[2]
                abs_errors_quad.append(abs(actual_next - quad_pred))
                actuals_quad.append(abs(actual_next))

            abs_errors_ma.append(abs(actual_next - ma_pred))
            abs_errors_lin.append(abs(actual_next - lin_pred))
            actuals_ma.append(abs(actual_next))
            actuals_lin.append(abs(actual_next))

        def safe_wmape(errors, actuals):
            return sum(errors) / sum(actuals) if sum(actuals) > 0 else ""

        wMAPE_ma = safe_wmape(abs_errors_ma, actuals_ma)
        wMAPE_lin = safe_wmape(abs_errors_lin, actuals_lin)
        wMAPE_quad = safe_wmape(abs_errors_quad, actuals_quad) if n >= 3 else np.nan

        avg_error_ma = np.mean(abs_errors_ma) if abs_errors_ma else np.nan
        avg_error_lin = np.mean(abs_errors_lin) if abs_errors_lin else np.nan
        avg_error_quad = np.mean(abs_errors_quad) if abs_errors_quad else np.nan

        rows.append(
            [
                n,
                wMAPE_ma,
                wMAPE_lin,
                wMAPE_quad,
                avg_error_ma,
                avg_error_lin,
                avg_error_quad,
            ]
        )

    with open(out_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "n",
                "wMAPE_MA",
                "wMAPE_Lin",
                "wMAPE_Quad",
                "AvgError_MA",
                "AvgError_Lin",
                "AvgError_Quad",
            ]
        )
        writer.writerows(rows)

    return rows


def process_substation(SUBSTATION, DB_PATH, EXPECTED_DELTA):
    data = load_timeseries(SUBSTATION, "power_active", DB_PATH)
    data_points = len(data)
    print(f"Loaded {data_points} data points for substation: {SUBSTATION}")
    continuity_errors = count_continuity_errors(data, EXPECTED_DELTA)

    results = process_batch(
        data, n_values=range(2, 151), out_file=f"{SUBSTATION}_results.csv"
    )

    print(
        f"Substation {SUBSTATION} reliability is found to be "
        f"{(1.0 - continuity_errors/data_points) * 100:.2f}% "
        f"from {data_points} intervals"
    )

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
        writer.writerow(
            [
                "n",
                "wMAPE_MA",
                "wMAPE_Lin",
                "wMAPE_Quad",
                "AvgError_MA",
                "AvgError_Lin",
                "AvgError_Quad",
            ]
        )
        writer.writerows(global_results)


def plot_wmape_from_csv(substation):
    df = pd.read_csv(f"{substation}_results.csv")
    df = df.apply(pd.to_numeric, errors="coerce")
    n_vals = df["n"].values

    series = {
        "Moving Average": df["wMAPE_MA"].values,
        "Linear Extrapolation": df["wMAPE_Lin"].values,
        "Quadratic Extrapolation": df["wMAPE_Quad"].values,
    }

    # Plot the series
    plt.figure(figsize=(10, 6))
    for name, y in series.items():
        plt.plot(n_vals, y, label=name, alpha=0.7)

    # Detect intersections
    methods = list(series.keys())
    for i in range(len(methods)):
        for j in range(i + 1, len(methods)):
            m1, m2 = methods[i], methods[j]
            y1, y2 = series[m1], series[m2]

            diff = y1 - y2
            sign_change = np.where(np.sign(diff[:-1]) != np.sign(diff[1:]))[0]

            for idx in sign_change:
                x0, x1 = n_vals[idx], n_vals[idx + 1]
                y0, y1_diff = diff[idx], diff[idx + 1]
                if y1_diff - y0 != 0:
                    x_cross = x0 - y0 * (x1 - x0) / (y1_diff - y0)
                else:
                    x_cross = x0

                plt.axvline(x_cross, color="gray", linestyle="--", alpha=0.5)
                plt.text(
                    x_cross - 0.5,
                    plt.ylim()[1] * 0.95,
                    f"{x_cross:.1f}",
                    rotation=90,
                    va="top",
                    ha="center",
                    fontsize=9,
                    color="black",
                )

    plt.xlabel("Window size (n)")
    plt.ylabel("wMAPE")
    plt.title(f"wMAPE vs Window Size ({substation})")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(f"graphs/{substation}_extrapolation.png", dpi=300)
    plt.close()


def plot_typical_profile(data, subname, mode="daily"):
    df = pd.DataFrame(data, columns=["timestamp", "load"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp")

    # Remove NaN
    df = df.dropna(subset=["load"])

    if mode == "daily":
        df["time_of_day"] = df.index.hour * 60 + df.index.minute
        grouped = df.groupby("time_of_day")["load"]
        mean_profile = grouped.mean()
        std_profile = grouped.std()

        x = mean_profile.index / 60.0
        xlabel = "Hour of day"
        title = f"Typical Quotidian Load Profile ({subname})"

    elif mode == "weekly":
        df["week_minute"] = (
            df.index.dayofweek * 1440 + df.index.hour * 60 + df.index.minute
        )
        grouped = df.groupby("week_minute")["load"]
        mean_profile = grouped.mean()
        std_profile = grouped.std()

        x = mean_profile.index / 60.0
        xlabel = "Hour of week"
        title = "Typical Hebdomadal Load Profile"

    else:
        raise ValueError("mode must be 'daily' or 'weekly'")

    # Plot
    plt.figure(figsize=(12, 6))
    plt.plot(x, mean_profile, label="Mean load", color="blue")
    plt.fill_between(
        x,
        mean_profile - std_profile,
        mean_profile + std_profile,
        color="blue",
        alpha=0.2,
        label="±1 Std Dev",
    )

    plt.xlabel(xlabel)
    plt.ylabel("Load")
    plt.title(title)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"graphs/{subname}_profile.png", dpi=300)
    plt.close()


def plot_daily_max_by_year(data, sub):
    df = pd.DataFrame(data, columns=["timestamp", "value"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)

    daily_max = df.resample("D").max()

    daily_max["year"] = daily_max.index.year
    daily_max["day_of_year"] = daily_max.index.dayofyear

    pivot = daily_max.pivot(index="day_of_year", columns="year", values="value")

    month_starts = [pd.Timestamp(f"2001-{m:02d}-01").day_of_year for m in range(1, 13)]
    month_labels = [calendar.month_abbr[m] for m in range(1, 13)]

    plt.figure(figsize=(12, 6))
    for year in pivot.columns:
        plt.plot(pivot.index, pivot[year], label=str(year))

    plt.xlabel("Month")
    plt.ylabel("Daily Maximum Demand (MVA)")
    plt.title(f"Daily Maximum Demand by Year ({sub})")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)

    plt.xticks(month_starts, month_labels)

    plt.tight_layout()
    plt.savefig(f"graphs/{sub}_max_demands.png", dpi=300)
    plt.close()


def assess_prediction_accuracy(time_series, typical_load_for_timestamps):
    if not time_series:
        return None

    df_actual = pd.DataFrame(time_series, columns=["timestamp", "actual"])
    df_actual["timestamp"] = pd.to_datetime(df_actual["timestamp"])

    pred_df = typical_load_for_timestamps(df_actual["timestamp"])
    merged = df_actual.merge(pred_df, on="timestamp", how="left")
    error = wMAPE(merged["actual"], merged["avg"])

    return error


def simulate_gilbert_elliot(
    num_steps=7 * 96, p_good_to_bad=0.04, p_bad_to_good=0.3, loss_good=0.1, loss_bad=0.8
):
    rng = np.random.default_rng(42)  # just wanna make the graph the same each run
    states = []
    losses = []

    state = "good"
    for _ in range(num_steps):
        if state == "good":
            lost = rng.random() < loss_good
        else:
            lost = rng.random() < loss_bad
        losses.append(lost)
        states.append(state)

        if state == "good" and rng.random() < p_good_to_bad:
            state = "bad"
        elif state == "bad" and rng.random() < p_bad_to_good:
            state = "good"

    return np.array(states), np.array(losses)


def plot_with_bands(states, losses, readings_per_day=96):
    num_steps = len(states)
    t = np.arange(num_steps) / readings_per_day

    fig, ax = plt.subplots(figsize=(12, 4))

    in_bad = states == "bad"
    start = None
    for i in range(num_steps):
        if in_bad[i] and start is None:
            start = t[i]
        elif not in_bad[i] and start is not None:
            span = ax.axvspan(start, t[i], color="black", alpha=0.6)
            start = None
    if start is not None:  # handle trailing bad patch
        ax.axvspan(start, t[-1], color="black", alpha=0.6)

    # # Plot received/lost readings
    # ax.scatter(t[~losses], np.ones(np.sum(~losses)),
    #            color="green", marker="o", label="Received", s=10)
    # ax.scatter(t[losses], np.ones(np.sum(losses)),
    #            color="red", marker="x", label="Lost", s=20)

    ax.set_ylim(0.5, 1.5)
    ax.set_yticks([])
    ax.set_xlabel("Time (days)")
    ax.set_title("Gilbert-Elliot Simulation with Bad State Bands")
    ax.legend([span], ["Loss"])
    plt.tight_layout()
    plt.savefig(f"graphs/GE_test.png", dpi=300)
    plt.close()


# def specialised_accuracy_testing(subs_to_test, db_path, models, periods_to_test=["day","week","month","year"]):
#     # We want to test the performance of our specialised medium term predictive models
#     results = []
#     for sub in subs_to_test:
#         for model in models:
#             for period in periods_to_test:
#                 # Start date and end date should be between 2023-10-01 00:00:00 and 2024-10-01 00:00:00
#                 training_data = load_timeseries(sub, "apparent_power", db_path, START_DATE, END_DATE)
#                 verification_data = load_timeseries(sub, "apparent_power", db_path, END_DATE, END_DATE + 1 MONTH)

#                 model.train(training_data)
#                 wmape, average_absolute_error = model.test(verification_data)
#                 results.append({
#                     "model": model.name,
#                     "period": period,
#                     "substation": sub
#                     "accuracy": wmape,
#                     "mean_error": average_absolute_error
#                 })

if __name__ == "__main__":

    states, losses = simulate_gilbert_elliot(p_good_to_bad=0.05, p_bad_to_good=0.2, loss_bad=0.9, loss_good=0.01)
    plot_with_bands(states, losses)

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
        # "102901",
        # "102902",
    ]

    # run_all(subs_to_test, DB_PATH, EXPECTED_DELTA)
    for sub in subs_to_test:
        data = load_timeseries(sub, "power_apparent", DB_PATH)

        result = analyze_weekly_load(data, sub)
        if result["7d_autocorrelation"] < 0.6 and result["24h_autocorrelation"] < 0.6:
            print(
                f"Substation {sub} should be classified as having an ACYCLIC load profile = {result['7d_autocorrelation']}, {result['24h_autocorrelation']}"
            )
            plot_typical_profile(data, sub, mode="weekly")
        elif result["7d_autocorrelation"] > result["24h_autocorrelation"]:
            print(
                f"Substation {sub} should be classified as having a HEBDOMADAL load profile = {result['7d_autocorrelation']}"
            )
            plot_typical_profile(data, sub, mode="daily")
        else:
            print(
                f"Substation {sub} should be classified as having a QUOTIDIAN load profile = {result['24h_autocorrelation']}"
            )
            plot_typical_profile(data, sub, mode="daily")

        print(
            f"Substation {sub} typical function error: {assess_prediction_accuracy(data, result['typical_load_fn'])}"
        )
        plot_daily_max_by_year(data, sub)

        plot_wmape_from_csv(sub)
