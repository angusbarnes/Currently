class Plugin:

    NAME = "LastWeekReplay"

    def __init__(self, host):
        self.host = host

    def register(self):
        print(f"{self.NAME} model was loaded")

    def deregister(self):
        print(f"{self.NAME} Deregistered")

    def predict_next(self, history):
        if len(history) > 96*7:
            return history[-96*7][1]
    
        return None

    def get_type(self):
        return "MODEL"
    
    def get_formatted_name(self):
        return f"{self.NAME}"