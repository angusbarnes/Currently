extends Node2D

var drawn_points: Array[Vector2] = []
var _pressed = false
# Called when the node enters the scene tree for the first time.
func _ready():
	pass # Replace with function body.


# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(delta):
	pass
		
var current_line : Line2D

func _input(event):
	
	if event is InputEventMouseButton:
		
		if event.button_index != MOUSE_BUTTON_LEFT:
			return
			
		_pressed = event.is_pressed()
		
		if _pressed:
			current_line = Line2D.new()
			add_child(current_line)
			current_line.antialiased = false
			current_line.end_cap_mode = Line2D.LINE_CAP_ROUND
			current_line.width = 4
			current_line.default_color = Color(Color.YELLOW, 0.7)
			current_line.add_point(get_global_mouse_position())
	elif event is InputEventMouseMotion && _pressed:
		current_line.add_point(get_global_mouse_position())
