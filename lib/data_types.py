from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FeederDefinition:
    feeder_bus: str
    feeder_length: float
    feeder_type: str
    active: bool


@dataclass
class BusNode:
    name: str
    rating: float
    substation: str
    feeders: List[FeederDefinition] = field(default_factory=list)
    children: List["BusNode"] = field(default_factory=list)
    pp_bus: Optional[int] = None  # Will store the pandapower bus index
    characterised_load_kw: float = None
    characterised_load_kvar: float = None

    def add_child(self, child_bus):
        self.children.append(child_bus)
