import numpy as np

class Plugin:
    def __init__(self, host):
        self.host = host

    def register(self):
        print("Linear 12-Period model was loaded")

    def deregister(self):
        print("Linear 12-Period Deregistered")

    def predict_next(self, history):
        if len(history) < 12:
            return None

        values = np.array([v for _, v in history[-12:]], dtype=float)
        x = np.arange(len(values))

        coeffs = np.polyfit(x, values, 1)
        poly = np.poly1d(coeffs)

        return float(poly(len(values)))

    def get_type(self):
        return "MODEL"

    def get_formatted_name(self):
        return "Linear12"