class CurrentlyPlugin:
    def register_handler(self, handler, callback):
        pass


class ExamplePlugin(CurrentlyPlugin):
    """
    Example plugin class structure
    """
    plugin_name = "My Example Plugin"
    plugin_version = "1.0.0"
    plugin_author = "Example Author"

    def __init__(self, host):
        self.host = host
        self._event_handlers = {}

    def register(self):
        print(f"[{self.plugin_name}] Registering plugin.")
        self.register_handler("on_data_received", self.on_data_received)
        self.register_handler("on_server_tick", self.on_tick)

    def on_data_received(self, data):
        print(f"[{self.plugin_name}] Data received: {data}")

    def on_server_tick(self, dt):
        print(f"[{self.plugin_name}] Tick event: t={dt}")