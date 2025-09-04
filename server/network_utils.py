import json
from dataclasses import asdict, is_dataclass, fields

def dataclass_to_json(obj) -> str:
    if not is_dataclass(obj):
        raise TypeError("dataclass_to_json expects a dataclass instance")
    return json.dumps(asdict(obj), separators=(",", ":"))

def dataclasses_to_json(objs: list) -> str:
    if not all(is_dataclass(o) for o in objs):
        raise TypeError("dataclasses_to_json expects a list of dataclass instances")
    return json.dumps([asdict(o) for o in objs], separators=(",", ":"))

def dataclass_from_json(cls, data: str):
    raw = json.loads(data)
    if not is_dataclass(cls):
        raise TypeError("dataclass_from_json expects a dataclass type")
    return cls(**raw)

def dataclasses_from_json(cls, data: str) -> list:
    raw_list = json.loads(data)
    if not isinstance(raw_list, list):
        raise ValueError("dataclasses_from_json expects a JSON array")
    return [cls(**raw) for raw in raw_list]