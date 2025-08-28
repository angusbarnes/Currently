extends Camera2D

# Configurable settings
@export var zoom_factor: float = 1.1       # Zoom multiplier per scroll tick (e.g. 1.1 = 10% change)
@export var min_zoom: float = 0.5
@export var max_zoom: float = 4.0
@export var base_pan_speed: float = 400.0  # Base screen-space speed in pixels/sec

# For disabling controls in certain contexts
var input_enabled: bool = true

# Internal
var dragging: bool = false
var last_mouse_pos: Vector2

func _ready():
	position_smoothing_enabled = false


func _unhandled_input(event):
	if not input_enabled:
		return

	# --- Zoom ---
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
			 # Zoom in
			_zoom_at_mouse(zoom_factor)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
			_zoom_at_mouse(1.0 / zoom_factor)     # Zoom out

		# --- Start/stop drag ---
		if event.button_index == MOUSE_BUTTON_MIDDLE:
			dragging = event.pressed
			last_mouse_pos = get_viewport().get_mouse_position()

		if event.button_index == MOUSE_BUTTON_RIGHT and event.pressed:
			pass
			
	# --- Drag movement ---
	if event is InputEventMouseMotion and dragging:
		var mouse_pos = get_viewport().get_mouse_position()
		var delta_screen = last_mouse_pos - mouse_pos
		# Convert screen delta to world delta based on current zoom
		position += delta_screen / zoom.x
		last_mouse_pos = mouse_pos


func _process(delta):
	if not input_enabled:
		return

	# --- Keyboard panning ---
	var move = Vector2.ZERO
	if Input.is_action_pressed("ui_left") or Input.is_action_pressed("move_left"):
		move.x -= 1
	if Input.is_action_pressed("ui_right") or Input.is_action_pressed("move_right"):
		move.x += 1
	if Input.is_action_pressed("ui_up") or Input.is_action_pressed("move_up"):
		move.y -= 1
	if Input.is_action_pressed("ui_down") or Input.is_action_pressed("move_down"):
		move.y += 1

	if move != Vector2.ZERO:
		# Keep perceived speed constant across zoom levels
		move = move.normalized() * base_pan_speed / zoom.x
		position += move * delta


func _zoom_at_mouse(multiplier: float):
	var old_zoom = zoom
	var new_zoom_value = clamp(zoom.x * multiplier, min_zoom, max_zoom)
	zoom = Vector2(new_zoom_value, new_zoom_value)

	# Adjust position so zoom focuses on mouse
	var mouse_world_before = get_global_mouse_position()
	var mouse_world_after = get_global_mouse_position()
	position += mouse_world_before - mouse_world_after
