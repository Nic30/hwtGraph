from io import StringIO
from typing import Union, List, Optional

from hwt.constants import INTF_DIRECTION
from hwt.hwIO import HwIO
from hwt.hwModule import HwModule
from hwt.hdl.const import HConst
from hwt.hdl.operator import HOperatorNode
from hwt.hdl.operatorDefs import HwtOps
from hwt.hdl.portItem import HdlPortItem
from hwt.hdl.statements.assignmentContainer import HdlAssignmentContainer
from hwt.hdl.types.defs import BIT
from hwt.serializer.hwt import HwtSerializer
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


def getParentHwModule(hwIO: Union[HwIO, HwModule]) -> Optional[HwModule]:
    while isinstance(hwIO._parent, HwIO):
        hwIO = hwIO._parent

    return hwIO._parent


def PortTypeFromDir(direction: INTF_DIRECTION):
    if direction == INTF_DIRECTION.SLAVE:
        return PortType.INPUT
    elif direction == INTF_DIRECTION.MASTER:
        return PortType.OUTPUT
    else:
        raise ValueError(direction)


def originObjOfPort(hwIO: HwIO):
    if hwIO._hwIOs:
        # has hierarchy
        origin = hwIO
    else:
        origin = hwIO._hdlPort
        assert origin is not None

    return origin


def _addPort(n: LNode, lp: LPort, hwIO: HwIO,
             reverseDirection=False):
    """
    add port to LPort for interface
    """
    origin = originObjOfPort(hwIO)
    d = hwIO._direction
    d = PortTypeFromDir(d)

    if reverseDirection:
        d = PortType.opposite(d)

    new_lp = LPort(lp, d, lp.side, name=hwIO._name, originObj=origin)
    if hwIO._hwIOs:
        for cHwIO in hwIO._hwIOs:
            _addPort(n, new_lp, cHwIO,
                     reverseDirection=reverseDirection)

    lp.children.append(new_lp)
    new_lp.parent = lp
    if n._node2lnode is not None:
        n._node2lnode[origin] = new_lp

    return new_lp


def addPortToLNode(ln: LNode, hwIO: HwIO, reverseDirection=False):
    origin = originObjOfPort(hwIO)

    d = hwIO._direction
    if hwIO._masterDir == DIRECTION.IN:
        d = INTF_DIRECTION.opposite(d)
    d = PortTypeFromDir(d)
    if reverseDirection:
        d = PortType.opposite(d)

    p = LNodeAddPortFromHdl(ln, origin,
                            d,
                            hwIO._name)
    for cHwIO in hwIO._hwIOs:
        _addPort(ln, p, cHwIO, reverseDirection=reverseDirection)

    return p


def addPort(n: LNode, hwIO: HwIO):
    """
    Add LayoutExternalPort for interface and LPort instances to this LNode
    """
    d = hwIO._direction
    if hwIO._masterDir == DIRECTION.IN:
        d = INTF_DIRECTION.opposite(d)

    d = PortTypeFromDir(d)
    ext_p = LayoutExternalPort(
        n, name=hwIO._name, direction=d,
        node2lnode=n._node2lnode,
        originObj=originObjOfPort(hwIO))
    n.children.append(ext_p)
    addPortToLNode(ext_p, hwIO, reverseDirection=True)
    return ext_p


def getSinglePort(ports: List[LPort]) -> LEdge:
    assert len(ports) == 1, ports
    return ports[0]


def isUselessTernary(op: HOperatorNode):
    if op.operator == HwtOps.TERNARY:
        ifTrue = op.operands[1]
        ifFalse = op.operands[2]
        if ifTrue._dtype == BIT and ifFalse._dtype == BIT:
            try:
                return bool(ifTrue) and not bool(ifFalse)
            except Exception:
                pass

    return False


def isUselessEq(op: HOperatorNode):
    if op.operator == HwtOps.EQ:
        o0, o1 = op.operands
        if o0._dtype.bit_length() == 1:
            try:
                if bool(o1):
                    return True
            except Exception:
                pass

    return False


def ternaryAsSimpleAssignment(root, op):
    originObj = HdlAssignmentContainer(op.operands[0], op.result, virtualOnly=True)
    m = root.addNode(originObj=originObj, name="Assignment", cls="HOperatorNode")
    m.addPort("", PortType.OUTPUT, PortSide.EAST)
    m.addPort("", PortType.INPUT, PortSide.WEST)
    return m


def LNodeAddPortFromHdl(node, origin: Union[HwIO, HdlPortItem],
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


def ValueAsLNode(root: LNode, val: HConst):
    n = root.addNode(originObj=val,
                     cls="HOperatorNode",
                     bodyText=toStr(val),
                     portConstraint=PortConstraints.FREE)
    n.addPort(None, PortType.OUTPUT, PortSide.EAST)
    return n


