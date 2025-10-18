import sqlite3
import pandas as pd
import os
import numpy as np
from .utils import report_mean_median_dev
from .report_generation import export_excel_report


class CharacterisedLoad:

    def __init__(self, substation_id: str):
        self.substation_id = substation_id

    def set_main_dataframe(self, frame: pd.DataFrame):
        self.frame = frame

    def get_main_dataframe(self):
        return self.frame

    def get_number_of_data_points(self):
        return len(self.frame)

    # Get the max demands without including the 99th percentile results
    # this removed the chance for outliers from creating inaccurate forecasts.
    # We also return the timestamps for use with the load characteriser
    def get_max_demands(self):
        df = self.frame
        apparent = df["power_apparent"].dropna()

        apparent_thresh = np.percentile(apparent, 99)

        filtered = df[(df["power_apparent"] <= apparent_thresh)]

        active_row = filtered.loc[filtered["power_active"].abs().idxmax()]
        reactive_row = filtered.loc[filtered["power_reactive"].abs().idxmax()]
        apparent_row = filtered.loc[filtered["power_apparent"].abs().idxmax()]

        return {
            "max_active": active_row["power_active"],
            "active_timestamp": active_row["timestamp"],
            "max_apparent": (
                apparent_row["power_active"],
                apparent_row["power_reactive"],
            ),
            "apparent_timestamp": apparent_row["timestamp"],
            "max_reactive": reactive_row["power_reactive"],
            "reactive_timestamp": reactive_row["timestamp"],
        }

    def get_absolute_maximums(self):
        return (
            np.max(self.frame["power_active"]),
            np.max(self.frame["power_reactive"]),
        )

    def get_seasonal_stats(self):
        spring_filtered = self.frame[self.frame["timestamp"].dt.month.isin([9, 10, 11])]
        summer_filtered = self.frame[self.frame["timestamp"].dt.month.isin([12, 1, 2])]
        winter_filtered = self.frame[self.frame["timestamp"].dt.month.isin([3, 4, 5])]
        autumn_filtered = self.frame[self.frame["timestamp"].dt.month.isin([6, 7, 8])]

        return {
            "Spring": report_mean_median_dev(spring_filtered["power_apparent"]),
            "Summer": report_mean_median_dev(summer_filtered["power_apparent"]),
            "Autumn": report_mean_median_dev(autumn_filtered["power_apparent"]),
            "Winter": report_mean_median_dev(winter_filtered["power_apparent"]),
        }

    def get_monthly_stats(self):
        return (
            self.frame.groupby("year_month")
            .agg(
                power_apparent_mean=("power_apparent", "mean"),
                power_active_mean=("power_active", "mean"),
                power_reactive_mean=("power_reactive", "mean"),
                total_energy_delivered=(
                    "cumulative_active_energy",
                    lambda x: np.max(x) - np.min(x),
                ),
                voltage_ab_mean=("voltage_ab", "mean"),
                voltage_ab_std=("voltage_ab", "std"),
                voltage_ab_max=("voltage_ab", "max"),
                voltage_bc_mean=("voltage_bc", "mean"),
                voltage_bc_std=("voltage_bc", "std"),
                voltage_bc_max=("voltage_bc", "max"),
                voltage_ca_mean=("voltage_ca", "mean"),
                voltage_ca_std=("voltage_ca", "std"),
                voltage_ca_max=("voltage_ca", "max"),
                current_a_mean=("current_a", "mean"),
                current_a_std=("current_a", "std"),
                current_a_max=("current_a", "max"),
                current_a_p99=("current_a", lambda x: x.quantile(0.99)),
                current_b_mean=("current_b", "mean"),
                current_b_std=("current_b", "std"),
                current_b_max=("current_a", "max"),
                current_b_p99=("current_b", lambda x: x.quantile(0.99)),
                current_c_mean=("current_c", "mean"),
                current_c_std=("current_c", "std"),
                current_c_max=("current_a", "max"),
                current_c_p99=("current_c", lambda x: x.quantile(0.99)),
            )
            .reset_index()
        )

    def get_date_range(self) -> tuple[str, str]:
        return (np.min(self.frame["timestamp"]), np.max(self.frame["timestamp"]))

    def get_average_loads(self):
        pload = np.nanmean(self.frame["power_active"])
        qload = np.nanmean(self.frame["power_reactive"])

        return pload, qload


def characterise_load(database_path: str, substation_id: str):

    load = CharacterisedLoad(substation_id)

    database_connection = sqlite3.connect(database_path)
    df = pd.read_sql_query(
        f'SELECT * FROM modbus_logs WHERE device_name = {substation_id} AND timestamp < "2024-12-01 00:00:00"',
        database_connection,
    )

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    df["load_a"] = np.round((df["voltage_an"] * df["current_a"]) / 1000, 3)
    df["load_b"] = np.round((df["voltage_bn"] * df["current_b"]) / 1000, 3)
    df["load_c"] = np.round((df["voltage_cn"] * df["current_c"]) / 1000, 3)

    def phase_imbalance(row):
        phases = [row["current_a"], row["current_b"], row["current_c"]]
        avg = sum(phases) / 3

        if avg == 0:
            return 0

        return (max(phases) - avg) / avg * 100

    # From NEMA: imbalance = (max(phase_currents) - avg(phase_currents)) / avg(phase_currents) * 100
    df["imbalance"] = df.apply(phase_imbalance, axis=1)

    df["calc_load"] = df["load_a"] + df["load_b"] + df["load_c"]
    df["delta"] = df["calc_load"] - df["power_apparent"]
    df["err %"] = np.round(df["delta"] / df["power_apparent"] * 100, 1)

    df["load_derived"] = np.sqrt(df["power_active"] ** 2 + df["power_reactive"] ** 2)

    df["year_month"] = df["timestamp"].dt.to_period("M")

    load.set_main_dataframe(df)

    return load


def create_load_report(load_data: CharacterisedLoad):

    p90_abs_active = load_data.get_main_dataframe()["power_active"].abs().quantile(0.90)

    row_90th_active = load_data.get_main_dataframe().loc[
        (load_data.get_main_dataframe()["power_active"].abs() - p90_abs_active)
        .abs()
        .idxmin()
    ]

    p90_abs_reactive = (
        load_data.get_main_dataframe()["power_reactive"].abs().quantile(0.90)
    )

    row_90th_reactive = load_data.get_main_dataframe().loc[
        (load_data.get_main_dataframe()["power_reactive"].abs() - p90_abs_reactive)
        .abs()
        .idxmin()
    ]

    os.makedirs("./out/data", exist_ok=True)

    pload, qload = load_data.get_average_loads()

    export_excel_report(
        {
            "substation_id": load_data.substation_id,
            "start_date": load_data.get_date_range()[0],
            "end_date": load_data.get_date_range()[1],
            "data_points": load_data.get_number_of_data_points(),
            "monthly_stats": load_data.get_monthly_stats(),
            "imbalance": np.round(
                np.mean(load_data.get_main_dataframe()["imbalance"]), 2
            ),
            "energy": np.round(
                max(load_data.get_main_dataframe()["cumulative_active_energy"])
            ),
            "pload": pload,
            "qload": qload,
            "90pload": row_90th_active["power_active"],
            "90qload": row_90th_reactive["power_reactive"],
        },
        output_path=f"out/data/{load_data.substation_id}_load_summary.xlsx",
    )

    return pload, qload
