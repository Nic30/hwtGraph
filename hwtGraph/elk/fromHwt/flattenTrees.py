from typing import Callable

from hwtGraph.elk.containers.constants import PortType, PortSide
from hwtGraph.elk.containers.lNode import LNode


def searchRootOfTree(reducibleChildren, nodeFromTree):
    while True:
        out_e = nodeFromTree.east[0].outgoingEdges
        if not out_e:
            return nodeFromTree

        nextNode = out_e[0].dsts[0].parentNode
        if nextNode in reducibleChildren:
            nodeFromTree = nextNode
        else:
            return nodeFromTree


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

    reducibleChildren = set()
    for ch in root.children:
        if nodeSelector(ch):
            reducibleChildren.add(ch)

    while reducibleChildren:
        _treeRoot = reducibleChildren.pop()
        reducibleChildren.add(_treeRoot)
        # wee need to keep order of inputs, use preorder
        treeRoot = searchRootOfTree(reducibleChildren, _treeRoot)

        inputEdges = []
        reducedNodes = []
        reducedNodesSet = set()
        # An iterative process to print preorder traveral of tree
        nodeStack = []
        nodeStack.append((treeRoot, None))

        while nodeStack:
            # Pop the top item from stack and print it to the graph
            node, e = nodeStack.pop()
            if node in reducibleChildren and node not in reducedNodesSet:
                reducedNodes.append(node)
                reducedNodesSet.add(node)
                # walk inputs and add child nodes to stack
                for p in node.west:
                    for e in p.iterEdges():
                        assert len(e.srcs) == 1
                        nodeStack.append((e.srcs[0].parentNode, e))
            else:
                inputEdges.append(e)

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

            for i, ie in enumerate(inputEdges):
                name = None
                index = len(inputEdges) - i - 1
                if hasattr(ie.originObj, "_dtype"):
                    w = ie.originObj._dtype.bit_length()
                    if w > 1:
                        name = "[%d:%d]" % ((index + 1) * w, index * w)
                    else:
                        name = None

                if name is None:
                    name = "[%d]" % (index)

                inp = newNode.addPort(name,
                                      PortType.INPUT, PortSide.WEST)
                srcs = list(ie.srcs)
                assert len(srcs) == 1
                ie.remove()
                root.addEdge(srcs[0], inp, originObj=ie.originObj)

            for n in reducedNodes:
                root.children.remove(n)
                reducibleChildren.remove(n)
        else:
            reducibleChildren.remove(reducedNodes[0])
