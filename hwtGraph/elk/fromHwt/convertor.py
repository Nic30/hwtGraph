from typing import Optional

from hwt.constants import INTF_DIRECTION
from hwt.hwModule import HwModule
from hwt.hdl.portItem import HdlPortItem
from hwt.serializer.utils import HdlStatement_sort_key, RtlSignal_sort_key
from hwtGraph.elk.containers.constants import PortType, PortSide
from hwtGraph.elk.containers.lNode import LNode
from hwtGraph.elk.fromHwt.netCtx import NetCtxs
from hwtGraph.elk.fromHwt.statementRenderer import StatementRenderer
from hwtGraph.elk.fromHwt.statementRendererUtils import addStmAsLNode, VirtualLNode
from hwtGraph.elk.fromHwt.utils import addPortToLNode, addPort, originObjOfPort


def HwModuleToLNode(m: HwModule, node: Optional[LNode]=None,
                toL: Optional[dict]=None,
                optimizations=[]) -> LNode:
    """
    Build LNode instance (a graph) from :class:`hwt.hwModule.HwModule` instance (a RTL graph)

    :attention: unit has to be synthesized
    """
    if toL is None:
        toL = {}

    if m._shared_component_with:
        # this component does not have body generated and uses a different
        # component
        shared_comp, _, _ = m._shared_component_with

        # copy ports
        shared_node = toL[shared_comp]
        for hwIO in m._hwIOs:
            addPortToLNode(node, hwIO)

        node._shared_component_with = shared_node
        return

    if node is None:
        root = LNode(name=m._name, originObj=m, node2lnode=toL)
    else:
        root = node

    stmPorts = {}

    # {RtlSignal: NetCtx}
    netCtx = NetCtxs(root)

    # create subunits
    for su in m._subHwModules:
        n = root.addNode(name=su._name, cls="HwModule", originObj=su)
        HwModuleToLNode(su, n, toL, optimizations)

    # create subunits from statements
    statements = sorted(m._rtlCtx.statements, key=HdlStatement_sort_key)
    for stm in statements:
        addStmAsLNode(root, stm, stmPorts, netCtx)

    # create ports for this unit
    for hwIO in m._hwIOs:
        addPort(root, hwIO)

    #k0 = HdlStatement_sort_key(statements[0])[1]
    # render content of statements
    for stm in statements:
        #k = HdlStatement_sort_key(stm)
        #k = (k[0], k[1] - k0)
        #print(k)
        #print([HdlStatement_sort_key(_k)[1] - k0 for _k in stm._iter_stms()])
        #print(stm)
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
    #print(list(x._name for x in sorted(m._rtlCtx.signals, key=RtlSignal_sort_key)))
    for s in sorted(m._rtlCtx.signals, key=RtlSignal_sort_key):
        if not s._isUnnamedExpr:
            net, _ = netCtx.getDefault(s)
            for e in s._rtlEndpoints:
                if isinstance(e, HdlPortItem):
                    net.addEndpoint(toL[e])

            for d in s._rtlDrivers:
                if isinstance(d, HdlPortItem):
                    net.addDriver(toL[d])

    netCtx.applyConnections(root)

    for opt in optimizations:
        opt(root)

    isRootOfWholeGraph = root.parent is None
    if not isRootOfWholeGraph:
        for hwIO in m._hwIOs:
            # connect my external port to port on my container on parent
            # also override toL to use this new port
            ext_p = toL[originObjOfPort(hwIO)].parentNode
            nodePort = addPortToLNode(root, hwIO)
            # connect this node which represents port to port of this node
            if hwIO._direction == INTF_DIRECTION.SLAVE:
                src = nodePort
                dst = ext_p.addPort("", PortType.INPUT, PortSide.WEST)
            else:
                src = ext_p.addPort("", PortType.OUTPUT, PortSide.EAST)
                dst = nodePort

            root.addEdge(src, dst, name=repr(hwIO), originObj=hwIO)

    return root
