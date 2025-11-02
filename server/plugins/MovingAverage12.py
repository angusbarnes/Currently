import numpy as np

class Plugin:
    def __init__(self, host, period: int = 12):
        self.host = host
        self.period = period

    def register(self):
        print(f"MovingAverage({self.period}) model was loaded")

    def deregister(self):
        print(f"MovingAverage({self.period}) Deregistered")

    def predict_next(self, history):
        if len(history) < self.period:
            return None

        values = np.array([v for _, v in history[-self.period:]], dtype=float)
        return float(np.mean(values))

    def get_type(self):
        return "MODEL"

    def get_formatted_name(self):
        return f"MovingAverage{self.period}"
