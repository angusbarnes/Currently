extends Node

func round_to_dec(num, digit):
    return round(num * pow(10.0, digit)) / pow(10.0, digit)

func safe_get_number_from_dict(dict: Dictionary, key: String, decimals: int = 2, error_value = "N/A"):
    if dict.has(key):
        return str(round_to_dec(dict[key], decimals))
    else:
        return error_value