class_name ConfigUIFactory extends Node

## Build a configuration form dynamically from a schema.
## Schema is an Array of Dictionaries, each field like:
## {
##   "id": "voltage",
##   "type": "int",       # string | int | bool | enum
##   "label": "Voltage (kV)",
##   "default": 110,
##   "options": ["North", "South", "East", "West"]  # for enums
## }

func build_config_ui(schema: Array) -> Control:
	var container := VBoxContainer.new()
	container.name = "ConfigForm"

	for field in schema:
		var label = Label.new()
		label.text = field.get("label", field["id"])
		container.add_child(label)

		var editor: Control

		match field["type"]:
			"string":
				editor = LineEdit.new()
				editor.text = str(field.get("default", ""))
			"int":
				editor = SpinBox.new()
				editor.min_value = field.get("min", -INF)
				editor.max_value = field.get("max", INF)
				editor.step = 1
				editor.value = int(field.get("default", 0))
			"bool":
				editor = CheckBox.new()
				editor.text = field.get("label", field["id"])  # inline label for bools
				editor.button_pressed = field.get("default", false)
				# optional: don’t add the label separately
				container.remove_child(label)
				label.queue_free()
			"enum":
				editor = OptionButton.new()
				var options: Array = field.get("options", [])
				for option in options:
					editor.add_item(str(option))
				var default_idx := options.find(field.get("default", options[0] if options else ""))
				if default_idx != -1:
					editor.select(default_idx)

		# tag editor with the field_id so we can later extract values
		editor.set_meta("field_id", field["id"])
		editor.set_meta("field_type", field["type"])

		container.add_child(editor)

	return container


## Extract a dictionary of values back out of a generated form
func collect_config_values(form: Control) -> Dictionary:
	var config := {}
	for child in form.get_children():
		if not child.has_meta("field_id"):
			continue
		var field_id: String = child.get_meta("field_id")
		var field_type: String = child.get_meta("field_type")

		match field_type:
			"string":
				config[field_id] = child.text
			"int":
				config[field_id] = int(child.value)
			"bool":
				config[field_id] = child.button_pressed
			"enum":
				config[field_id] = child.get_item_text(child.get_selected_id())

	return config
