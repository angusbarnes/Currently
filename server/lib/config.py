import sys
import os
from . import utils

try:
    import tomllib
except ImportError:
    # On older versions of python we can fall back to tomli
    import tomli as tomllib

_default_config = {
    "show": True,
    "force-active": False,
    "debug": False,
    "target-voltage": 11000,
}


def SetPathParamResolves(resolver_map: dict):
    pass


def _parse_scenario_file(scenario_path, resolvers=None):
    if not os.path.isfile(scenario_path):
        raise FileNotFoundError(f"Scenario file not found: {scenario_path}")
    with open(scenario_path, "rb") as f:
        return tomllib.load(f)


def _parse_params(args, base_config):
    config = base_config.copy()
    if "--params" in args:
        idx = args.index("--params") + 1
        while idx < len(args) and args[idx].startswith("--"):
            key_value = args[idx][2:].split("=", 1)
            if len(key_value) == 2:
                key, value = key_value
                if value.isdigit():
                    value = int(value)
                else:
                    try:
                        value = utils.string_to_bool(value)
                    except:
                        pass
                config[key] = value
            idx += 1
    return config


def load_config(args, resolvers=None):
    config = _default_config.copy()

    if "--scenario" in args:
        scenario_index = args.index("--scenario") + 1
        if scenario_index >= len(args):
            raise ValueError("Expected a filename after --scenario")
        scenario_path = args[scenario_index]
        config.update(_parse_scenario_file(scenario_path, resolvers))

    config = _parse_params(args, config)
    return config


CONFIG = load_config(sys.argv)
