extends Panel


@export var phase_a_label: Label
@export var phase_b_label: Label
@export var phase_c_label: Label
@export var current_a_label: Label
@export var current_b_label: Label
@export var current_c_label: Label

func _ready():
    SelectionManager.selection_changed.connect(_substation_selection_changed)


var last_selected_sub: SubstationTile = null

func _substation_selection_changed(tile: SubstationTile):
    last_selected_sub = tile

func _process(delta):
    if last_selected_sub == null:
        return
    var data = last_selected_sub.get_last_interval()
    
    phase_a_label.text = Utils.safe_get_number_from_dict(data, "voltage_an")
    phase_b_label.text = Utils.safe_get_number_from_dict(data, "voltage_bn")
    phase_c_label.text = Utils.safe_get_number_from_dict(data, "voltage_cn")
    current_a_label.text = Utils.safe_get_number_from_dict(data, "current_a")
    current_b_label.text = Utils.safe_get_number_from_dict(data, "current_b")
    current_c_label.text = Utils.safe_get_number_from_dict(data, "current_c")
