from itertools import chain
from typing import List, Generator

from hwt.pyUtils.uniqList import UniqList
from hwt.synthesizer.componentPath import ComponentPath
from hwtGraph.elk.containers.constants import PortSide, PortType, \
    NodeType, PortConstraints
from hwtGraph.elk.containers.lEdge import LEdge
from hwtGraph.elk.containers.lPort import LPort


class LNode():
    """
    Component for component diagram

    :ivar ~.originObj: original object which this node represents
    :ivar ~.name: name of this unit
    :ivar ~.class_name: name of class of this unit

    :ivar ~.north: list of LPort for on  top side.
    :ivar ~.east: list of LPort for on right side.
    :ivar ~.south: list of LPort for on bottom side.
    :ivar ~.west: list of LPort for on left side.
    :ivar ~.bodyText: text which should be rendered inside body of component
        (if it is not only container of children)
    :ivar ~._shared_component_with: optional LNode insance
        if set the body of this component is not filled and it is same
        as the _shared_component_with LNode
    """

    def __init__(self, parent: "LNode"=None, name: str=None, cls: str=None,
                 originObj=None, node2lnode=None, bodyText=None):
        if name is not None:
            assert isinstance(name, str)
        self.originObj = originObj
        self.name = name
        self.cls = cls
        self.bodyText = bodyText

        self.west = []
        self.east = []
        self.north = []
        self.south = []

        self.parent = parent

        self.portConstraints = PortConstraints.FIXED_ORDER
        self.children = []
        self.origin = None
        self._shared_component_with = None
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

    def addPort(self, name, direction: PortType, side: PortSide, originObj=None):
        port = LPort(self, direction, side, name=name, originObj=originObj)
        self.getPortSideView(side).append(port)
        return port

    def addNode(self, name: str=None, cls: str=None, originObj=None,
                portConstraint=PortConstraints.FIXED_ORDER,
                bodyText=None) -> "LNode":
        n = LNode(self, name=name, cls=cls, originObj=originObj,
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

    def _getUniqRefChildren(self, path_prefix: ComponentPath):
        comp = self._shared_component_with
        if comp is None:
            children = self.children
        else:
            assert not self.children, self
            # reuse the body of an existing component
            path_prefix = path_prefix / self
            children = comp.children

        return children, path_prefix

    def toElkJson_registerNodes(self, idStore,
                                path_prefix: ComponentPath):

        id_ = idStore.registerNode(path_prefix / self)
        c = self._shared_component_with
        if c is not None:
            idStore[path_prefix / self / c] = id_

        children, path_prefix = self._getUniqRefChildren(path_prefix)
        for ch in children:
            ch.toElkJson_registerNodes(idStore, path_prefix)

    def toElkJson_registerPorts(self, idStore,
                                path_prefix: ComponentPath):
        """
        The index of a port in the fixed order around a node.
        The order is assumed as clockwise, starting with the leftmost port on the top side.
        This option must be set if ‘Port Constraints’ is set to FIXED_ORDER
        and no specific positions are given for the ports. Additionally,
        the option ‘Port Side’ must be defined in this case.
        """
        addIndex = self.portConstraints == PortConstraints.FIXED_ORDER
        c = self._shared_component_with
        pp = path_prefix / self

        if c is None:
            for i, p in enumerate(self.iterPorts()):
                if addIndex:
                    p.index = i
                idStore.registerPort(path_prefix / p)
        else:
            for i, (p, orig_p) in enumerate(zip(self.iterPorts(), c.iterPorts())):
                if addIndex:
                    p.index = i
                id_ = idStore.registerPort(path_prefix / p)
                idStore[pp / orig_p] = id_

        children, path_prefix = self._getUniqRefChildren(path_prefix)
        for ch in children:
            ch.toElkJson_registerPorts(idStore, path_prefix)

    def toElkJson(self, idStore: "ElkIdStore", path_prefix: ComponentPath = ComponentPath(), isTop=True):
        props = {
            "org.eclipse.elk.portConstraints": self.portConstraints.name,
            'org.eclipse.elk.randomSeed': 0,
            'org.eclipse.elk.layered.mergeEdges': 1,
        }
        hw_meta = {
            "name": self.name,
            "cls": self.cls,
        }
        d = {
            "hwMeta": hw_meta,
            "properties": props
        }
        hideChildren = False
        if self.bodyText is not None:
            hw_meta["bodyText"] = self.bodyText

        if isTop:
            self.toElkJson_registerNodes(idStore, path_prefix)
            self.toElkJson_registerPorts(idStore, path_prefix)
        else:
            d["id"] = str(idStore[path_prefix / self])
            hideChildren = True
            # if self.parent.parent is not None:
            #    props["org.eclipse.elk.noLayout"] = True

        d["ports"] = [p.toElkJson(idStore, path_prefix)
                      for p in self.iterPorts()]

        children, path_prefix = self._getUniqRefChildren(path_prefix)
        if children:
            assert isinstance(children, list)
            formalParent = self._shared_component_with
            if formalParent is None:
                formalParent = self
            nodes = []
            edges = UniqList()
            for ch in children:
                for e in ch.iterEdges():
                    if e.parentNode is formalParent:
                        edges.append(e)

            for ch in children:
                nodes.append(ch.toElkJson(idStore, isTop=False, path_prefix=path_prefix))

            nodes.sort(key=lambda n: n["id"])
            d["_children" if hideChildren else "children"] = nodes

            for e in edges:
                idStore.registerEdge(path_prefix / e)

            d["_edges" if hideChildren else "edges"] = [e.toElkJson(idStore, path_prefix) for e in edges]

        hw_meta["maxId"] = idStore.getMaxId()

        return d

    def getNode(self):
        return self

    def __repr__(self):
        return "<{0} {1:#018x} {2}>".format(
            self.__class__.__name__, id(self), self.name)


class LayoutExternalPort(LNode):

    def __init__(self, parent: "LNode", name: str=None,
                 direction=None, node2lnode=None, originObj=None):
        super(LayoutExternalPort, self).__init__(
            parent=parent, name=name, node2lnode=node2lnode, originObj=originObj)
        self.direction = direction
        self.type = NodeType.EXTERNAL_PORT
        # if direction == PortType.INPUT:
        #     self.layeringLayerConstraint = LayerConstraint.FIRST
        # elif direction == PortType.OUTPUT:
        #     self.layeringLayerConstraint = LayerConstraint.LAST
        # else:
        #     raise ValueError(direction)

    def toElkJson(self, idStore, isTop=True, path_prefix=None):
        d = super(LayoutExternalPort, self).toElkJson(idStore, isTop=isTop, path_prefix=path_prefix)
        d["hwMeta"]['isExternalPort'] = True
        # d['properties']["org.eclipse.elk.layered.layering.layerConstraint"] = self.layeringLayerConstraint.name
        return d
