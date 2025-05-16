import os
import pathlib
import typing
from copy import deepcopy

__GLOBAL_VERBOSE = False


def _v_log(statement):
    if __GLOBAL_VERBOSE:
        print(statement)


def _load_from_file(
    path: pathlib.Path, seed_dict: typing.Dict[str, str] = None, override=False
) -> typing.Dict[str, str]:
    """
    Load environment variables from file into a python dict object

    Args:
        path: The file path for the environmental file to parse
        seed_dict: A base dictionary of previously established .env variables
        override: If this is set to true, key-values which have been previously defined will
                  be silently overriden by the newest value
    Returns:
        A dict[str, str] which contains a mapping of key-value pairs
    """

    key_value_pairs: typing.Dict[str, str] = {}

    # If a seed dictionary is provided, we should deep copy it to prevent any modifications
    # from outside this scope.
    # TODO: Clarify if this is necessary for a [str, str] dict since strings are immutable anyway
    if seed_dict:
        key_value_pairs = deepcopy(seed_dict)

    with open(path, "r", encoding="utf-8") as file:
        for i, line in enumerate(file):
            text = line.strip()

            # Ignore blank lines and comments
            if not text or text[0] == "#":
                continue

            if "=" not in text or text.count("=") != 1:
                raise SyntaxError(
                    f"Syntax error in environment file. There is an incorrect number of '=' characters. Line #{i+1} in '{path.absolute()}'"
                )

            key, value = text.split("=")

            if key in key_value_pairs and not override:
                raise KeyError(
                    f"Re-definition of environment variable '{key}' in file '{path.absolute()}' on line #{i+1}."
                )
            else:
                key_value_pairs[key] = value

    return key_value_pairs


def load_env(path="./", override=False, verbose=False):
    """
    Load environment variables from one/many .env files

    Args:
        path: The root path for the project or a specific .env file.
            If a directory is specified, this will search all contained files with
            the '.env' extension and load them into a dictionary. If a specific file is specfied,
            this function will simply return the contents of that file as a dictionary.
        override: Should duplicate values silently override each other. It is generally recommended
            to keep this value as False unless you have a good reason to change it.
        verbose: Should verbose logging be provided. If this is set to True, more detailed logs will
            be printed to stdout as .env files are parsed.
    Returns:
        A python dict containing key value pairs as specified in the searched .env files.
    """
    global __GLOBAL_VERBOSE
    __GLOBAL_VERBOSE = verbose
    resolved_path = pathlib.Path(path)

    if resolved_path.is_file():

        if not resolved_path.exists():
            raise FileNotFoundError("No environment file with this name exists")

        return _load_from_file(resolved_path)

    elif resolved_path.is_dir():
        _v_log(f"Searching {resolved_path.absolute()} for '.env' files.")
        context_kv_dict = {}
        for path in resolved_path.glob("*.env"):
            if path.is_file() and path.name.endswith(".env"):

                # Replace the current context with the additional parameters in the found .env file
                context_kv_dict = _load_from_file(
                    path, context_kv_dict, override=override
                )

        return context_kv_dict
    else:
        raise Exception("An unknown path type was encountered. Aborting .env parsing.")
