extends Node

signal selection_changed(substation: SubstationTile)

var selected_tiles: Array[SubstationTile] = []

func select(tile: SubstationTile, ctrl_pressed: bool):
	selection_changed.emit(tile)
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
