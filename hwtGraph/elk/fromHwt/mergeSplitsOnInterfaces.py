from typing import Union, List, Tuple

from hwt.pyUtils.arrayQuery import single, DuplicitValueExc, NoValueExc
from hwtGraph.elk.containers.constants import PortType, PortSide
from hwtGraph.elk.containers.lEdge import LEdge
from hwtGraph.elk.containers.lNode import LNode
from hwtGraph.elk.containers.lPort import LPort
from hwtGraph.elk.fromHwt.utils import removeEdge


class PortConnectionCtx(list):
    pass


class MergeSplitsOnInterfacesCtx():
    def __init__(self):
        self.items = {}

    def register(self, rootPort, splitOrConcat: LNode, mainEdge: LEdge):
        try:
            c = self.items[rootPort]
        except KeyError:
            c = PortConnectionCtx()
            self.items[rootPort] = c
        c.append((splitOrConcat, mainEdge))

    def iterPortSplits(self):
        for srcPort, splitsAndConcats in self.items.items():
            if len(splitsAndConcats) == portCnt(srcPort):
                yield srcPort, splitsAndConcats


def getRootIntfPort(port: LPort):
    """
    :return: most top port which contains this port
    """
    while True:
        if isinstance(port.parent, LNode):
            return port
        else:
            port = port.parent


def portCnt(port):
    """
    recursively count number of ports without children
    """
    if port.children:
        return sum(map(lambda p: portCnt(p), port.children))
    else:
        return 1


def _copyPort(port: LPort, targetParent: Union[LPort], reverseDirection):
    """
    add port to LPort for interface
    """
    d = port.direction
    side = port.side
    if reverseDirection:
        d = PortType.opposite(d)
        side = PortSide.opposite(side)

    newP = LPort(targetParent.getNode(), d, side, name=port.name)
    if isinstance(targetParent, LPort):
        targetParent.children.append(newP)
        newP.parent = targetParent
    else:
        targetParent.getPortSideView(side).append(newP)

    for ch in port.children:
        _copyPort(ch, newP, reverseDirection)

    return newP


def copyPort(port, targetLNode, reverseDir, topPortName=None):
    """
    Create identical port on targetNode
    """
    newP = _copyPort(port, targetLNode, reverseDir)

    if topPortName is not None:
        newP.name = topPortName

    return newP


def walkSignalPorts(rootPort: LPort):
    """
    recursively walk ports without any children
    """
    if rootPort.children:
        for ch in rootPort.children:
            yield from walkSignalPorts(ch)
    else:
        yield rootPort


def reconnectPorts(root: LNode, srcPort: LPort,
                   oldSplits: List[Tuple[LNode, LEdge]],
                   newSplitNode: LNode):
    """
    :ivar root: top LNode instance in which are nodes and links stored
    :ivar srcPort: for SLICE it is port which is connected to input of SLICE node
        for CONCAT it is port which is connected to output of CONCAT
    :ivar oldSplits: list of tuples (node, edge) which should be disconnected from graph
    :ivar newSplitNode: new node which should be connected to graph
    """
    # sort oldSplit nodes because they are not in same order as signals on
    # ports
    mainPortSignals = list(walkSignalPorts(srcPort))
    portOrder = {p: i for i, p in enumerate(mainPortSignals)}
    isOneToN = len(newSplitNode.west) == 1

    def portSortKey(x):
        n, e = x
        if e.dstNode is n:
            return portOrder[e.src]
        elif e.srcNode is n:
            return portOrder[e.dst]
        else:
            raise ValueError("Edge not connected to split node", e, n)

    oldSplits.sort(key=portSortKey)
    newSplitPorts = [walkSignalPorts(p) for p in
                     (newSplitNode.east if isOneToN else newSplitNode.west)]

    if isOneToN:
        newMainPort = newSplitNode.west[0]
    else:
        newMainPort = newSplitNode.east[0]

    for mainPort, splitInp, (oldSplitNode, e) in zip(
            mainPortSignals,
            walkSignalPorts(newMainPort),
            oldSplits):
        assert mainPort.direction != splitInp.direction, (
            mainPort, splitInp)

        # reconnect edge from src port to split node
        assert (e.src is mainPort and e.dstNode is oldSplitNode)\
            or (e.dst is mainPort and e.srcNode is oldSplitNode), e
        removeEdge(e)

        _newSplitPorts = [next(p) for p in newSplitPorts]
        # reconnect part from split node to other target nodes
        if oldSplitNode.name == "CONCAT":
            root.addEdge(splitInp, mainPort,
                         originObj=e.originObj)

            for oldP, newP in zip(oldSplitNode.west, _newSplitPorts):
                for e in list(oldP.incomingEdges):
                    root.addEdge(e.src, newP, originObj=e.originObj)
                    removeEdge(e)

        elif oldSplitNode.name == "SLICE":
            root.addEdge(mainPort, splitInp,
                         originObj=e.originObj)

            for oldP, newP in zip(oldSplitNode.east, reversed(_newSplitPorts)):
                for e in list(oldP.outgoingEdges):
                    root.addEdge(newP, e.dst, originObj=e.originObj)
                    removeEdge(e)
        else:
            raise ValueError(oldSplitNode)

        root.children.remove(oldSplitNode)


def mergeSplitsOnInterfaces(root: LNode):
    """
    collect all split/concatenation nodes and group them by target interface
    """
    for ch in root.children:
        if ch.children:
            mergeSplitsOnInterfaces(ch)

    ctx = MergeSplitsOnInterfacesCtx()
    for ch in root.children:
        srcPort = None
        try:
            if ch.name == "CONCAT":
                p = single(ch.east, lambda x: True)
                e = single(p.outgoingEdges, lambda x: True)
                srcPort = e.dst
            elif ch.name == "SLICE":
                p = single(ch.west, lambda x: True)
                e = single(p.incomingEdges, lambda x: True)
                srcPort = e.src
        except (DuplicitValueExc, NoValueExc):
            continue

        if srcPort is not None and isinstance(srcPort.parent, LPort):
            # only for non primitive ports
            rootPort = getRootIntfPort(srcPort)
            ctx.register(rootPort, ch, e)

    # join them if it is possible
    for srcPort, splitsAndConcats in ctx.iterPortSplits():
        if len(splitsAndConcats) <= 1:
            continue

        name = "SPLIT" if srcPort.direction == PortType.OUTPUT else "CONCAT"
        newSplitNode = root.addNode(name)
        copyPort(srcPort, newSplitNode, True, "")
        n = splitsAndConcats[0][0]
        for i in range(max(len(n.west),
                           len(n.east))):
            copyPort(
                srcPort, newSplitNode,
                False, "[%d]" % i)

        reconnectPorts(root, srcPort, splitsAndConcats,
                       newSplitNode)
