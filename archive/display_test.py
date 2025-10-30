import networkx as nx
import matplotlib.pyplot as plt
import mplcursors

# Create a graph for the single line diagram
G = nx.Graph()

# Define nodes (buses, transformers, loads)
nodes = {
    "Bus 1": {"type": "Bus", "voltage": "11kV"},
    "Bus 2": {"type": "Bus", "voltage": "33kV"},
    "Transformer 1": {"type": "Transformer", "rating": "10MVA"},
    "Load 1": {"type": "Load", "power": "5MW"},
    "Load 2": {"type": "Load", "power": "3MW"},
}

# Add nodes to the graph
for node, attrs in nodes.items():
    G.add_node(node, **attrs)

# Define connections (edges)
edges = [
    ("Bus 1", "Transformer 1"),
    ("Transformer 1", "Bus 2"),
    ("Bus 2", "Load 1"),
    ("Bus 2", "Load 2"),
]

# Add edges to the graph
G.add_edges_from(edges)

# Layout for visualization
pos = {
    "Bus 1": (0, 2),
    "Transformer 1": (1, 2),
    "Bus 2": (2, 2),
    "Load 1": (3, 3),
    "Load 2": (3, 1),
}

# Draw the graph
fig, ax = plt.subplots(figsize=(6, 4))
nx.draw(G, pos, with_labels=True, node_size=3000, node_color="lightblue", edge_color="gray", font_size=10)

# Add tooltips with mplcursors
cursor = mplcursors.cursor(hover=True)

@cursor.connect("add")
def on_hover(sel):
    node = sel.annotation.get_text()
    if node in nodes:
        sel.annotation.set_text(f"{node}\n{nodes[node]}")
        sel.annotation.get_bbox_patch().set(fc="white", alpha=0.8)

plt.title("Single Line Diagram")
plt.show()
