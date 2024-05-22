from typing import List

from hwt.pyUtils.setList import SetList
from hwtGraph.elk.containers.constants import PortType
from hwtGraph.elk.containers.lNode import LNode
from hwtGraph.elk.containers.lPort import LPort
from itertools import chain


def merge_non_reduced_ports(port: LPort, reduced_ports: List[LPort]):
    for ch0 in reduced_ports:
        for ch1 in ch0.children:
            ch1.name = f"{ch1.parent.name:s}.{ch1.name:s}"
            ch1.parent = port
            port.children.append(ch1)


# [TODO] We can not just remove sub-ports which have same src/dst as main port
#        we can reduce the edges, but the sub-port itself has to remain because
#        we need it for info bout structure of the main port and also
#        shred components may have differently shared shared sub-port connection
#        which should result in a different port expansion now the port is just missing
def portTryReduce(root: LNode, port: LPort):
    """
    Check if majority of children is connected to same port
    if it is the case reduce children and connect this port instead children

    :note: use reduceUselessAssignments, extractSplits, flattenTrees before this function
        to maximize it's effect
    """
    if not port.children:
        return

    for p in port.children:
        portTryReduce(root, p)

    target_nodes = {}
    ch_cnt = countDirectlyConnected(port, target_nodes)
    if not target_nodes:
        # disconnected port
        return

    new_target, children_edge_to_destroy = max(target_nodes.items(),
                                               key=lambda x: len(x[1]))
    if port.direction == new_target.direction:
        return
        # , (port, new_target, children_edge_to_destroy)
    cnt = len(children_edge_to_destroy)
    if cnt < ch_cnt / 2 or cnt == 1 and ch_cnt == 2:
        # too small or few shared connection to reduce
        return

    children_to_destroy = SetList()
    on_target_children_to_destroy = SetList()
    for child, edge in children_edge_to_destroy:
        if child.direction == PortType.OUTPUT:
            target_ch = edge.dsts
        elif child.direction == PortType.INPUT:
            target_ch = edge.srcs
        else:
            raise ValueError(child.direction)
        if len(target_ch) != 1:
            raise NotImplementedError("multiple connected nodes", target_ch)
        target_ch = target_ch[0]

        assert target_ch.parent is new_target, (
            target_ch,
            target_ch.parent,
            new_target, 'Wrong target:\n', edge.src, "\n", edge.dst,
            "\n", target_ch.parent, "\n", new_target)

        if child.direction == PortType.OUTPUT:
            edge.removeTarget(target_ch)
        elif child.direction == PortType.INPUT:
            edge.removeTarget(child)

        if not edge.srcs or not edge.dsts:
            edge.remove()

        if not target_ch.incomingEdges and not target_ch.outgoingEdges:
            # disconnect selected children from this port and target
            on_target_children_to_destroy.append(target_ch)

        if not child.incomingEdges and not child.outgoingEdges:
            children_to_destroy.append(child)

    for p in chain(children_to_destroy, on_target_children_to_destroy):
        p.connectedAsParent = True

    # destroy children of new target and this port if possible
    # port.children = [
    #    ch for ch in port.children if ch not in children_to_destroy]
    # new_target.children = [
    #    ch for ch in new_target.children if ch not in on_target_children_to_destroy]

    # if the port does have some sub ports which are an exceptions
    # from main port connection we have to add them
    # merge_non_reduced_ports(port, children_to_destroy)
    # merge_non_reduced_ports(new_target, on_target_children_to_destroy)

    # connect this port to new target as it was connected by children before
    # [TODO] names for new edges
    if port.direction == PortType.OUTPUT:
        root.addEdge(port, new_target)
    elif port.direction == PortType.INPUT:
        root.addEdge(new_target, port)
    else:
        raise NotImplementedError(port.direction)


def resolveSharedConnections(root: LNode):
    """
    Walk all ports on all nodes and group subinterface connections
    to only parent interface connection if it is possible
    """
    for ch in root.children:
        resolveSharedConnections(ch)

    for ch in root.children:
        for p in ch.iterPorts():
            portTryReduce(root, p)


def getConnectedNode(port: LPort):
    assert len(port.connectedEdges) == 1
    e = port.connectedEdges[0]
    raise NotImplementedError()
    if e.src is port:
        raise NotImplementedError()
    else:
        assert e.dst is port


def countDirectlyConnected(port: LPort, result: dict) -> int:
    """
    Count how many ports are directly connected to other nodes

    :return: cumulative sum of port counts
    """
    inEdges = port.incomingEdges
    outEdges = port.outgoingEdges

    if port.connectedAsParent or (port.children and not all(p.connectedAsParent for p in port.children)):
        ch_cnt = 0
        # try:
        #    assert not inEdges, (port, port.children, inEdges)
        #    assert not outEdges, (port, port.children, outEdges)
        # except AssertionError:
        #    raise
        for ch in port.children:
            ch_cnt += countDirectlyConnected(ch, result)

        return ch_cnt

    elif not inEdges and not outEdges:
        # this port is not connected, just check if it expected state
        if port.direction == PortType.INPUT:
            if port.originObj is not None:
                assert not port.originObj.src.drivers, (port, port.originObj)
            else:
                print("Warning", port, "not connected")
        return 0
    else:
        connectedElemCnt = 0
        for e in inEdges:
            connectedElemCnt += len(e.srcs)
            if connectedElemCnt > 1:
                return 0

        for e in outEdges:
            connectedElemCnt += len(e.dsts)
            if connectedElemCnt > 1:
                return 0

        if connectedElemCnt != 1:
            return 0

        if inEdges:
            e = inEdges[0]
        else:
            e = outEdges[0]

        # if is connected to different port
        if e.srcs[0].name != e.dsts[0].name:
            return 0

        if e.srcs[0] is port:
            p = e.dsts[0].parent
        else:
            # (can be hyperedge and then this does not have to be)
            # assert e.dsts[0] is port, (e, port)
            p = e.srcs[0].parent

        # if is part of interface which can be reduced
        if not isinstance(p, LNode):
            connections = result.get(p, [])
            connections.append((port, e))
            result[p] = connections

        return 1
