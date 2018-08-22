from hwtGraph.elk.containers.constants import PortType


class LEdge():
    """
    Edge in layout graph

    :ivar parentNode: parent node instance
    :ivar name: name of this edge (label)
    :ivar originObj: optional object which was this edge generated for
    :ivar srcs: list of LPort instances where this edge starts
    :ivar dsts: list of LPort instances where this edge ends
    """

    def __init__(self, parentNode: "LNode", srcs, dsts, name: str=None, originObj=None):
        self.parentNode = parentNode
        if name is not None:
            assert isinstance(name, str)
        self.name = name
        self.originObj = originObj
        assert isinstance(srcs, list)
        assert isinstance(dsts, list)

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
            assert dst.direction == PortType.OUTPUT, dst
        else:
            assert dst.direction == PortType.INPUT, dst

        if addToDst:
            self.dsts.append(dst)
        dst.incomingEdges.append(self)

    def removeSource(self, src: "LPort"):
        self.srcs.remove(src)
        src.outgoingEdges.remove(self)

    def addSource(self, src: "LPort", addToSrc=True):
        if self.parentNode is src.parentNode:
            assert src.direction == PortType.INPUT, src
        else:
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

    def toElkJson(self, idStore):
        if len(self.dsts) > 1 or len(self.srcs) > 1:
            # hyperedge
            return {
                "id": str(idStore[self]),
                "sources": [str(idStore[src]) for src in self.srcs],
                "targets": [str(idStore[dst]) for dst in self.dsts],
            }
        else:
            # regular edge
            src = self.srcs[0]
            dst = self.dsts[0]
            return {
                "id": str(idStore[self]),
                "source": str(idStore[src.parentNode]),
                "sourcePort": str(idStore[src]),
                "target": str(idStore[dst.parentNode]),
                "targetPort": str(idStore[dst]),
            }

    def __repr__(self):
        return "<%s, %r -> %r>" % (
            self.__class__.__name__, self.src, self.dst)
