from typing import Callable, Set

from hwt.pyUtils.uniqList import UniqList
from hwtGraph.elk.containers.constants import PortType, PortSide
from hwtGraph.elk.containers.lNode import LNode


def searchRootOfTree(reducibleChildren: Set[LNode], nodeFromTree: LNode, removedNodes: Set[LNode]):
    """
    Walk tree of nodes to root

    :param reducibleChildren: nodes which are part of tree
    :param nodeFromTree: node where to start the search
    """

    while True:
        out_e = nodeFromTree.east[0].outgoingEdges
        # node has no successors
        if not out_e:
            return nodeFromTree

        nextNode = out_e[0].dsts[0].parentNode
        if nextNode in reducibleChildren and nextNode not in removedNodes:
            # can reduce node, walk the tree to root
            nodeFromTree = nextNode
        else:
            # can not reduce, return last root of tree
            return nodeFromTree


def collectNodesInTree(treeRoot: LNode, reducibleChildren: Set[LNode], reducedNodesSet: Set[LNode]):
    """
    Collect nodes which will be reduced and input nodes of tree for tree of nodes.

    :param treeRoot: root node of tree
    :param reducibleChildren: members of tree
    :return: Tuple[reducedNodes, inputEdges] where reducedNodes is List[LNode]
        and inputEdges is List[Tuple[LNode, LPort, LEdge]]
    """
    # List[Tuple[LNode, LPort, LEdge]]
    inputEdges = []
    # List[LNode]
    # :note: we are using the list because we want to keep the order of the operations
    reducedNodes = []
    # An iterative process to print pre-order traversal of tree
    # List[Tuple[LNode, LPort, LEdge]]
    nodeStack = []
    nodeStack.append((treeRoot, None, None))

    # collect nodes in tree and input edges
    while nodeStack:
        # pop the node from stack and try to find it's children
        node, p, e = nodeStack.pop()
        if node in reducibleChildren and node not in reducedNodesSet:
            reducedNodes.append(node)
            reducedNodesSet.add(node)
            # walk inputs and add child nodes to stack
            for _p in node.west:
                for _e in _p.iterEdges():
                    # assert len(e.srcs) == 1 and len(e.dsts) == 1
                    nodeStack.append((_e.srcs[0].parentNode, _p, _e))
        else:
            inputEdges.append((node, p, e))

    return reducedNodes, inputEdges


def flattenTrees(root, nodeSelector: Callable[[LNode], bool]):
    """
    Walk all nodes and discover trees of nodes (usually operators)
    and reduce them to single node with multiple outputs

    :attention: selected nodes has to have single output
                and has to be connected to nets with single driver
    """
    assert isinstance(root.children, list)
    for ch in root.children:
        if ch.children:
            flattenTrees(ch, nodeSelector)

    # collect all nodes which can be potentially reduced
    reducibleChildren = UniqList(ch for ch in root.children if nodeSelector(ch))

    removedNodes = set()
    for _treeRoot in reducibleChildren:
        # try to pick a node from random tree and search it's root
        if _treeRoot in removedNodes:
            continue

        # we need to keep order of inputs, use pre-order
        treeRoot = searchRootOfTree(reducibleChildren, _treeRoot, removedNodes)

        reducedNodes, inputEdges = collectNodesInTree(treeRoot, reducibleChildren, removedNodes)
        # if tree is big enough for reduction, reduce it to single node
        if len(reducedNodes) > 1:
            newNode = root.addNode(name=reducedNodes[0].name,
                                   cls=reducedNodes[0].cls)

            o = newNode.addPort("", PortType.OUTPUT, PortSide.EAST)

            oEdges = treeRoot.east[0].outgoingEdges
            # intented copy of oEdges
            for outputedge in list(oEdges):
                dsts = list(outputedge.dsts)
                assert len(dsts) > 0
                outputedge.remove()
                root.addHyperEdge([o, ], dsts, originObj=outputedge.originObj)

            port_names = []
            bit_offset = 0
            for i, (iN, iP, iE) in enumerate(inputEdges):
                name = None
                index = len(inputEdges) - i - 1
                origin_sig = iE.originObj
                if type(origin_sig) is tuple:
                    for _origin_sig in origin_sig:
                        if hasattr(_origin_sig, "_dtype"):
                            origin_sig = _origin_sig

                if hasattr(origin_sig, "_dtype"):
                    w = origin_sig._dtype.bit_length()
                    if w > 1:
                        name = "[%d:%d]" % (w + bit_offset, bit_offset)
                    else:
                        name = "[%d]" % bit_offset
                    bit_offset += w

                if name is None:
                    assert bit_offset == 0, ("can not mix implicitly indexed and bit indexed array items", inputEdges)
                    name = "[%d]" % (index)
                port_names.append(name)

            for name, (_, iP, iE) in zip(port_names, inputEdges):
                inp = newNode.addPort(name,
                                      PortType.INPUT, PortSide.WEST)
                iE.removeTarget(iP)
                iE.addTarget(inp)

            for n in reducedNodes:
                root.children.remove(n)
