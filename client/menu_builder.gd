extends Control
@onready var factory := preload("res://ConfigUIFactory.gd").new()

func _ready():
	var schema = [
		{"id": "name", "type": "string", "label": "Substation Name", "default": "New Substation"},
		{"id": "voltage", "type": "int", "label": "Voltage (kV)", "default": 110, "min": 0, "max": 500},
		{"id": "status", "type": "bool", "label": "Enabled", "default": true},
		{"id": "region", "type": "enum", "label": "Region", "options": ["North", "South", "East", "West"], "default": "North"}
	]

	var ui = factory.build_config_ui(schema)
	add_child(ui)

	var save_btn = Button.new()
	save_btn.set_position(save_btn.position + Vector2.DOWN * 230)
	save_btn.text = "Save Config"
	save_btn.pressed.connect(func():
		var cfg = factory.collect_config_values(ui)
		print("Collected config: ", cfg)
	)
	add_child(save_btn)
