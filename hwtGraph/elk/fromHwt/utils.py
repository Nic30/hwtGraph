from typing import Union, List

from hwt.hdl.assignment import Assignment
from hwt.hdl.constants import INTF_DIRECTION
from hwt.hdl.operator import Operator
from hwt.hdl.operatorDefs import AllOps
from hwt.hdl.portItem import PortItem
from hwt.hdl.types.defs import BIT
from hwt.hdl.value import Value
from hwt.pyUtils.uniqList import UniqList
from hwt.serializer.hwt.serializer import HwtSerializer
from hwt.synthesizer.interface import Interface
from hwt.synthesizer.rtlLevel.mainBases import RtlSignalBase
from hwtGraph.elk.containers.constants import PortType, PortSide, PortConstraints
from hwtGraph.elk.containers.lEdge import LEdge
from hwtGraph.elk.containers.lNode import LayoutExternalPort, LNode
from hwtGraph.elk.containers.lPort import LPort


class NetCtxs(dict):
    def applyConnections(self, root):
        for net in set(self.values()):
            for src in net.drivers:
                for dst in net.endpoints:
                    root.addEdge(src, dst)

    def joinNetsByKey(self, k0, k1):
        v0, _ = self.getDefault(k0)
        v1, _ = self.getDefault(k1)
        if v0 is v1:
            return v0

        v0.extend(v1)
        v0.actualKeys.extend(v1.actualKeys)

        self[k1] = v0
        return v0

    def joinNetsByKeyVal(self, k0, v1):
        v0, _ = self.getDefault(k0)
        if v0 is v1:
            return v0

        v0.extend(v1)
        v0.actualKeys.extend(v1.actualKeys)

        for k in v1.actualKeys:
            self[k] = v0

        return v0

    def joinNetsByValKey(self, v0, k1):
        v1, _ = self.getDefault(k1)
        if v0 is v1:
            return v0

        v0.extend(v1)
        v0.actualKeys.extend(v1.actualKeys)

        for k in v1.actualKeys:
            self[k] = v0

        return v0

    def getDefault(self, k):
        try:
            return self[k], True
        except KeyError:
            v = self[k] = NetCtx(self, k)
            return v, False


class NetCtx():
    def __init__(self, others: NetCtxs, actualKey):
        self.actualKeys = [actualKey, ]
        self.others = others
        self.drivers = UniqList()
        self.endpoints = UniqList()

    def extend(self, other):
        self.drivers.extend(other.drivers)
        self.endpoints.extend(other.endpoints)

    def addDriver(self, d):
        if isinstance(d, RtlSignalBase):
            return self.others.joinNetsByKeyVal(d, self)
        else:
            return self.drivers.append(d)

    def addEndpoint(self, ep):
        if isinstance(ep, RtlSignalBase):
            return self.others.joinNetsByValKey(self, ep)
        else:
            return self.endpoints.append(ep)


def toStr(obj):
    """
    Convert hwt object to string
    """
    return HwtSerializer.asHdl(obj, HwtSerializer.getBaseContext())


def getParentUnit(intf):
    while isinstance(intf._parent, Interface):
        intf = intf._parent

    return intf._parent


def PortTypeFromDir(direction):
    if direction == INTF_DIRECTION.SLAVE:
        return PortType.INPUT
    elif direction == INTF_DIRECTION.MASTER:
        return PortType.OUTPUT
    else:
        raise ValueError(direction)


def originObjOfPort(intf):
    d = intf._direction
    d = PortTypeFromDir(d)

    if intf._interfaces:
        origin = intf
    elif d == PortType.OUTPUT:
        # has hierarchy
        origin = intf._sigInside.endpoints[0]
        assert isinstance(origin, PortItem), (intf, origin)
    elif d == PortType.INPUT:
        origin = intf._sigInside.drivers[0]
        assert isinstance(origin, PortItem), (intf, origin)
    else:
        raise ValueError(d)

    return origin


def _addPort(n: LNode, lp: LPort, intf: Interface,
             reverseDirection=False):
    """
    add port to LPort for interface
    """
    origin = originObjOfPort(intf)
    d = intf._direction
    d = PortTypeFromDir(d)

    if reverseDirection:
        d = PortType.opposite(d)

    new_lp = LPort(lp, d, lp.side, name=intf._name)
    new_lp.originObj = origin
    if intf._interfaces:
        for child_intf in intf._interfaces:
            _addPort(n, new_lp, child_intf,
                     reverseDirection=reverseDirection)

    lp.children.append(new_lp)
    new_lp.parent = lp
    if n._node2lnode is not None:
        n._node2lnode[origin] = new_lp

    return new_lp


def addPortToLNode(ln: LNode, intf: Interface, reverseDirection=False):
    origin = originObjOfPort(intf)

    d = intf._direction
    d = PortTypeFromDir(d)
    if reverseDirection:
        d = PortType.opposite(d)

    p = LNodeAddPortFromHdl(ln, origin,
                            d,
                            intf._name)
    for _intf in intf._interfaces:
        _addPort(ln, p, _intf, reverseDirection=reverseDirection)


def addPort(n: LNode, intf: Interface):
    """
    Add LayoutExternalPort for interface
    """
    d = PortTypeFromDir(intf._direction)
    ext_p = LayoutExternalPort(
        n, intf._name, d, node2lnode=n._node2lnode)
    ext_p.originObj = originObjOfPort(intf)
    n.children.append(ext_p)
    addPortToLNode(ext_p, intf, reverseDirection=True)

    return ext_p


def getSinglePort(ports: List[LPort]) -> LEdge:
    assert len(ports) == 1, ports
    return ports[0]


def removeEdge(edge: LEdge):
    edge.dst.incomingEdges.remove(edge)
    edge.src.outgoingEdges.remove(edge)
    edge.dst = edge.dstNode = edge.src = edge.srcNode = None


def isUselessTernary(op):
    if op.operator == AllOps.TERNARY:
        ifTrue = op.operands[1]
        ifFalse = op.operands[2]
        if ifTrue._dtype == BIT and ifFalse._dtype == BIT:
            try:
                return bool(ifTrue) and not bool(ifFalse)
            except Exception:
                pass
    return False


def isUselessEq(op: Operator):
    if op.operator == AllOps.EQ:
        o0, o1 = op.operands
        if o0._dtype.bit_length() == 1:
            try:
                if bool(o1):
                    return True
            except Exception:
                pass
    return False


def ternaryAsSimpleAssignment(root, op):
    originObj = Assignment(op.operands[0], op.result, virtualOnly=True)
    u = root.addNode(originObj=originObj, name="Assignment")
    u.addPort("", PortType.OUTPUT, PortSide.EAST)
    u.addPort("",  PortType.INPUT,  PortSide.WEST)
    return u


def LNodeAddPortFromHdl(node, origin: Union[Interface, PortItem],
                        direction: PortType,
                        name: str):
    if direction == PortType.OUTPUT:
        side = PortSide.EAST
    elif direction == PortType.INPUT:
        side = PortSide.WEST
    else:
        raise ValueError(direction)

    p = node.addPort(name, direction, side)
    p.originObj = origin
    if node._node2lnode is not None:
        node._node2lnode[origin] = p
    return p


def ValueAsLNode(root: LNode, val: Value):
    u = root.addNode(originObj=val, bodyText=toStr(
        val), portConstraint=PortConstraints.FREE)
    u.addPort(None, PortType.OUTPUT, PortSide.EAST)
    return u
