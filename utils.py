import numpy as np
from numpy.typing import ArrayLike

def mean_median_dev(data: ArrayLike) -> tuple[float, float, float]:
    return (np.mean(data), np.nanmedian(data), np.std(data))

def report_mean_median_dev(data: ArrayLike) -> None:
    mean, median, std = np.round(mean_median_dev(data), 2)
    return { "Mean": mean, "Median": median, "Stddev": std}


def string_to_bool(s):
    s = s.lower()
    if s in ('true', '1', 't'):
        return True
    elif s in ('false', '0', 'f', ''):
        return False
    else:
        raise ValueError(f"Invalid boolean string: '{s}'")