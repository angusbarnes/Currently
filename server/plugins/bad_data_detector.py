class Plugin:
    def __init__(self, host):
        self.host = host

    def register(self):
        print("[bad_data_dectector] Registered, with modifications test change")

    def deregister(self):
        print("[ExamplePlugin] Deregistered")

    def get_type(self):
        return "MODEL"
    
    def predict_next(self):
        return "MODEL"
    
    def update_history(self):
        pass