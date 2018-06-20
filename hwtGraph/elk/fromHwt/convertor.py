from typing import Optional

from hwt.hdl.portItem import PortItem
from hwt.synthesizer.unit import Unit
from hwtGraph.elk.containers.lNode import LNode

from hwtGraph.elk.fromHwt.statementRenderer import StatementRenderer
from hwtGraph.elk.fromHwt.statementRendererUtils import addStmAsLNode, VirtualLNode
from hwtGraph.elk.fromHwt.utils import addPortToLNode, addPort, NetCtxs


def sortStatementPorts(root):
    # [TODO]
    pass


def UnitToLNode(u: Unit, node: Optional[LNode]=None,
                toL: Optional[dict]=None,
                optimizations=[]) -> LNode:
    """
    Build LNode instance from Unit instance

    :attention: unit has to be synthesized
    """
    if toL is None:
        toL = {}
    if node is None:
        root = LNode(name=u._name, originObj=u, node2lnode=toL)
    else:
        root = node

    stmPorts = {}

    # {RtlSignal: NetCtx}
    netCtx = NetCtxs()

    # create subunits
    for su in u._units:
        n = root.addNode(name=su._name, originObj=su)
        UnitToLNode(su, n, toL, optimizations)
        for intf in su._interfaces:
            addPortToLNode(n, intf)

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
    for s in u._ctx.signals:
        if not s.hidden:
            net, _ = netCtx.getDefault(s)
            for e in s.endpoints:
                if isinstance(e, PortItem):
                    net.addEndpoint(toL[e])

            for d in s.drivers:
                if isinstance(d, PortItem):
                    net.addDriver(toL[d])
            # connectSignalToStatements(
            #    s, toL, stmPorts, root, reducedStatements)

    netCtx.applyConnections(root)

    for opt in optimizations:
        opt(root)

    return root
