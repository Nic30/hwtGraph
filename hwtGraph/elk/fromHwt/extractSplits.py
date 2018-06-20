from hwt.hdl.assignment import Assignment
from hwt.hdl.operator import Operator, isConst
from hwt.hdl.operatorDefs import AllOps
from hwt.hdl.types.array import HArray
from hwt.hdl.types.bits import Bits
from hwtGraph.elk.containers.constants import PortType, PortSide
from hwtGraph.elk.containers.lNode import LNode

from hwtGraph.elk.fromHwt.utils import removeEdge


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
    signals = root.originObj._ctx.signals

    # search from "sig" side (look at doc string)
    for s in signals:
        if len(s.drivers) == 1 and len(s.endpoints) > 1:
            expectedItems = None
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
                        i = index.staticEval().toPy()
                        if isinstance(i, int):
                            i = slice(i + 1, i)

                        t = s._dtype
                        if isinstance(t, Bits):
                            w = t.bit_length()
                        elif isinstance(t, HArray):
                            w = int(t.size)
                        else:
                            # slice on unexpected data type
                            raise NotImplementedError(t)
                        sliceW = i.start - i.stop
                        items = w // sliceW
                        if expectedItems is None:
                            expectedItems = items
                        else:
                            if expectedItems != items:
                                continue

                        if items * sliceW == w:
                            sliceI = i.stop // sliceW
                            if ep not in toL:
                                continue
                            sliceParts.append((sliceI, ep))
                            continue

            compatible = expectedItems is not None and expectedItems == len(
                sliceParts)
            if compatible:
                # reduce to slice
                sliceParts.sort(reverse=True)
                n = toL[sliceParts[0][1]]
                p = n.west[0]
                if not p.incomingEdges:
                    return
                srcPort = p.incomingEdges[0].src
                sliceNode = root.addNode(
                    "SLICE", originObj=InterfaceSplitInfo(sliceParts))
                inputPort = sliceNode.addPort(
                    "", PortType.INPUT, PortSide.WEST)

                # create new sliceNode
                for i, assig in sliceParts:
                    name = "[%d]" % i
                    outPort = sliceNode.addPort(
                        name, PortType.OUTPUT, PortSide.EAST)
                    oldAssigNode = toL[assig]
                    dstPorts = []

                    for e in list(oldAssigNode.west[0].incomingEdges):
                        removeEdge(e)

                    for e in list(oldAssigNode.east[0].outgoingEdges):
                        dstPorts.append((e.dst, e.originObj))
                        removeEdge(e)

                    root.children.remove(oldAssigNode)
                    # remove index value node (we know that it is constant,
                    # from original select)
                    root.children.remove(
                        oldAssigNode.west[1].incomingEdges[0].srcNode)

                    for dst, originObj in dstPorts:
                        root.addEdge(outPort, dst, originObj=originObj)

                root.addEdge(srcPort, inputPort, e.name, e.originObj)
