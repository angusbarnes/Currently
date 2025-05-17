import logging

def report_loading_conditions(site_max_loads, characterised_loads):

    print("============= MAX DEMAND SITE LOADS ==============")
    print(f"     P = {site_max_loads[0]:.2f} kW")
    print(f"     Q = {site_max_loads[1]:.2f} kVAr")
    print()

    print("============= SUBSTATION LOADS ==============")
    header = f"{'Substation':<12} {'P Load (kW)':>12} {'Q Load (kVAr)':>15} {'Charac. P':>10} {'Charac. Q':>10}"
    print(header)
    print("-" * len(header))

    for substation, load_details in characterised_loads.items():
        max_p_load_percent, max_q_load_percent, max_p_load, max_q_load = load_details
        print(f"{substation:<12} {max_p_load:>12.2f} {max_q_load:>15.2f} {max_p_load_percent*site_max_loads[0]:>10.2f} {max_q_load_percent*site_max_loads[1]:>10.2f}")
