import csv
from dataclasses import dataclass
import pandapower as pp
import pygame
import math
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class FeederDefinition:
    feeder_bus: str
    feeder_length: float
    feeder_type: str

@dataclass
class BusNode:
    name: str
    rating: float
    substation: str
    feeders: List[FeederDefinition] = field(default_factory=list)
    children: List['BusNode'] = field(default_factory=list)
    pp_bus: Optional[int] = None  # Will store the pandapower bus index

    def add_child(self, child_bus):
        self.children.append(child_bus)

# Load CSV
bus_nodes = {}
with open('network.csv', newline='') as csvfile:
    reader = csv.reader(csvfile)
    next(reader)  # Skip header

    for bus, feeder, feeder_length, feeder_type, rating, substation, _ in reader:
        feeder_def = FeederDefinition(
            feeder_bus=feeder,
            feeder_length=float(feeder_length) / 1000,
            feeder_type=feeder_type
        )

        if bus not in bus_nodes:
            bus_nodes[bus] = BusNode(
                name=bus,
                rating=float(rating),
                substation=substation
            )
        bus_nodes[bus].feeders.append(feeder_def)

# Create pandapower network and BusNode objects
net = pp.create_empty_network()

# Create pandapower bus for each node
for node in bus_nodes.values():
    node.pp_bus = pp.create_bus(net, vn_kv=11.0, name=node.name)

# Add slack bus if not defined in CSV
if "slack" not in bus_nodes:
    slack_node = BusNode("slack", rating=0.0, substation="slack")
    slack_node.pp_bus = pp.create_bus(net, vn_kv=11.0, name="slack")
    pp.create_ext_grid(net, bus=slack_node.pp_bus)
    bus_nodes["slack"] = slack_node
else:
    pp.create_ext_grid(net, bus=bus_nodes["slack"].pp_bus)

# Create connections
for node in bus_nodes.values():
    for feeder in node.feeders:
        if feeder.feeder_bus not in bus_nodes:
            raise Exception(f"Feeder bus '{feeder.feeder_bus}' not defined for bus '{node.name}'")
        feeder_node = bus_nodes[feeder.feeder_bus]

        pp.create_line(
            net,
            from_bus=feeder_node.pp_bus,
            to_bus=node.pp_bus,
            length_km=feeder.feeder_length,
            std_type="NAYY 4x50 SE"
        )
        feeder_node.add_child(node)

    if node.rating > 0:
        pp.create_load(net, bus=node.pp_bus, p_mw=node.rating, q_mvar=0.1)

tree_elements = {name: node for name, node in bus_nodes.items()}


def layout_tree(node: BusNode, x, y, spacing_x, spacing_y, positions, depth=0):
    positions[node.name] = (x, y)
    num_children = len(node.children)
    if num_children == 0:
        return

    width = (num_children - 1) * spacing_x
    start_x = x - width // 2

    for i, child in enumerate(node.children):
        child_x = start_x + i * spacing_x

        _length = -1
        for feeder in child.feeders:
            if feeder.feeder_bus == node.name:
                _length = feeder.feeder_length
                break

        if _length < 0:
            raise Exception("Could not find relevant feeder length for child node")
        
        child_y = y + spacing_y * max(0.5, _length*10)
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


