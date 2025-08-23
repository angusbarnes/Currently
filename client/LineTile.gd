extends Line2D


@export var line_id: String
@export var line_label: Label
@export var current_label: Label

var is_selected: bool = false

#func _gui_input(event: InputEvent) -> void:
	#if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		#var ctrl = Input.is_key_pressed(KEY_CTRL) or Input.is_key_pressed(KEY_META) # Cmd on Mac
		#SelectionManager.select(self, ctrl)

#func set_selected(value: bool):
	#is_selected = value
	#_update_outline()

#func _update_outline():
	#if is_selected:
		#add_theme_stylebox_override("panel", _selected_style())
	#else:
		#add_theme_stylebox_override("panel", _default_style())
#
#func _toggle_selection():
	#is_selected = !is_selected
	#_update_outline()
#
#func _default_style() -> StyleBoxFlat:
	#var sb = StyleBoxFlat.new()
	#sb.bg_color = Color(0.15, 0.15, 0.15) # grey background
	#sb.set_border_width_all(0)
	#sb.set_expand_margin_all(0)
	#return sb
#
#func _selected_style() -> StyleBoxFlat:
	#var sb = StyleBoxFlat.new()
	#sb.bg_color = Color(0.15, 0.15, 0.15)
	#sb.set_border_width_all(3.0)
	#sb.set_expand_margin_all(3.0)
	#sb.border_color = Color.YELLOW
	#return sb
	
#func update_online_status(online: bool):
		#var sb = StyleBoxFlat.new()
		#
		#if online:
			#sb.bg_color = Color.CHARTREUSE;
		#else:
			#sb.bg_color = Color.TOMATO
	#
		#connected_status_panel.add_theme_stylebox_override("panel", sb)

func _ready():
	assert(line_id.length() != 0, "line ID cannot be empty!")
	SubstationManager.register_tile(line_id, self)
	line_label.text = line_id

func update_data(data: Dictionary):
	if data.has("current_A"):
		current_label.text = "%0.1f A" % data["current_A"]
