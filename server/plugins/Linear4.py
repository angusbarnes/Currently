import numpy as np

class Plugin:
    def __init__(self, host):
        self.host = host

    def register(self):
        print("Linear 4-Period model was loaded")

    def deregister(self):
        print("Linear 4-Period Deregistered")

    def predict_next(self, history):
        # Need at least 4 points
        if len(history) < 4:
            return None

        values = np.array([v for _, v in history[-4:]], dtype=float)
        x = np.arange(len(values))  # 0, 1, 2, 3

        coeffs = np.polyfit(x, values, 1)
        poly = np.poly1d(coeffs)

        return float(poly(len(values)))

    def get_type(self):
        return "MODEL"

    def get_formatted_name(self):
        return "Linear4"
