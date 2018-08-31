from typing import Callable, Set

from hwtGraph.elk.containers.constants import PortType, PortSide
from hwtGraph.elk.containers.lNode import LNode


def searchRootOfTree(reducibleChildren: Set[LNode], nodeFromTree: LNode):
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
        if nextNode in reducibleChildren:
            # can reduce node, walk the tree to root
            nodeFromTree = nextNode
        else:
            # can not reduce, return last root of tree
            return nodeFromTree


def collectNodesInTree(treeRoot: LNode, reducibleChildren: Set[LNode]):
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
    reducedNodes = []
    # Set[LNode]
    reducedNodesSet = set()
    # An iterative process to print preorder traveral of tree
    # List[Typle[LNode, LPort, LEdge]]
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
    for ch in root.children:
        if ch.children:
            flattenTrees(ch, nodeSelector)

    # collect all nodes which can be potentialy reduced
    reducibleChildren = set()
    for ch in root.children:
        if nodeSelector(ch):
            reducibleChildren.add(ch)

    while reducibleChildren:
        # try to pick a node from random tree and search it's root
        _treeRoot = reducibleChildren.pop()
        reducibleChildren.add(_treeRoot)
        # we need to keep order of inputs, use preorder
        treeRoot = searchRootOfTree(reducibleChildren, _treeRoot)

        reducedNodes, inputEdges = collectNodesInTree(treeRoot, reducibleChildren)
        # if tree is big enoguh for reduction, reduce it to single node
        if len(reducedNodes) > 1:
            newName = reducedNodes[0].name
            newNode = root.addNode(newName)

            o = newNode.addPort("", PortType.OUTPUT, PortSide.EAST)

            oEdges = treeRoot.east[0].outgoingEdges
            for outputedge in list(oEdges):
                dsts = list(outputedge.dsts)
                assert len(dsts) > 0
                outputedge.remove()
                root.addHyperEdge([o, ], dsts, originObj=outputedge.originObj)

            for i, (iN, iP, iE) in enumerate(inputEdges):
                name = None
                index = len(inputEdges) - i - 1
                if hasattr(iE.originObj, "_dtype"):
                    w = iE.originObj._dtype.bit_length()
                    if w > 1:
                        name = "[%d:%d]" % ((index + 1) * w, index * w)
                    else:
                        name = None

                if name is None:
                    name = "[%d]" % (index)

                inp = newNode.addPort(name,
                                      PortType.INPUT, PortSide.WEST)
                iE.removeTarget(iP)
                iE.addTarget(inp)

            for n in reducedNodes:
                root.children.remove(n)
                reducibleChildren.remove(n)
        else:
            reducibleChildren.remove(reducedNodes[0])
