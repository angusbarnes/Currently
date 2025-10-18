import logging


def report_loading_conditions(site_max_loads, characterised_loads):

    print("============= MAX DEMAND SITE LOADS ==============")
    print(f"     P = {site_max_loads[0]:.2f} kW")
    print(f"     Q = {site_max_loads[1]:.2f} kVAr")
    print()

    print("======================= CHARACTERISED LOADS =======================")
    header = f"{'Substation':<12} {'P Load (kW)':>12} {'Q Load (kVAr)':>15} {'Charac. P':>10} {'Charac. Q':>10}"
    print(header)
    print("-" * len(header))

    for substation, load_details in characterised_loads.items():
        max_p_load_percent, max_q_load_percent, max_p_load, max_q_load = load_details
        print(
            f"{substation:<12} {max_p_load:>12.2f} {max_q_load:>15.2f} {max_p_load_percent*site_max_loads[0]:>10.2f} {max_q_load_percent*site_max_loads[1]:>10.2f}"
        )


def report_bus_voltages(net, decimals=2):
    res_bus = net.res_bus
    bus_df = net.bus

    if res_bus.empty:
        print("No bus voltage results to display.")
        return

    print("============= BUS VOLTAGE RESULTS =============")
    header = (
        f"{'Bus ID':<8} {'Bus Name':<20} {'V_mag (pu)':>10} {'V_ang (deg)':>13} "
        f"{'P (kW)':>10} {'Q (kVAr)':>10}"
    )
    print(header)
    print("-" * len(header))

    for idx, row in res_bus.iterrows():
        bus_name = bus_df.loc[idx, "name"]
        v_mag = round(row["vm_pu"], decimals)
        v_ang = round(row["va_degree"], decimals)
        p_kw = round(row["p_mw"] * 1000, decimals)
        q_kvar = round(row["q_mvar"] * 1000, decimals)

        print(
            f"{idx:<8} {bus_name:<20} {v_mag:>10.{decimals}f} {v_ang:>13.{decimals}f} "
            f"{p_kw:>10.{decimals}f} {q_kvar:>10.{decimals}f}"
        )


def report_line_loadings(net, decimals=2):
    res_line = net.res_line
    line_data = net.line
    bus_data = net.bus

    if res_line.empty:
        print("No line results to display.")
        return

    print("============= LINE LOADING RESULTS =============")
    header = f"{'Line ID':<8} {'From Bus':<20} {'To Bus':<20} {'Loading (%)':>13} {'I (A)':>10}"
    print(header)
    print("-" * len(header))

    for idx, row in res_line.iterrows():
        from_bus_idx = line_data.loc[idx, "from_bus"]
        to_bus_idx = line_data.loc[idx, "to_bus"]
        from_bus_name = bus_data.loc[from_bus_idx, "name"]
        to_bus_name = bus_data.loc[to_bus_idx, "name"]

        loading = round(row["loading_percent"], decimals)
        i_amps = row["i_ka"] * 1000  # Convert kA to A

        print(
            f"{idx:<8} {from_bus_name:<20} {to_bus_name:<20} "
            f"{loading:>13.{decimals}f} {i_amps:>10.{decimals}f}"
        )
