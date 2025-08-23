extends Node

@onready var ws = WebSocketPeer.new()
var tiles: Dictionary = {}  # substation_id → SubstationTile reference

signal connected
signal disconnected
signal error(msg: String)

# --- Schema definition for incoming substation data ---
const SUBSTATION_SCHEMA = {
    "id": TYPE_STRING,
    "voltage_kV": TYPE_FLOAT,
    "current_A": TYPE_FLOAT,
    "power_MW": TYPE_FLOAT,
    "online": TYPE_BOOL,
}

func _ready():
    ws.connect_to_url("ws://127.0.0.1:8080")
    print("[WS] Manager Loaded: Connecting to server...")
    set_process(true)

func _process(delta):
    ws.poll()

    match ws.get_ready_state():
        WebSocketPeer.STATE_CONNECTING:
            # Called every frame during connecting
            pass
        WebSocketPeer.STATE_OPEN:
            _process_messages()
        WebSocketPeer.STATE_CLOSED:
            print("[WS] Connection closed.")
            emit_signal("disconnected")
        WebSocketPeer.STATE_CLOSING:
            print("[WS] Closing connection (possible error).")
            emit_signal("error", "WebSocket encountered an error.")

func _process_messages():
    while ws.get_available_packet_count() > 0:
        var packet = ws.get_packet()
        if ws.was_string_packet():
            var msg = packet.get_string_from_utf8()
            print("[WS] Received: %s" % msg)
            _handle_message(msg)
        else:
            print("[WS] Received non-string packet, ignoring.")

func _handle_message(msg: String):
    var res = JSON.parse_string(msg)
    if typeof(res) != TYPE_DICTIONARY:
        print("[WS][ERROR] Invalid packet, not a dictionary: %s" % msg)
        return

    # Schema validation
    var missing: Array = []
    var wrong_type: Array = []
    for key in SUBSTATION_SCHEMA.keys():
        if not res.has(key):
            missing.append(key)
        elif typeof(res[key]) != SUBSTATION_SCHEMA[key]:
            wrong_type.append("%s (expected %s, got %s)" % [
                key, 
                str(SUBSTATION_SCHEMA[key]), 
                str(typeof(res[key]))
            ])

    if missing.size() > 0 or wrong_type.size() > 0:
        print("[WS][WARN] Schema check failed for packet ID=%s" % res.get("id", "<no id>"))
        if missing.size() > 0:
            print("   Missing fields: %s" % str(missing))
        if wrong_type.size() > 0:
            print("   Wrong types: %s" % str(wrong_type))

    if res.has("id"):
        var id = res["id"]
        if tiles.has(id):
            tiles[id].update_data(res)
        else:
            print("[WS][WARN] Got data for unknown substation ID=%s" % id)

func register_tile(id: String, tile: Node):
    assert(not tiles.has(id), "Two tiles cannot share the same substation ID! Name: " + id)
    tiles[id] = tile
    print("[WS] Registered new tile: %s" % id)

func unregister_tile(id: String):
    tiles.erase(id)
    print("[WS] Unregistered tile: %s" % id)

func send_config_change(id: String, config: Dictionary):
    if ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
        var payload = {
            "action": "config_update",
            "id": id,
            "config": config
        }
        var json_str = JSON.stringify(payload)
        ws.send_string(json_str)
        print("[WS] Sent config update for ID=%s: %s" % [id, json_str])
    else:
        print("[WS][WARN] Tried to send config change but socket not open.")
