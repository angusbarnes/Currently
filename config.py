import sys
import utils

_default_config = {
    "show": True,
    "force-active": False,
    "debug": False
}

def _parse_params(args):
    config = _default_config.copy()
    if "--params" in args:
        idx = args.index("--params") + 1
        while idx < len(args) and args[idx].startswith("--"):
            key_value = args[idx][2:].split("=", 1)
            if len(key_value) == 2:
                key, value = key_value
                if value.isdigit():
                    value = int(value)
                else:
                    try: value = utils.string_to_bool(value)
                    except: pass

                config[key] = value
            idx += 1
    return config

CONFIG = _parse_params(sys.argv)