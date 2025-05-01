import csv
from dataclasses import dataclass
import pandapower as pp
import pandapower.networks as pn
import pandapower.topology as top
import networkx as nx
from networkx.drawing.nx_pydot import graphviz_layout 
import matplotlib.pyplot as plt
from pprint import pprint
from pandapower.plotting.plotly import simple_plotly
from collections import deque

@dataclass
class BusDefinition:
    bus_name: str
    feeder_bus: str
    feeder_length: float
    substation: str

# Load CSV
bus_definitions = []
defined_busses = set()

with open('network.csv', newline='') as csvfile:
    spamreader = csv.reader(csvfile)
    next(spamreader)  # Skip header

    for bus, feeder, feeder_length, substation, _ in spamreader:
        if bus in defined_busses:
            raise Exception(f"Re-definition of bus: {bus}")
        bus_definitions.append(
            BusDefinition(
                bus, 
                feeder, 
                float(feeder_length) / 1000,
                substation
            )
        )
        defined_busses.add(bus)

# Build dependency graph
unresolved = {bus.bus_name: bus for bus in bus_definitions}
resolved = {}
net = pp.create_empty_network()

# Start with known root bus(es)
bus_objects = {}
queue = deque()

# For example, if you assume the 'slack' is the root
slack_name = "slack"
bus_objects[slack_name] = pp.create_bus(net, vn_kv=11.0)
resolved[slack_name] = True

# Load any bus whose feeder is already resolved
while unresolved:
    progress_made = False
    to_remove = []

    for name, bus in unresolved.items():
        if bus.feeder_bus in resolved:
            bus_objects[bus.bus_name] = pp.create_bus(net, 11.0, name=name)
            pp.create_line(
                net,
                from_bus=bus_objects[bus.feeder_bus],
                to_bus=bus_objects[bus.bus_name],
                length_km=bus.feeder_length,
                std_type="NAYY 4x50 SE"
            )
            resolved[bus.bus_name] = True
            to_remove.append(name)
            progress_made = True

    for name in to_remove:
        del unresolved[name]

    if not progress_made:
        raise Exception(
            f"Could not resolve all buses. Remaining unresolved: {list(unresolved.keys())}. "
            "Possible circular dependency or missing feeder bus."
        )

pprint(net)
# simple_plotly(net)

G = top.create_nxgraph(net, include_lines=True, include_trafos=True)

pos = graphviz_layout(G, prog='twopi')

labels = {node: net.bus.loc[node, 'name'] for node in G.nodes if node in net.bus.index}


plt.figure(figsize=(10, 8))
nx.draw(G, pos, with_labels=False, node_size=500, node_color='lightblue', font_size=10)
nx.draw_networkx_labels(G, pos, labels, font_size=10)
plt.title("Pandapower Network (NetworkX View)")
plt.show()
# 

# slack_bus = pp.create_bus(net, vn_kv=11.0)
# b2 = pp.create_bus(net, vn_kv=20.0)
# b3 = pp.create_bus(net, vn_kv=20.0)


# pp.create_line(net, from_bus=slack_bus, to_bus=b2, length_km=2.5, std_type="NAYY 4x50 SE")
# pp.create_line(net, from_bus=slack_bus, to_bus=b3, length_km=2.5, std_type="NAYY 4x50 SE")      
# pp.create_ext_grid(net, bus=slack_bus)


# pp.create_load(net, bus=b2, p_mw=1.5, q_mvar=0.5)
# pp.create_load(net, bus=b3, p_mw=1.0)




# pp.runpp(net)

# print(net.res_bus.vm_pu)
# print(net.res_bus)
# print(net.res_line.loading_percent)
