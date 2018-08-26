from itertools import chain
from typing import List, Generator

from hwt.pyUtils.uniqList import UniqList

from hwtGraph.elk.containers.constants import PortSide, PortType, \
    NodeType, PortConstraints
from hwtGraph.elk.containers.lEdge import LEdge
from hwtGraph.elk.containers.lPort import LPort


class LNode():
    """
    Component for component diagram

    :ivar originObj: original object which this node represents
    :ivar name: name of this unit
    :ivar class_name: name of class of this unit

    :ivar north: list of LPort for on  top side.
    :ivar east: list of LPort for on right side.
    :ivar south: list of LPort for on bottom side.
    :ivar west: list of LPort for on left side.
    :ivar bodyText: text which should be rendered inside body of component
        (if it is not only container of children)
    """

    def __init__(self, parent: "LNode"=None, name: str=None,
                 originObj=None, node2lnode=None, bodyText=None):
        super(LNode, self).__init__()
        if name is not None:
            assert isinstance(name, str)
        self.originObj = originObj
        self.name = name
        self.bodyText = bodyText

        self.west = []
        self.east = []
        self.north = []
        self.south = []

        self.parent = parent

        self.portConstraints = PortConstraints.FIXED_ORDER
        self.children = []
        self.origin = None
        self._node2lnode = node2lnode

    def iterPorts(self) -> Generator[LPort, None, None]:
        return chain(self.north, self.east,
                     reversed(self.south), reversed(self.west))

    def getPortSideView(self, side) -> List["LPort"]:
        """
        Returns a sublist view for all ports of given side.

        :attention: Use this only after port sides are fixed!

        This is currently the case after running the {@link org.eclipse.elk.alg.layered.intermediate.PortListSorter}.
        Non-structural changes to this list are reflected in the original list. A structural modification is any
        operation that adds or deletes one or more elements; merely setting the value of an element is not a structural
        modification. Sublist indices can be cached using {@link LNode#cachePortSides()}.

        :param side: a port side
        :return: an iterable for the ports of given side
        """
        if side == PortSide.WEST:
            return self.west
        elif side == PortSide.EAST:
            return self.east
        elif side == PortSide.NORTH:
            return self.north
        elif side == PortSide.SOUTH:
            return self.south
        else:
            raise ValueError(side)

    def addPort(self, name, direction: PortType, side: PortSide):
        port = LPort(self, direction, side, name=name)
        self.getPortSideView(side).append(port)
        return port

    def addNode(self, name: str=None, originObj=None,
                portConstraint=PortConstraints.FIXED_ORDER,
                bodyText=None) -> "LNode":
        n = LNode(self, name=name, originObj=originObj,
                  node2lnode=self._node2lnode, bodyText=bodyText)
        n.portConstraints = portConstraint
        if self._node2lnode is not None:
            self._node2lnode[originObj] = n
        self.children.append(n)
        return n

    def iterEdges(self, filterSelfLoops=False):
        """
        Iter edges connected from outside of this unit
        """
        for p in self.iterPorts():
            yield from p.iterEdges(filterSelfLoops=filterSelfLoops)

    def addEdge(self, src: LPort, dst: LPort, name=None, originObj=None):
        e = LEdge(self, [src], [dst], name=name, originObj=originObj)
        return e

    def addHyperEdge(self, srcs, dsts, name=None, originObj=None):
        e = LEdge(self, srcs, dsts, name=name, originObj=originObj)
        return e

    def toElkJson_registerNodes(self, idStore, isTop=False):
        idStore.registerNode(self)
        for ch in self.children:
            ch.toElkJson_registerNodes(idStore)

    def toElkJson_registerPorts(self, idStore):
        """
        The index of a port in the fixed order around a node.
        The order is assumed as clockwise, starting with the leftmost port on the top side.
        This option must be set if ‘Port Constraints’ is set to FIXED_ORDER
        and no specific positions are given for the ports. Additionally,
        the option ‘Port Side’ must be defined in this case.
        """
        addIndex = self.portConstraints == PortConstraints.FIXED_ORDER
        for i, p in enumerate(self.iterPorts()):
            if addIndex:
                p.index = i
            idStore.registerPort(p)

        for ch in self.children:
            ch.toElkJson_registerPorts(idStore)

    def toElkJson(self, idStore: "ElkIdStore", isTop=True):
        props = {
            "org.eclipse.elk.portConstraints": self.portConstraints.name,
            'org.eclipse.elk.randomSeed': 0,
            'org.eclipse.elk.layered.mergeEdges': 1,
        }
        d_hwt = {
            "name": self.name,
        }
        d = {
            "hwt": d_hwt,
            "properties": props
        }
        if self.bodyText is not None:
            d_hwt["bodyText"] = self.bodyText

        if not isTop:
            d["id"] = str(idStore[self])
            d["hideChildren"] = True
            # if self.parent.parent is not None:
            #    props["org.eclipse.elk.noLayout"] = True
        else:
            self.toElkJson_registerNodes(idStore, isTop=isTop)
            self.toElkJson_registerPorts(idStore)

        d["ports"] = [p.toElkJson(idStore)
                      for p in self.iterPorts()]
        if self.children:
            nodes = []
            edges = UniqList()
            for ch in self.children:
                for e in ch.iterEdges():
                    if e.parentNode is self:
                        edges.append(e)

            for ch in self.children:
                nodes.append(ch.toElkJson(idStore, isTop=False))

            nodes.sort(key=lambda n: n["id"])
            d["children"] = nodes

            for e in edges:
                idStore.registerEdge(e)

            d["edges"] = [e.toElkJson(idStore) for e in edges]

        d_hwt["maxId"] = idStore.getMaxId()

        return d

    def getNode(self):
        return self

    def __repr__(self):
        return "<{0} {1:#018x} {2}>".format(
            self.__class__.__name__, id(self), self.name)


class LayoutExternalPort(LNode):

    def __init__(self, parent: "LNode", name: str=None,
                 direction=None, node2lnode=None):
        super(LayoutExternalPort, self).__init__(
            parent=parent, name=name, node2lnode=node2lnode)
        self.direction = direction
        self.type = NodeType.EXTERNAL_PORT
        # if direction == PortType.INPUT:
        #     self.layeringLayerConstraint = LayerConstraint.FIRST
        # elif direction == PortType.OUTPUT:
        #     self.layeringLayerConstraint = LayerConstraint.LAST
        # else:
        #     raise ValueError(direction)

    def toElkJson(self, idStore, isTop=True):
        d = super(LayoutExternalPort, self).toElkJson(idStore, isTop=isTop)
        d["hwt"]['isExternalPort'] = True
        # d['properties']["org.eclipse.elk.layered.layering.layerConstraint"] = self.layeringLayerConstraint.name
        return d
