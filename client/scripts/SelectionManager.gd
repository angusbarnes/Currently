extends Node

signal selection_changed(substation: SubstationTile)
var last_selected: SubstationTile

var selected_tiles: Array[SubstationTile] = []

func update():
    if last_selected != null:
        selection_changed.emit(last_selected)

func select(tile: SubstationTile, ctrl_pressed: bool):
    selection_changed.emit(tile)
    last_selected = tile
    print("Selection changed")
    if ctrl_pressed:
        # Toggle
        if tile in selected_tiles:
            deselect(tile)
        else:
            _add_selection(tile)
    else:
        # Single select
        clear_selection()
        _add_selection(tile)

func _add_selection(tile: SubstationTile):
    selected_tiles.append(tile)
    tile.set_selected(true)

func deselect(tile: SubstationTile):
    selected_tiles.erase(tile)
    tile.set_selected(false)

func clear_selection():
    for t in selected_tiles:
        t.set_selected(false)
    selected_tiles.clear()
