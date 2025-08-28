extends Panel


@export var phase_a_label: Label
@export var phase_b_label: Label
@export var phase_c_label: Label
@export var current_a_label: Label
@export var current_b_label: Label
@export var current_c_label: Label

func round_to_dec(num, digit):
	return round(num * pow(10.0, digit)) / pow(10.0, digit)

func _ready():
	SelectionManager.selection_changed.connect(_substation_selection_changed)


var last_selected_sub: SubstationTile = null

func _substation_selection_changed(tile: SubstationTile):
	last_selected_sub = tile

func _process(delta):
	if last_selected_sub == null:
		return
	var data = last_selected_sub.get_last_interval()
	
	phase_a_label.text = str(round_to_dec(data["voltage_an"],2))
	phase_b_label.text = str(round_to_dec(data["voltage_bn"],2))
	phase_c_label.text = str(round_to_dec(data["voltage_cn"],2))
	current_a_label.text = str(round_to_dec(data["current_a"],2))
	current_b_label.text = str(round_to_dec(data["current_b"],2))
	current_c_label.text = str(round_to_dec(data["current_c"],2))
