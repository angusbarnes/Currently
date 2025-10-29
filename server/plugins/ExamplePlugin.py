class Plugin:
    def __init__(self, host):
        self.host = host

    def register(self):
        self.host.add_event_listener("on_tick", self.on_tick)
        print("[ExamplePlugin] Registered, with modifications")

    def deregister(self):
        print("[ExamplePlugin] Deregistered")

    def on_tick(self, dt):
        print(f"[ExamplePlugin] Tick: {dt}")
