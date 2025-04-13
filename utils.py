import numpy as np
from numpy.typing import ArrayLike

def mean_median_dev(data: ArrayLike) -> tuple[float, float, float]:
    return (np.mean(data), np.nanmedian(data), np.std(data))

def report_mean_median_dev(data: ArrayLike) -> None:
    mean, median, std = np.round(mean_median_dev(data), 2)
    return { "Mean": mean, "Median": median, "Stddev": std}