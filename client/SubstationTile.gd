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
    sb.bg_color = Color(0.15, 0.15, 0.15) # grey background
    sb.set_border_width_all(0)
    sb.set_expand_margin_all(0)
    return sb

func _selected_style() -> StyleBoxFlat:
    var sb = StyleBoxFlat.new()
    sb.bg_color = Color(0.15, 0.15, 0.15)
    sb.set_border_width_all(3.0)
    sb.set_expand_margin_all(3.0)
    sb.border_color = Color.YELLOW
    return sb
    
func update_online_status(online: bool):
        var sb = StyleBoxFlat.new()
        
        if online:
            sb.bg_color = Color.CHARTREUSE;
        else:
            sb.bg_color = Color.TOMATO
    
        connected_status_panel.add_theme_stylebox_override("panel", sb)

func _ready():
    assert(substation_id.length() != 0, "Substation ID cannot be empty!")
    SubstationManager.register_tile(substation_id, self)
    substation_label.text = substation_id
    


func update_data(data: Dictionary):
    if data.has("voltage_kV"):
        voltage_label.text = "%0.1f kV" % data["voltage_kV"]
    if data.has("current_A"):
        current_label.text = "%0.1f A" % data["current_A"]
    if data.has("power_MW"):
        power_label.text = "%0.1f MW" % data["power_MW"]
    if data.has("online"):
        update_online_status(data["online"])

# Example of user-triggered config change
func _on_button_pressed():
    var new_config = { "alert_threshold": 220 }
    SubstationManager.send_config_change(substation_id, new_config)
