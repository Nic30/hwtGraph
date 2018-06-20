from typing import List

from hwtGraph.elk.containers.lNode import LNode
from hwtGraph.elk.containers.lPort import LPort


def flattenPort(port: LPort):
    """
    Flatten hierarchical ports
    """
    yield port
    if port.children:
        for ch in port.children:
            yield from flattenPort(ch)
        port.children.clear()


def _flattenPortsSide(side: List[LNode]) -> List[LNode]:
    """
    Flatten hierarchical ports on node side
    """
    new_side = []
    for i in side:
        for new_p in flattenPort(i):
            new_side.append(new_p)
    return new_side


def flattenPorts(root: LNode):
    """
    Flatten ports to simplify layout generation

    :attention: children property is destroyed, parent property stays same
    """
    for u in root.children:
        u.west = _flattenPortsSide(u.west)
        u.east = _flattenPortsSide(u.east)
        u.north = _flattenPortsSide(u.north)
        u.south = _flattenPortsSide(u.south)
