from hwtGraph.elk.containers.constants import PortType
from hwtGraph.elk.containers.lNode import LNode
from hwtGraph.elk.containers.lPort import LPort


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
    cnt = len(children_edge_to_destroy)
    if cnt < ch_cnt / 2 or cnt == 1 and ch_cnt == 2:
        # too small to few shared connection to reduce
        return

    children_to_destroy = set()
    on_target_children_to_destroy = set()
    for child, edge in children_edge_to_destroy:
        if child.direction == PortType.OUTPUT:
            target_ch = edge.dst
        elif child.direction == PortType.INPUT:
            target_ch = edge.src
        else:
            raise ValueError(child.direction)

        try:
            assert target_ch.parent is new_target, (
                target_ch,
                target_ch.parent,
                new_target)
        except AssertionError:
            print('Wrong target:\n', edge.src, "\n", edge.dst,
                  "\n", target_ch.parent, "\n", new_target)
            raise
        # disconnect selected children from this port and target
        children_to_destroy.add(child)
        on_target_children_to_destroy.add(target_ch)

        for p in (child, target_ch):
            removed = False
            try:
                p.incomingEdges.remove(edge)
                removed = True
            except ValueError:
                pass
            try:
                p.outgoingEdges.remove(edge)
                removed = True
            except ValueError:
                pass
            assert removed

    # destroy children of new target and this port if possible
    port.children = [
        ch for ch in port.children if ch not in children_to_destroy]
    new_target.children = [
        ch for ch in new_target.children if ch not in on_target_children_to_destroy]

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

    if port.children:
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
        if port.direction == PortType.INPUT:
            print("Warning", port, "not connected")
        return 0
    else:
        if len(inEdges) + len(outEdges) != 1:
            return 0

        if inEdges:
            e = inEdges[0]
        else:
            e = outEdges[0]

        # if is connected to different port
        if e.src.name != e.dst.name:
            return 0

        if e.src is port:
            p = e.dst.parent
        else:
            assert e.dst is port
            p = e.src.parent

        # if is part of interface which can be reduced
        if not isinstance(p, LNode):
            connections = result.get(p, [])
            connections.append((port, e))
            result[p] = connections

        return 1
