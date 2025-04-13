import sqlite3
import pandas as pd
import numpy as np
from io import StringIO
from envparser import load_env
from utils import mean_median_dev, report_mean_median_dev
from report_generation import PDFReport, plot_monthly_apparent_power, plot_seasonal_bar

class CharacterisedLoad:
    
    def __init__(self, substation_id: str):
        self.substation_id = substation_id

    def set_main_dataframe(self, frame: pd.DataFrame):
        self.frame = frame

    def get_main_dataframe(self):
        return self.frame

    def get_seasonal_stats(self):
        spring_filtered = self.frame[self.frame['timestamp'].dt.month.isin([9, 10, 11])]
        summer_filtered = self.frame[self.frame['timestamp'].dt.month.isin([12, 1, 2])]
        winter_filtered = self.frame[self.frame['timestamp'].dt.month.isin([3, 4, 5])]
        autumn_filtered = self.frame[self.frame['timestamp'].dt.month.isin([6, 7, 8])]

        return {
            "Spring": report_mean_median_dev(spring_filtered["power_apparent"]),
            "Summer": report_mean_median_dev(summer_filtered["power_apparent"]),
            "Autumn": report_mean_median_dev(autumn_filtered["power_apparent"]),
            "Winter": report_mean_median_dev(winter_filtered["power_apparent"])
        }

    def get_monthly_stats(self):
        return self.frame.groupby('year_month')['power_apparent'].agg(['sum', 'mean', 'std']).reset_index()
    
    def get_date_range(self) -> tuple[str, str]:
        return (np.min(self.frame['timestamp']), np.max(self.frame['timestamp']))

def characterise_load(database_path: str, substation_id: str):

    load = CharacterisedLoad(substation_id)

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

    df['year_month'] = df['timestamp'].dt.to_period('M')

    load.set_main_dataframe(df)

    # str_print("======================================================================================================")
    # str_print("                                 LOAD CHARACTERISATION REPORT")
    # str_print(f"Substation ID: {substation_id}")
    # str_print(f"Data Points: {len(df)}")
    # str_print(f"Date Range: {np.min(df['timestamp'])} -> {np.max(df['timestamp'])}")
    # str_print("======================================================================================================")
    # str_print(df[["load_a", "load_b", "load_c", "calc_load", "power_active", "power_reactive", "power_apparent", "err %"]])
    # str_print("======================================================================================================")

    # report_mean_median_dev("Active Power", df["power_active"])
    # report_mean_median_dev("Reactive Power", df["power_reactive"])
    # report_mean_median_dev("Apparent Power", df["power_apparent"])

    return load


def create_load_report(load_data: CharacterisedLoad):
    pdf = PDFReport()
    pdf.add_page()

    # Report Header
    pdf.set_font("Arial", "", 10)
    pdf.cell(None, 10, f"Substation ID: {load_data.substation_id}", ln=1)
    pdf.cell(None, 10, f"Data Points: {len(load_data.get_main_dataframe())}", ln=1)
    dates = load_data.get_date_range()
    pdf.cell(None, 10, f"Date Range: {dates[0]} -> {dates[1]}", ln=1)

    # Seasonal Summary
    pdf.chapter_title("Summary of Seasonal Apparent Power")
    for season, stats in load_data.get_seasonal_stats().items():
        line = f"{season}: Mean = {stats['Mean']}, Median = {stats['Median']}, Stddev = {stats['Stddev']}"
        pdf.chapter_text(line)

    # Monthly Chart
    pdf.chapter_title("Monthly Mean Apparent Power")
    chart1 = plot_monthly_apparent_power(load_data.get_monthly_stats())
    pdf.insert_image(chart1)

    # Seasonal Chart
    pdf.chapter_title("Seasonal Mean Apparent Power")
    chart2 = plot_seasonal_bar(load_data.get_seasonal_stats())
    pdf.insert_image(chart2)

    # Save PDF
    pdf.output(f"{load_data.substation_id}_load_characterisation_report.pdf")