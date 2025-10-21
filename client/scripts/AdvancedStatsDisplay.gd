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
    print("Advanced stats recieved selection changed")

func _process(delta):
    if last_selected_sub == null:
        return
    var data = last_selected_sub.get_last_interval()
    
    phase_a_label.text = Utils.safe_get_number_from_dict(data, "av")
    phase_b_label.text = Utils.safe_get_number_from_dict(data, "bv")
    phase_c_label.text = Utils.safe_get_number_from_dict(data, "cv")
    current_a_label.text = Utils.safe_get_number_from_dict(data, "ai")
    current_b_label.text = Utils.safe_get_number_from_dict(data, "bi")
    current_c_label.text = Utils.safe_get_number_from_dict(data, "ci")
