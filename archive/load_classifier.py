from server.lib.envparser import load_env
import pandas as pd
import numpy as np
from tqdm import tqdm
import logging
from server.lib.load_characterisation import characterise_load

def lookup_or_next_closest(time_sorted_df, target_timestamp, timestamp_col="timestamp"):
    idx = time_sorted_df[time_sorted_df[timestamp_col] >= target_timestamp].index
    
    if len(idx) > 0:
        return time_sorted_df.loc[idx[0]]
    else:
        # If target is beyond all values, return the last row
        return time_sorted_df.iloc[-1]


#TODO: Abstract this more correctly for main file orchestration
def get_characterised_loads():
    ENV = load_env()

    site_data = pd.read_csv("./sensitive/site_totals.csv", parse_dates=["timestamp"], dayfirst=True)
    site_data_sorted = site_data.sort_values("timestamp").reset_index(drop=True)

    IDS = []
    with open('substation_ids.txt', 'r') as id_file:
        IDS = map(lambda x: x.strip(), id_file.readlines())

    IDS = list(IDS)

    results = {}

    pload_total, qload_total = 0, 0
    for id in IDS:
        load = characterise_load(ENV['DATABASE_PATH'], id)
        pload, qload = load.get_average_loads()

        pload_total += pload
        qload_total += qload

        demands = load.get_max_demands()
        max_p, max_q = load.get_absolute_maximums()

        corresponding_site_apparent_load = lookup_or_next_closest(site_data_sorted, demands['apparent_timestamp'])

        apparent_ts = corresponding_site_apparent_load["timestamp"]

        site_active = corresponding_site_apparent_load["ANSTO TOTAL_KW"]
        site_reactive = corresponding_site_apparent_load["ANSTO TOTAL_KVAR"]

        if (apparent_ts != demands['apparent_timestamp']):
            logging.warning(f"Substation {id}: Missed max demand interval, using next closest fallback. Looking for {demands['apparent_timestamp']}, found {apparent_ts}")

        results[id] = (demands["max_apparent"][0]/site_active,demands["max_apparent"][1]/site_reactive, max_p, max_q)

    max_site_p = np.max(site_data_sorted["ANSTO TOTAL_KW"])
    max_site_q = np.max(site_data_sorted["ANSTO TOTAL_KVAR"])
    logging.info(f"Characterised loads: {results}. Max site demand P={max_site_p} kW, Q={max_site_q} kVAr")
    return results, (max_site_p, max_site_q)