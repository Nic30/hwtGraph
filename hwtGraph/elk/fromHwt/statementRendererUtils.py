from typing import Dict, List

from hwt.hdl.assignment import Assignment
from hwt.hdl.operator import isConst
from hwt.hdl.statement import HdlStatement
from hwt.synthesizer.rtlLevel.mainBases import RtlSignalBase
from hwtGraph.elk.containers.constants import PortType, PortSide
from hwtGraph.elk.containers.lNode import LNode
from hwtGraph.elk.fromHwt.netCtx import NetCtxs
from hwtGraph.elk.fromHwt.utils import ValueAsLNode, toStr


def walkStatementsForSig(statements: List[HdlStatement], s: RtlSignalBase):
    assert isinstance(statements, list)
    for stm in statements:
        if s in stm._outputs:
            assert isinstance(stm._outputs, list)
            yield stm


class Signal2stmPortCtx():

    def __init__(self, stmNode: LNode):
        self.stmNode = stmNode
        self.data = {}

    def getInside(self, sig: RtlSignalBase, portType: PortType):
        p = self.data.get((sig, portType), None)
        if not isinstance(self.stmNode, VirtualLNode):
            if p is None:
                return self.register(sig, portType)
            else:
                return p

        n = p.parentNode
        if p.direction == PortType.INPUT:
            return n.east[0]
        elif p.direction == PortType.OUTPUT:
            return n.west[0]
        else:
            raise NotImplementedError()

    def getOutside(self, sig: RtlSignalBase, portType: PortType):
        return self.data[(sig, portType)]

    def register(self, sig: RtlSignalBase, portType: PortType):
        k = (sig, portType)
        p = self.data.get(k, None)
        if p is not None:
            assert p.direction == portType, p
            return p

        if portType == PortType.INPUT:
            side = PortSide.WEST
        elif portType == portType.OUTPUT:
            side = PortSide.EAST
        else:
            raise ValueError(portType)

        p = self.stmNode.addPort(sig.name, portType, side, originObj=sig)
        self.data[k] = p
        return p


class VirtualLNode():

    def __init__(self, parent: LNode, stm: HdlStatement):
        self.originObj = stm
        self.parent = parent
        self.addNode = parent.addNode
        self.addEdge = parent.addEdge

    def __repr__(self):
        return "<VirtualLNode for %r>" % self.originObj


def addStmAsLNode(root: LNode, stm: HdlStatement,
                  stmPorts: Dict[LNode, Signal2stmPortCtx],
                  netCtx: NetCtxs) -> LNode:
    toL = root._node2lnode
    isOnlyAssig = isinstance(stm, Assignment)
    if isOnlyAssig and not stm.indexes and isConst(stm.src):
        # is only constant
        n = ValueAsLNode(root, stm.src)
        ctx, _ = netCtx.getDefault(stm.dst)
        ctx.addDriver(n.east[0])

    elif isOnlyAssig:
        # inline operators in assignment to parent node
        n = toL[stm] = VirtualLNode(root, stm)

    else:
        # render content of statement into container node
        bodyText = toStr(stm)
        n = root.addNode(
            originObj=stm,
            cls="Process",
            bodyText=bodyText)

        stmPorts[n] = Signal2stmPortCtx(n)

    return n
