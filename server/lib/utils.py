import numpy as np
from numpy.typing import ArrayLike
from pathlib import Path


def resolve_relative_path_from_config(relative_path, config_path):
    toml_path = Path(config_path).resolve()
    base_dir = toml_path.parent

    if not isinstance(relative_path, str):
        raise Exception(f"Expected relative path passed as string, got: {type(relative_path)}")
    path = Path(relative_path)
    if path.is_absolute():
            return relative_path
    
    return (base_dir / path).resolve()


def mean_median_dev(data: ArrayLike) -> tuple[float, float, float]:
    return (np.mean(data), np.nanmedian(data), np.std(data))


def report_mean_median_dev(data: ArrayLike) -> None:
    mean, median, std = np.round(mean_median_dev(data), 2)
    return {"Mean": mean, "Median": median, "Stddev": std}


def string_to_bool(s):
    s = s.lower()
    if s in ("true", "1", "t"):
        return True
    elif s in ("false", "0", "f", ""):
        return False
    else:
        raise ValueError(f"Invalid boolean string: '{s}'")


def safe_str_to_float(s):
    if not isinstance(s, str):
        return None
    try:
        cleaned = s.strip().replace(",", "").replace('"', "").replace("'", "")
        return float(cleaned)
    except ValueError:
        return None
