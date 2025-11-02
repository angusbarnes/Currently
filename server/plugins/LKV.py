class Plugin:

    def __init__(self, host):
        self.host = host

    def register(self):
        print("LastKnownValue model was loaded")

    def deregister(self):
        print("LastKnownValue Deregistered")

    def predict_next(self, history):
        # This is getting the last entry in the list and then getting the second
        # element which is an S value
        if len(history) > 0:
            return history[-1][1]
    
        return None

    def get_type(self):
        return "MODEL"
    
    def get_formatted_name(self):
        return "LastKnownValue"