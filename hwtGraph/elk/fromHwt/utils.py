from io import StringIO
from typing import Union, List

from hwt.hdl.assignment import Assignment
from hwt.hdl.constants import INTF_DIRECTION
from hwt.hdl.operator import Operator, isConst
from hwt.hdl.operatorDefs import AllOps
from hwt.hdl.portItem import HdlPortItem
from hwt.hdl.types.defs import BIT
from hwt.hdl.value import HValue
from hwt.pyUtils.uniqList import UniqList
from hwt.serializer.hwt import HwtSerializer
from hwt.synthesizer.interface import Interface
from hwt.synthesizer.rtlLevel.mainBases import RtlSignalBase
from hwt.synthesizer.unit import Unit
from hwtGraph.elk.containers.constants import PortType, PortSide, \
    PortConstraints
from hwtGraph.elk.containers.lEdge import LEdge
from hwtGraph.elk.containers.lNode import LayoutExternalPort, LNode
from hwtGraph.elk.containers.lPort import LPort
from ipCorePackager.constants import DIRECTION


def toStr(obj):
    """
    Convert hwt object to string
    """
    to_hdl = HwtSerializer.TO_HDL_AST()
    to_hdl.debug = True
    hdl = to_hdl.as_hdl(obj)
    buff = StringIO()
    ser = HwtSerializer.TO_HDL(buff)
    ser.visit_iHdlObj(hdl)
    return buff.getvalue()


def getParentUnit(intf: Union[Interface, Unit]):
    while isinstance(intf._parent, Interface):
        intf = intf._parent

    return intf._parent


def PortTypeFromDir(direction: INTF_DIRECTION):
    if direction == INTF_DIRECTION.SLAVE:
        return PortType.INPUT
    elif direction == INTF_DIRECTION.MASTER:
        return PortType.OUTPUT
    else:
        raise ValueError(direction)


def originObjOfPort(intf: Interface):
    if intf._interfaces:
        # has hierarchy
        origin = intf
    else:
        origin = intf._hdl_port
        assert origin is not None

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

    new_lp = LPort(lp, d, lp.side, name=intf._name, originObj=origin)
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
    if intf._masterDir == DIRECTION.IN:
        d = INTF_DIRECTION.opposite(d)
    d = PortTypeFromDir(d)
    if reverseDirection:
        d = PortType.opposite(d)

    p = LNodeAddPortFromHdl(ln, origin,
                            d,
                            intf._name)
    for _intf in intf._interfaces:
        _addPort(ln, p, _intf, reverseDirection=reverseDirection)

    return p


def addPort(n: LNode, intf: Interface):
    """
    Add LayoutExternalPort for interface and LPort instances to this LNode
    """
    d = intf._direction
    if intf._masterDir == DIRECTION.IN:
        d = INTF_DIRECTION.opposite(d)

    d = PortTypeFromDir(d)
    ext_p = LayoutExternalPort(
        n, name=intf._name, direction=d,
        node2lnode=n._node2lnode,
        originObj=originObjOfPort(intf))
    n.children.append(ext_p)
    addPortToLNode(ext_p, intf, reverseDirection=True)
    return ext_p


def getSinglePort(ports: List[LPort]) -> LEdge:
    assert len(ports) == 1, ports
    return ports[0]


def isUselessTernary(op: Operator):
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
    u = root.addNode(originObj=originObj, name="Assignment", cls="Operator")
    u.addPort("", PortType.OUTPUT, PortSide.EAST)
    u.addPort("", PortType.INPUT, PortSide.WEST)
    return u


def LNodeAddPortFromHdl(node, origin: Union[Interface, HdlPortItem],
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


def ValueAsLNode(root: LNode, val: HValue):
    u = root.addNode(originObj=val,
                     cls="Operator",
                     bodyText=toStr(val),
                     portConstraint=PortConstraints.FREE)
    u.addPort(None, PortType.OUTPUT, PortSide.EAST)
    return u


