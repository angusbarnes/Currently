import sqlite3
import pandas as pd
import numpy as np
from envparser import load_env
from utils import mean_median_dev, report_mean_median_dev

def characterise_load(database_path: str, substation_id):

    database_connection = sqlite3.connect(database_path)
    df = pd.read_sql_query(f"SELECT * FROM modbus_logs WHERE device_name = {substation_id}", database_connection)

    df['timestamp'] = pd.to_datetime(df['timestamp'])

    df["load_a"] = np.round((df["voltage_an"] * df["current_a"])/1000, 3)
    df["load_b"] = np.round((df["voltage_bn"] * df["current_b"])/1000, 3)
    df["load_c"] = np.round((df["voltage_cn"] * df["current_c"])/1000, 3)

    df["calc_load"] = df["load_a"] + df["load_b"] + df["load_c"]
    df["delta"] = df["calc_load"] - df["power_apparent"]
    df["err %"] = np.round(df["delta"] / df["power_apparent"] * 100, 1)

    df["load_derived"] = np.sqrt(df["power_active"]**2 + df["power_reactive"]**2)

    print("======================================================================================================")
    print("                                 LOAD CHARACTERISATION REPORT")
    print(f"Substation ID: {substation_id}")
    print(f"Data Points: {len(df)}")
    print(f"Date Range: {np.min(df['timestamp'])} -> {np.max(df['timestamp'])}")
    print("======================================================================================================")
    print(df[["load_a", "load_b", "load_c", "calc_load", "power_active", "power_reactive", "power_apparent", "err %"]])
    print("======================================================================================================")

    spring_filtered = df[df['timestamp'].dt.month.isin([9, 10, 11])]
    summer_filtered = df[df['timestamp'].dt.month.isin([12, 1, 2])]
    winter_filtered = df[df['timestamp'].dt.month.isin([3, 4, 5])]
    autumn_filtered = df[df['timestamp'].dt.month.isin([6, 7, 8])]


    report_mean_median_dev("Active Power", df["power_active"])
    report_mean_median_dev("Reactive Power", df["power_reactive"])
    report_mean_median_dev("Apparent Power", df["power_apparent"])


    report_mean_median_dev("Spring Apparent Power", spring_filtered["power_apparent"])
    report_mean_median_dev("Summer Apparent Power", summer_filtered["power_apparent"])
    report_mean_median_dev("Autumn Apparent Power", autumn_filtered["power_apparent"])
    report_mean_median_dev("Winter Apparent Power", winter_filtered["power_apparent"])

    df['year_month'] = df['timestamp'].dt.to_period('M')

    # Aggregate: sum and mean
    monthly_stats = df.groupby('year_month')['power_apparent'].agg(['sum', 'mean', 'std']).reset_index()

    print(monthly_stats)