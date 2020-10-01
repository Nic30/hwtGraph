from typing import List

from hwt.hdl.statement import HdlStatement
from hwtGraph.elk.containers.lNode import LNode
from hwtGraph.elk.containers.lPort import LPort
from hwt.serializer.utils import RtlSignal_sort_key


def _sortPorts(portList: List[LPort]):
    return sorted(portList, key=lambda x: RtlSignal_sort_key(x.originObj))


def sortStatementPorts(root: LNode):
    if isinstance(root.originObj, HdlStatement):
        if root.west:
            root.west = _sortPorts(root.west)
        if root.east:
            root.east = _sortPorts(root.east)
        if root.north:
            root.north = _sortPorts(root.north)
        if root.south:
            root.south = _sortPorts(root.south)
    
    for c in root.children:
        sortStatementPorts(c)
        
