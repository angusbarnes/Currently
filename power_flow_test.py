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
import pygame
import math

@dataclass
class BusDefinition:
    bus_name: str
    feeder_bus: str
    feeder_length: float
    bus_rated_load: float
    substation: str

class BusNode:
    def __init__(self, name, rating, length_from_parent=0.0):
        self.name = name
        self.length = length_from_parent
        self.children = []
        self.rating = rating

    def add_child(self, child_bus):
        self.children.append(child_bus)


# Recursive function to calculate layout positions
def layout_tree(node, x, y, spacing_x, spacing_y, positions, depth=0):
    positions[node.name] = (x, y)
    num_children = len(node.children)
    if num_children == 0:
        return

    width = (num_children - 1) * spacing_x
    start_x = x - width // 2

    for i, child in enumerate(node.children):
        child_x = start_x + i * spacing_x
        child_y = y + spacing_y * max(0.5, child.length*10)
        layout_tree(child, child_x, child_y, spacing_x, spacing_y, positions)

def draw_tree(screen, font, node: BusNode, positions, offset_x, offset_y, zoom):
    x, y = positions[node.name]
    x = int(x * zoom + offset_x)
    y = int(y * zoom + offset_y)

    pygame.draw.circle(screen, (0, 100, 255), (x, y), int(20 * zoom) * math.sqrt(node.rating/0.5))
    text = font.render(node.name, True, (255, 255, 255))
    text_rect = text.get_rect(center=(x, y))
    screen.blit(text, text_rect)

    for child in node.children:
        cx, cy = positions[child.name]
        cx = int(cx * zoom + offset_x)
        cy = int(cy * zoom + offset_y)
        pygame.draw.line(screen, (200, 200, 200), (x, y), (cx, cy), max(1, int(2 * zoom)))
        draw_tree(screen, font, child, positions, offset_x, offset_y, zoom)


# Load CSV
bus_definitions = []
defined_busses = set()

with open('network.csv', newline='') as csvfile:
    spamreader = csv.reader(csvfile)
    next(spamreader)  # Skip header

    for bus, feeder, feeder_length, feeder_type, rating, substation, _ in spamreader:
        if bus in defined_busses:
            raise Exception(f"Re-definition of bus: {bus}")
        bus_definitions.append(
            BusDefinition(
                bus, 
                feeder, 
                float(feeder_length) / 1000,
                float(rating),
                substation
            )
        )
        defined_busses.add(bus)

# Build dependency graph
unresolved = {bus.bus_name: bus for bus in bus_definitions}
resolved = {}
net = pp.create_empty_network()

bus_objects = {}
queue = deque()

slack_name = "slack"
slack_bus_obj = pp.create_bus(net, vn_kv=11.0)
bus_objects[slack_name] = slack_bus_obj
pp.create_ext_grid(net, bus=slack_bus_obj)
resolved[slack_name] = True

tree_elements = {"slack": BusNode(slack_name, 10)}

while unresolved:
    progress_made = False
    to_remove = []

    for name, bus in unresolved.items():
        if bus.feeder_bus in resolved:
            graphical_bus_object = BusNode(bus.bus_name, bus.bus_rated_load, bus.feeder_length)

            tree_elements[bus.bus_name] = graphical_bus_object
            tree_elements[bus.feeder_bus].add_child(graphical_bus_object)
            
            bus_obj = pp.create_bus(net, 11.0, name=name)
            bus_objects[bus.bus_name] = bus_obj
            pp.create_line(
                net,
                from_bus=bus_objects[bus.feeder_bus],
                to_bus=bus_objects[bus.bus_name],
                length_km=bus.feeder_length,
                std_type="NAYY 4x50 SE"
            )

            pp.create_load(net, bus=bus_obj, p_mw=bus.bus_rated_load, q_mvar=0.1)
            resolved[bus.bus_name] = True
            to_remove.append(name)
            progress_made = True

    for name in to_remove:
        #TODO: Perhaps refactor to remove unsafe delete call
        del unresolved[name]

    if not progress_made:
        raise Exception(
            f"Could not resolve all buses. Remaining unresolved: {list(unresolved.keys())}. "
            "Possible circular dependency or missing feeder bus."
        )

pprint(net)

def run_visualization(root):
    pygame.init()
    screen = pygame.display.set_mode((1900, 980))
    pygame.display.set_caption("Substation Tree Visualization")
    font = pygame.font.SysFont(None, 20)
    clock = pygame.time.Clock()

    offset_x, offset_y = 0, 0
    dragging = False
    drag_start = (0, 0)
    zoom = 1.0

    positions = {}
    layout_tree(root, 950, 50, 120, 80, positions)

    running = True
    while running:
        screen.fill((30, 30, 30))

        draw_tree(screen, font, root, positions, offset_x, offset_y, zoom)

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == pygame.BUTTON_LEFT:  # Right-click drag
                    dragging = True
                    drag_start = pygame.mouse.get_pos()
                elif event.button == 4:  # Scroll up (zoom in)
                    mx, my = pygame.mouse.get_pos()
                    world_x = (mx - offset_x) / zoom
                    world_y = (my - offset_y) / zoom
                    zoom *= 1.1
                    offset_x = mx - world_x * zoom
                    offset_y = my - world_y * zoom

                elif event.button == 5:  # Scroll down (zoom out)
                    mx, my = pygame.mouse.get_pos()
                    world_x = (mx - offset_x) / zoom
                    world_y = (my - offset_y) / zoom
                    zoom /= 1.1
                    offset_x = mx - world_x * zoom
                    offset_y = my - world_y * zoom

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == pygame.BUTTON_LEFT:
                    dragging = False

            elif event.type == pygame.MOUSEMOTION:
                if dragging:
                    mx, my = event.rel
                    offset_x += mx
                    offset_y += my

        clock.tick(30)

    pygame.quit()

pp.runpp(net)

print(net.res_bus.vm_pu)
print(net.res_bus)
print(net.res_line.loading_percent)

run_visualization(tree_elements['slack'])

# # simple_plotly(net)

# G = top.create_nxgraph(net, include_lines=True, include_trafos=True)

# pos = graphviz_layout(G, prog='twopi')

# labels = {node: net.bus.loc[node, 'name'] for node in G.nodes if node in net.bus.index}


# plt.figure(figsize=(10, 8))
# nx.draw(G, pos, with_labels=False, node_size=500, node_color='lightblue', font_size=10)
# nx.draw_networkx_labels(G, pos, labels, font_size=10)
# plt.title("Pandapower Network (NetworkX View)")
# plt.show()
# # 

# # slack_bus = pp.create_bus(net, vn_kv=11.0)
# # b2 = pp.create_bus(net, vn_kv=20.0)
# # b3 = pp.create_bus(net, vn_kv=20.0)


# # pp.create_line(net, from_bus=slack_bus, to_bus=b2, length_km=2.5, std_type="NAYY 4x50 SE")
# # pp.create_line(net, from_bus=slack_bus, to_bus=b3, length_km=2.5, std_type="NAYY 4x50 SE")      
# # pp.create_ext_grid(net, bus=slack_bus)


# # pp.create_load(net, bus=b2, p_mw=1.5, q_mvar=0.5)
# # pp.create_load(net, bus=b3, p_mw=1.0)


