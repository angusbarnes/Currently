from dataclasses import dataclass
from pathlib import Path
import csv
import logging
import pandapower as pp
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional
import pandapower as pp
import pandapower.networks as pn
import numpy as np
import random

from typing import List, Dict


def string_to_bool(s):
    s = s.lower()
    if s in ("true", "1", "t"):
        return True
    elif s in ("false", "0", "f", ""):
        return False
    else:
        raise ValueError(f"Invalid boolean string: '{s}'")


@dataclass
class LineType:
    name: str
    c_nf_per_km: float
    r_ohm_per_km: float
    x_ohm_per_km: float
    max_i_ka: float
    q_mm2: float  # Conductor cross sectional area
    alpha: float  # Temperature coeff for cable
    type: str = "cs"


def load_cable_types(cable_file: Path):
    custom_line_types = []
    with open(cable_file, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            custom_line_types.append(row)

    known_cables = []

    for cable in custom_line_types:
        try:
            known_cables.append(
                LineType(
                    name=cable["Cable Name"],
                    c_nf_per_km=float(cable["C (nF/km)"]),
                    r_ohm_per_km=float(cable["R (Ohm/km)"]),
                    x_ohm_per_km=float(cable["X (j Ohm/km)"]),
                    max_i_ka=float(cable["Max I (kA)"]),
                    q_mm2=float(cable["Q (mm2)"]),
                    alpha=float(cable["Alpha"]),
                )
            )
        except Exception as e:
            logging.warning(
                f"Could not register cable type '{cable['Cable Name']}': {e}. Check the definition in the cable file"
            )

    logging.info(f"{len(known_cables)} cable types registered successfully.")
    return known_cables


class Node:
    def serialise(self):
        raise NotImplementedError()

    def deserialise(self):
        raise NotImplementedError()


def assure_float(f: float):
    if f is None:
        return 0.0

    return f


@dataclass
class Line:
    id: int
    name: str
    line_from: str
    line_to: str
    length: float
    type: str
    is_active: bool = True
    line_object: object = None
    comment: str = ""

    loading_percent: Optional[float] = None
    i_from_ka: Optional[float] = None
    i_to_ka: Optional[float] = None
    p_from_mw: Optional[float] = None
    q_from_mvar: Optional[float] = None
    p_to_mw: Optional[float] = None
    q_to_mvar: Optional[float] = None
    pl_mw: Optional[float] = None
    ql_mvar: Optional[float] = None

    def serialise(self):
        _json = {}

        _json["id"] = str(self.id) if self.id != 0 else '100'
        _json["name"] = self.name
        _json["length"] = self.length
        _json["type"] = self.type
        _json["loading"] = assure_float(self.loading_percent)
        _json["i"] = assure_float(self.i_from_ka) * 1000

        return _json


# TODO: This is a somewhat lazy approach. Maybe re-write later if have time??
class GilbertElliottSimulator:
    def __init__(
        self,
        p_good_to_bad=0.85,
        p_bad_to_good=0.2,
        p_loss_good=0.01,
        p_loss_bad=0.9,
        seed=None,
    ):
        self.p_good_to_bad = p_good_to_bad
        self.p_bad_to_good = p_bad_to_good
        self.p_loss_good = p_loss_good
        self.p_loss_bad = p_loss_bad
        self.state = "G"  # Prolly better if I made this an enum but yolo
        self.rng = np.random.default_rng(seed)

    def should_drop(self):
        if self.state == "G":
            lost = random.random() < self.p_loss_good

            if random.random() < self.p_good_to_bad:
                self.state = "B"
        else:
            lost = random.random() < self.p_loss_bad
            if random.random() < self.p_bad_to_good:
                self.state = "G"
        return lost


@dataclass
class ActiveNode:
    id: int
    name: str
    rating: float
    is_active: bool = True
    node_lv_nominal: float = 415
    is_transformer_node: bool = True
    node_mv_nominal: float = 11.0
    node_object: object = None
    comment: str = ""

    is_online: bool = False

    vm_pu: Optional[float] = None
    va_degree: Optional[float] = None
    p_mw: Optional[float] = None
    q_mvar: Optional[float] = None

    gilbert_elliott_simulator: GilbertElliottSimulator = None
    valid_readings = []

    def serialise(self):
        _json = {}

        _json["id"] = str(self.id)
        _json["name"] = self.name
        _json["rating"] = assure_float(self.rating)
        _json["voltage"] = assure_float(self.vm_pu) * self.node_mv_nominal
        _json["p_kw"] = assure_float(self.p_mw) * 1000
        _json["q_kvar"] = assure_float(self.q_mvar) * 1000
        _json["phase"] = assure_float(self.va_degree)
        _json["online"] = self.is_online

        return _json

    def predict_next(self):
        return self.valid_readings[-1]

    def set_ge_model(self, model):
        self.gilbert_elliott_simulator = model

    def should_drop_current_reading(self) -> bool:
        if not self.gilbert_elliott_simulator:
            raise RuntimeError(
                f"Attempted to simulate network conditions, but no simulation model was specified. Node={self.id}"
            )

        return self.gilbert_elliott_simulator.should_drop()

    def add_valid_reading(self, p, q):
        self.valid_readings.append((p, q))


def update_nodes_from_results(nodes: Dict[int, ActiveNode], res_bus) -> None:
    for id, node in nodes.items():
        if id in res_bus.index:
            row = res_bus.loc[id]
            node.vm_pu = round(float(row["vm_pu"]), 5)
            node.va_degree = round(float(row["va_degree"]), 5)
            node.p_mw = round(float(row["p_mw"]), 5)
            node.q_mvar = round(float(row["q_mvar"]), 5)


def update_lines_from_results(lines: Dict[int, Line], res_line) -> None:
    for id, line in lines.items():
        if id in res_line.index:
            row = res_line.loc[id]
            line.loading_percent = round(float(row["loading_percent"]), 5)
            line.i_from_ka = round(float(row["i_from_ka"]), 5)
            line.i_to_ka = round(float(row["i_to_ka"]), 5)
            line.p_from_mw = round(float(row["p_from_mw"]), 5)
            line.q_from_mvar = round(float(row["q_from_mvar"]), 5)
            line.p_to_mw = round(float(row["p_to_mw"]), 5)
            line.q_to_mvar = round(float(row["q_to_mvar"]), 5)
            line.pl_mw = round(float(row["pl_mw"]), 5)
            line.ql_mvar = round(float(row["ql_mvar"]), 5)


def load_nodes_from_disk(node_file: Path) -> Dict[int, ActiveNode]:

    nodes = {}
    with open(node_file, "r") as nodes_file:
        reader = csv.reader(nodes_file)
        next(reader)  # Skip header

        for bus_name, transformer_rating, data_link_key, is_active, notes in reader:

            # Janky ass error checking, make this cleaner if have time
            try:
                node = ActiveNode(
                    int(data_link_key),
                    bus_name,
                    float(transformer_rating),
                    is_active=string_to_bool(is_active),
                    comment=notes,
                )
                node.set_ge_model(GilbertElliottSimulator(seed=int(data_link_key)))
            except ValueError as err:
                raise ValueError(
                    f"The bus definition for {bus_name}:{data_link_key} is malformed. Check the values for all fields. TRACE: {err}"
                )

            nodes[int(data_link_key)] = node

    return nodes


def load_lines_from_disk(line_file: Path) -> Dict[int, Line]:
    lines = {}
    with open(line_file, "r") as lines_file:
        reader = csv.reader(lines_file)
        next(reader)  # Skip header
        for to_node, from_node, length, type, data_link_key, is_active, notes in reader:

            line_name = f"FROM: {from_node}, TO: {to_node}"

            # Janky ass error checking, make this cleaner if have time
            try:
                line = Line(
                    int(data_link_key),
                    line_name,
                    from_node,
                    to_node,
                    float(length),
                    type,
                    string_to_bool(is_active),
                    comment=notes,
                )
            except ValueError:
                raise ValueError(
                    f"The line definition for {line_name}:{data_link_key} is malformed. Check the values for all fields"
                )

            lines[int(data_link_key)] = line

    return lines


def build_network(
    nodes: Dict[int, ActiveNode], lines: Dict[int, Line], cable_types: List[LineType]
):
    """
    Construct a pandapower network from the specified nodes and lines. Warning: This function mutates
    the state of the nodes and lines by linking them to the pandapower network elements
    """
    net = pp.create_empty_network()

    # Forcefully create slack bus with ID: 0
    nodes[0] = ActiveNode(0, "slack", 0)

    for cable_type in cable_types:
        pp.create_std_type(
            net,
            {
                "c_nf_per_km": cable_type.c_nf_per_km,
                "r_ohm_per_km": cable_type.r_ohm_per_km,
                "x_ohm_per_km": cable_type.x_ohm_per_km,
                "max_i_ka": cable_type.max_i_ka,
                "type": cable_type.type,
                "q_mm2": cable_type.q_mm2,
                "alpha": cable_type.alpha,
            },
            name=cable_type.name,
            element="line",
        )

    node_name_lookup_cache = {}

    total_rating = 0

    for id, node in nodes.items():
        pp_bus = pp.create_bus(
            net, vn_kv=node.node_mv_nominal, name=node.name, index=id
        )
        node.node_object = pp_bus

        total_rating += node.rating

        if node.name in node_name_lookup_cache:
            raise ValueError(
                f"Duplicate node names detected. Cannot have two nodes with the same name={node.name}"
            )

        node_name_lookup_cache[node.name] = node.id

    # Now that it has been created, attach the slack bus to the external grid
    pp.create_ext_grid(net, nodes[0].node_object)

    for id, line in lines.items():

        node_from = None
        node_to = None

        if line.line_from in node_name_lookup_cache:
            node_from = nodes[node_name_lookup_cache[line.line_from]]
        else:
            raise ValueError(f"No existing node for name={line.line_from}")

        if line.line_to in node_name_lookup_cache:
            node_to = nodes[node_name_lookup_cache[line.line_to]]
        else:
            raise ValueError(f"No existing node for name={line.line_to}")

        # We only tell pandapower about active lines
        if line.is_active:
            pp_line = pp.create_line(
                net,
                from_bus=node_from.node_object,
                to_bus=node_to.node_object,
                length_km=line.length / 1000,
                std_type=line.type,
                name=line.name,
            )

            line.line_object = pp_line

    return net, total_rating


def clear_network_loads(net: pd.DataFrame):
    """
    Helper function which clears all load definitions from a pandapower network
    """
    net.load.drop(net.load.index, inplace=True)
