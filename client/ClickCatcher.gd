extends Control

func _ready() -> void:
	mouse_filter = MOUSE_FILTER_PASS   # allow events to pass by default

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		if not Input.is_key_pressed(KEY_CTRL):
			SelectionManager.clear_selection()
		# prevent camera from reacting if you want the "empty click" to ONLY clear selection
		accept_event()
