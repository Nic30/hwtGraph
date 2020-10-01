from hwt.hdl.assignment import Assignment
from hwt.hdl.operator import Operator, isConst
from hwt.hdl.operatorDefs import AllOps
from hwtGraph.elk.containers.constants import PortType, PortSide
from hwtGraph.elk.containers.lNode import LNode
from hwt.serializer.utils import RtlSignal_sort_key


class InterfaceSplitInfo(tuple):
    pass


def extractSplits(root: LNode):
    """
    convert group of indexed assignments witch are splitting signal to Split node

    a = sig[0]
    b = sig[1]
    to
    a, b = sig

    :param toL: dictionary {hdl object: layout object}
    """
    toL = root._node2lnode
    signals = sorted(root.originObj._ctx.signals, key=RtlSignal_sort_key)

    # search from "sig" side (look at doc string)
    for s in signals:
        if len(s.drivers) == 1 and len(s.endpoints) > 1:
            sliceParts = []
            for ep in s.endpoints:
                if isinstance(ep, Assignment) and not ep.indexes and ep.src.hidden:
                    op = ep.src.origin
                else:
                    op = ep

                if isinstance(op, Operator)\
                        and op.operator == AllOps.INDEX\
                        and op.operands[0] is s:
                    index = op.operands[1]
                    if isConst(index):
                        sliceRange = index.staticEval().to_py()
                        if isinstance(sliceRange, int):
                            sliceRange = slice(sliceRange + 1, sliceRange)

                        if ep not in toL:
                            continue
                        sliceParts.append((sliceRange, ep))

            if sliceParts: 
                # reduce to slice
                sliceParts.sort(key=lambda x: x[0].start)
                n = toL[sliceParts[0][1]]
                p = n.west[0]
                if not p.incomingEdges:
                    return
                srcPorts = p.incomingEdges[0].srcs
                assert len(srcPorts) == 1
                srcPort = srcPorts[0]
                dstPortsOnInputNet = list(p.incomingEdges[0].dsts)
                sliceNode = root.addNode(
                    name="SLICE", cls="Operator", originObj=InterfaceSplitInfo(x[1] for x in sliceParts))
                inputPort = sliceNode.addPort(
                    "", PortType.INPUT, PortSide.WEST)

                # create new sliceNode
                for sliceRange, assig in sliceParts:
                    if sliceRange.start - sliceRange.stop == 1:
                        name = "[%d]" % sliceRange.stop
                    else:
                        name = "[%d:%d]" % (sliceRange.start, sliceRange.stop)
                    outPort = sliceNode.addPort(
                        name, PortType.OUTPUT, PortSide.EAST)
                    oldAssigNode = toL[assig]
                    dstPorts = []

                    dstPortsOnInputNet.remove(oldAssigNode.west[0])
                    for e in list(oldAssigNode.west[0].incomingEdges):
                        e.remove()

                    for e in list(oldAssigNode.east[0].outgoingEdges):
                        for _dst in e.dsts:
                            dstPorts.append((_dst, e.originObj))
                        e.remove()

                    root.children.remove(oldAssigNode)
                    # remove index value node (we know that it is constant,
                    # from original select)
                    _e = oldAssigNode.west[1].incomingEdges[0]
                    _e.removeTarget(oldAssigNode.west[1])
                    assert len(_e.srcs) == 1
                    indexValNodeP = _e.srcs[0]
                    if not _e.dsts:
                        _e.remove()

                    if not indexValNodeP.outgoingEdges:
                        root.children.remove(indexValNodeP.parentNode)

                    root.addHyperEdge([outPort],
                                      [dst[0] for dst in dstPorts],
                                      originObj=dstPorts[0][1])

                dstPortsOnInputNet.append(inputPort)
                root.addHyperEdge([srcPort, ], dstPortsOnInputNet,
                                  name=e.name, originObj=e.originObj)
