extends Panel
class_name SubstationTile

@export var substation_id: String
@export var substation_label: RichTextLabel
@export var connected_status_panel: Panel
@export var voltage_label: Label
@export var current_label: Label
@export var power_label: Label
var is_selected: bool = false

func _gui_input(event: InputEvent) -> void:
    if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
        var ctrl = Input.is_key_pressed(KEY_CTRL) or Input.is_key_pressed(KEY_META) # Cmd on Mac
        SelectionManager.select(self, ctrl)

func set_selected(value: bool):
    is_selected = value
    _update_outline()

func _update_outline():
    if is_selected:
        add_theme_stylebox_override("panel", _selected_style())
    else:
        add_theme_stylebox_override("panel", _default_style())

func _toggle_selection():
    is_selected = !is_selected
    _update_outline()

func _default_style() -> StyleBoxFlat:
    var sb = StyleBoxFlat.new()
    sb.bg_color = Color(0.104, 0.104, 0.104) # grey background
    sb.set_corner_radius_all(12)
    sb.set_border_width_all(0)
    sb.set_expand_margin_all(0)
    return sb

func _selected_style() -> StyleBoxFlat:
    var sb = StyleBoxFlat.new()
    sb.bg_color = Color(0.104, 0.104, 0.104)
    sb.set_border_width_all(3.0)
    sb.set_corner_radius_all(12)
    sb.set_expand_margin_all(3.0)
    sb.border_color = Color.YELLOW
    return sb
    
func update_online_status(online: String):
        var sb = StyleBoxFlat.new()
        sb.set_corner_radius_all(30)
        
        if online == "BAD":
            sb.bg_color = Color.ORANGE;
        elif online == "GOOD":
            sb.bg_color = Color.CHARTREUSE;
        else:
            sb.bg_color = Color.TOMATO
    
        connected_status_panel.add_theme_stylebox_override("panel", sb)

func _ready():
    assert(substation_id.length() != 0, "Substation ID cannot be empty!")
    SubstationManager.register_tile(substation_id, self)
    substation_label.text = substation_id
    
    
func get_last_interval() -> Dictionary:
    return last_data

func has_safe_value(dict: Dictionary, key: String):
    return dict.has(key) and dict[key] != null

var last_voltage: int = 0
var last_data: Dictionary = {}
func update_data(data: Dictionary):
    last_data = data
    if has_safe_value(data, "voltage_an"):
        if data["voltage_an"] > last_voltage:
            voltage_label.add_theme_color_override("font_color", Color.GREEN)
        elif data["voltage_an"] < last_voltage:
            voltage_label.add_theme_color_override("font_color", Color.RED)
        else:
            voltage_label.add_theme_color_override("font_color", Color.HONEYDEW)
        voltage_label.text = "%0.1f kV" % data["voltage_an"]
        last_voltage = data["voltage_an"]
    if has_safe_value(data, "current_a"):
        current_label.text = "%0.1f A" % data["current_a"]
    if has_safe_value(data, "power_active"):
        power_label.text = "%0.1f MW" % data["power_active"]
    if data.has("online"):
        update_online_status(data["online"])

# Example of user-triggered config change
func _on_button_pressed():
    var new_config = { "alert_threshold": 220 }
    SubstationManager.send_config_change(substation_id, new_config)
