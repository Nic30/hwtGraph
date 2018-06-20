from typing import Callable

from hwtGraph.elk.containers.constants import PortType, PortSide
from hwtGraph.elk.containers.lNode import LNode
from hwtGraph.elk.fromHwt.utils import removeEdge


def searchRootOfTree(reducibleChildren, nodeFromTree):
    while True:
        out_e = nodeFromTree.east[0].outgoingEdges
        if not out_e:
            return nodeFromTree

        nextNode = out_e[0].dstNode
        if nextNode in reducibleChildren:
            nodeFromTree = nextNode
        else:
            return nodeFromTree


def flattenTrees(root, nodeSelector: Callable[[LNode], bool]):
    """
    Walk all nodes and discover trees of nodes (usually operators) and reduce them
    to single node with multiple outputs

    :attention: node has to have single output
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
            # Pop the top item from stack and print it
            node, e = nodeStack.pop()
            if node in reducibleChildren and node not in reducedNodesSet:
                reducedNodes.append(node)
                reducedNodesSet.add(node)
                # walk inputs and add child nodes to stack
                for p in node.west:
                    for e in p.iterEdges():
                        nodeStack.append((e.srcNode, e))
            else:
                inputEdges.append(e)

        if len(reducedNodes) > 1:
            outputedge = treeRoot.east[0].outgoingEdges[0]
            assert outputedge is not None

            newName = reducedNodes[0].name
            newNode = root.addNode(newName)

            o = newNode.addPort("", PortType.OUTPUT, PortSide.EAST)
            dst = outputedge.dst
            removeEdge(outputedge)
            root.addEdge(o, dst, originObj=outputedge.originObj)

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
                src = ie.src
                removeEdge(ie)
                root.addEdge(src, inp, originObj=ie.originObj)

            for n in reducedNodes:
                root.children.remove(n)
                reducibleChildren.remove(n)
        else:
            reducibleChildren.remove(reducedNodes[0])
