from typing import List

from hwt.synthesizer.componentPath import ComponentPath
from hwtGraph.elk.containers.constants import PortType


class LEdge():
    """
    Edge in layout graph

    :ivar ~.parentNode: parent node instance
    :ivar ~.name: name of this edge (label)
    :ivar ~.originObj: optional object which was this edge generated for
    :ivar ~.srcs: list of LPort instances where this edge starts
    :ivar ~.dsts: list of LPort instances where this edge ends
    """

    def __init__(self, parentNode: "LNode", srcs: List["LPort"], dsts: List["LPort"],
                 name: str=None, originObj=None):
        self.parentNode = parentNode
        if name is not None:
            assert isinstance(name, str)
        
        self.name = name
        self.originObj = originObj

        assert isinstance(srcs, list) and len(srcs) >= 1, originObj
        assert isinstance(dsts, list) and len(dsts) >= 1, originObj

        self.srcs = []
        self.dsts = []
        for src in srcs:
            self.addSource(src, addToSrc=False)
        self.srcs = srcs

        for dst in dsts:
            self.addTarget(dst, addToDst=False)
        self.dsts = dsts

    def removeTarget(self, dst: "LPort"):
        self.dsts.remove(dst)
        dst.incomingEdges.remove(self)

    def addTarget(self, dst: "LPort", addToDst=True):
        if self.parentNode is dst.parentNode:
            # connection between input and output on nodes with same parent
            assert dst.direction == PortType.OUTPUT, dst
        elif self.parentNode.parent is dst.parentNode:
            # target is parent output port
            assert dst.direction == PortType.INPUT, dst
        else:
            # target is child input port
            assert self.parentNode is dst.parentNode.parent, dst
            assert dst.direction == PortType.INPUT, dst

        if addToDst:
            self.dsts.append(dst)
        dst.incomingEdges.append(self)

    def removeSource(self, src: "LPort"):
        self.srcs.remove(src)
        src.outgoingEdges.remove(self)

    def addSource(self, src: "LPort", addToSrc=True):
        if self.parentNode is src.parentNode:
            # connection between input and output on nodes with same parent
            assert src.direction == PortType.INPUT, src
        elif self.parentNode.parent is src.parentNode:
            # source is parent input port
            assert src.direction == PortType.INPUT, src
        else:
            # source is child output port
            assert self.parentNode is src.parentNode.parent, src
            assert src.direction == PortType.OUTPUT, src
        if addToSrc:
            self.srcs.append(src)
        src.outgoingEdges.append(self)

    def remove(self):
        for dst in self.dsts:
            dst.incomingEdges.remove(self)
        for src in self.srcs:
            src.outgoingEdges.remove(self)
        self.srcs.clear()
        self.dsts.clear()

    def toElkJson(self, idStore, path_prefix: ComponentPath):
        def getId(o):
            k = path_prefix / o
            return str(idStore[k])
        if len(self.dsts) > 1 or len(self.srcs) > 1:
            # hyperedge
            d = {
                "sources": [(getId(src.parentNode),
                             getId(src)) for src in self.srcs],
                "targets": [(getId(dst.parentNode),
                             getId(dst)) for dst in self.dsts],
            }
        else:
            # regular edge
            src = self.srcs[0]
            dst = self.dsts[0]
            d = {
                "source": getId(src.parentNode),
                "sourcePort": getId(src),
                "target": getId(dst.parentNode),
                "targetPort": getId(dst),
            }
        d["id"] = getId(self)
        name = self.name
        if name is None and self.originObj is not None:
            name = repr(self.originObj)
        d["hwMeta"] = {"name": name}

        return d

    def __repr__(self):
        return "<%s, %r -> %r>" % (
            self.__class__.__name__, self.srcs, self.dsts)
