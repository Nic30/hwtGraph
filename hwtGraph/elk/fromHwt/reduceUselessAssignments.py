from hwt.hdl.assignment import Assignment
from hwt.pyUtils.uniqList import UniqList
from hwt.synthesizer.rtlLevel.mainBases import RtlSignalBase
from hwtGraph.elk.containers.lNode import LNode
from hwtGraph.elk.fromHwt.utils import getSinglePort


def reduceUselessAssignments(root: LNode):
    """
    Remove assignments if it is only a direct connection and can be replaced with direct link
    """
    for n in root.children:
        if n.children:
            reduceUselessAssignments(n)

    to_remove = set()
    for n in root.children:
        if isinstance(n.originObj, Assignment)\
                and not n.originObj.indexes\
                and len(n.west) == 1:
            src = n.originObj.src
            if isinstance(src, RtlSignalBase) and src.hidden:
                continue

            to_remove.add(n)

            srcPorts = []
            dstPorts = []
            edgesToRemove = UniqList()

            inP = getSinglePort(n.west)
            outP = getSinglePort(n.east)
            for e in inP.incomingEdges:
                sPort = e.src
                srcPorts.append((sPort, e.originObj))
                edgesToRemove.append(e)

            for e in outP.outgoingEdges:
                dPort = e.dst
                dstPorts.append(dPort)
                edgesToRemove.append(e)

            for e in edgesToRemove:
                e.remove()

            for srcPort, originObj in srcPorts:
                for dstPort in dstPorts:
                    root.addEdge(srcPort, dstPort,
                                 originObj=originObj)

    if to_remove:
        root.children = [n for n in root.children if n not in to_remove]
