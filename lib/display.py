import math
import os
import logging
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    logging.error("Pygame is not installed. Display features will be disabled.")
    PYGAME_AVAILABLE = False

from lib.data_types import BusNode


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

        # Declutter display for very short cables
        if _length < 0.050:
            _length += 0.050

        child_y = y + spacing_y * max(0.5, _length * 10)
        layout_tree(child, child_x, child_y, spacing_x, spacing_y, positions)


def draw_tree(screen, font, node: BusNode, positions, offset_x, offset_y, zoom):
    x, y = positions[node.name]
    x = int(x * zoom + offset_x)
    y = int(y * zoom + offset_y)

    pygame.draw.circle(
        screen, (0, 100, 255), (x, y), int(20 * zoom) * math.sqrt(node.rating / 0.5)
    )
    text = font.render(node.name, True, (255, 255, 255))
    text_rect = text.get_rect(center=(x, y))
    screen.blit(text, text_rect)

    for child in node.children:
        cx, cy = positions[child.name]
        cx = int(cx * zoom + offset_x)
        cy = int(cy * zoom + offset_y)

        _active = False
        _size = 0
        for feeder in child.feeders:
            if feeder.feeder_bus == node.name:
                _active = feeder.active
                break

        pygame.draw.line(
            screen,
            (200, 200, 200) if _active else (200, 20, 20),
            (x, y),
            (cx, cy),
            max(1, int(2 * zoom)),
        )
        draw_tree(screen, font, child, positions, offset_x, offset_y, zoom)


def run_visualization(root):

    if not PYGAME_AVAILABLE:
        logging.error("Visualisation is not available unless pygame is installed.")
        return

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
