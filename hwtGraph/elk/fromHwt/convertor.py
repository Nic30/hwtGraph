from typing import Optional

from hwt.hdl.constants import INTF_DIRECTION
from hwt.hdl.portItem import HdlPortItem
from hwt.synthesizer.unit import Unit
from hwtGraph.elk.containers.constants import PortType, PortSide
from hwtGraph.elk.containers.lNode import LNode
from hwtGraph.elk.fromHwt.statementRenderer import StatementRenderer
from hwtGraph.elk.fromHwt.statementRendererUtils import addStmAsLNode, VirtualLNode
from hwtGraph.elk.fromHwt.utils import addPortToLNode, addPort, NetCtxs,\
    originObjOfPort


def sortStatementPorts(root):
    # [TODO]
    pass


def UnitToLNode(u: Unit, node: Optional[LNode]=None,
                toL: Optional[dict]=None,
                optimizations=[]) -> LNode:
    """
    Build LNode instance (a graph) from Unit instance (a RTL graph)

    :attention: unit has to be synthesized
    """
    if toL is None:
        toL = {}

    if u._shared_component_with:
        # this component does not have body generated and uses a different
        # component
        shared_comp, _, _ = u._shared_component_with
        shared_node = toL[shared_comp]
        for intf in u._interfaces:
            addPortToLNode(node, intf)
        node._shared_component_with = shared_node
        return

    if node is None:
        root = LNode(name=u._name, originObj=u, node2lnode=toL)
    else:
        root = node

    stmPorts = {}

    # {RtlSignal: NetCtx}
    netCtx = NetCtxs(root)

    # create subunits
    for su in u._units:
        n = root.addNode(name=su._name, cls="Unit", originObj=su)
        UnitToLNode(su, n, toL, optimizations)

    # create subunits from statements
    for stm in u._ctx.statements:
        n = addStmAsLNode(root, stm, stmPorts, netCtx)

    # create ports for this unit
    for intf in u._interfaces:
        addPort(root, intf)

    # render content of statements
    for stm in u._ctx.statements:
        n = toL.get(stm, None)
        if n is not None:
            if isinstance(n, VirtualLNode):
                # statement is not in wrap and does not need any port context
                p = None
            else:
                # statement is in wrap and needs a port context
                # to resolve port connections to wrap
                p = stmPorts[n]

            r = StatementRenderer(n, toL, p, netCtx)
            r.renderContent()

    # connect nets inside this unit
    for s in sorted(u._ctx.signals, key=lambda x: (x.name, x._instId)):
        if not s.hidden:
            net, _ = netCtx.getDefault(s)
            for e in s.endpoints:
                if isinstance(e, HdlPortItem):
                    net.addEndpoint(toL[e])

            for d in s.drivers:
                if isinstance(d, HdlPortItem):
                    net.addDriver(toL[d])

    netCtx.applyConnections(root)

    for opt in optimizations:
        opt(root)

    isRootOfWholeGraph = root.parent is None
    if not isRootOfWholeGraph:
        for intf in u._interfaces:
            # connect my external port to port on my container on parent
            # also override toL to use this new port
            ext_p = toL[originObjOfPort(intf)].parentNode
            nodePort = addPortToLNode(root, intf)
            # connect this node which represents port to port of this node
            if intf._direction == INTF_DIRECTION.SLAVE:
                src = nodePort
                dst = ext_p.addPort("", PortType.INPUT, PortSide.WEST)
            else:
                src = ext_p.addPort("", PortType.OUTPUT, PortSide.EAST)
                dst = nodePort

            root.addEdge(src, dst, name=repr(intf), originObj=intf)

    return root
