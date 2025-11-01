extends Control

@onready var scores_container = $ScoreboardContainer
@export var entry_scene: PackedScene

func _ready():
    SelectionManager.selection_changed.connect(_substation_selection_changed)
    
func _substation_selection_changed(substation):
    var player_scores = {
        "Alice": 0.85,
        "Bob": 0.92,
        "Carol": 0.77
    }
    populate_scoreboard(player_scores)

func populate_scoreboard(scores: Dictionary) -> void:

    for child in scores_container.get_children():
        child.queue_free()

    # Sort the dictionary by ascending score
    var sorted_entries = scores.keys()
    sorted_entries.sort_custom(func(a, b):
        return scores[a] < scores[b]
    )

    for name in sorted_entries:
        var entry = entry_scene.instantiate()
        var name_label = entry.get_node("Name")
        var score_label = entry.get_node("Score")

        name_label.text = name
        score_label.text = "%.1f%%" % (scores[name] * 100.0)

        scores_container.add_child(entry)
