from itertools import chain
from typing import List

from hwtGraph.elk.containers.constants import PortSide, PortType


class LPort():
    """
    Port for component in component diagram

    :ivar originObj: original object which this node represents
    :ivar parent: parent unit of this port
    :ivar name: name of this port
    :ivar direction: direction of this port
    :ivar geometry: absolute geometry in layout
    :ivar children: list of children ports, before interface connecting phase
            (when routing this list is empty and children are directly on parent LNode)
    :ivar index: The index of a port in the fixed order around a node.
        The order is assumed as clockwise, starting with the leftmost port on the top side.
        This option must be set if ‘Port Constraints’ is set to FIXED_ORDER
        and no specific positions are given for the ports. Additionally,
        the option ‘Port Side’ must be defined in this case.
    """

    def __init__(self, parent: "LNode", direction: PortType,
                 side: PortSide, name: str=None):
        super(LPort, self).__init__()
        self.originObj = None
        self.parent = parent
        if isinstance(parent, LPort):
            self.parentNode = parent.parentNode
        else:
            self.parentNode = parent

        self.name = name
        self.direction = direction

        self.outgoingEdges = []
        self.incomingEdges = []
        self.children = []
        self.side = side
        self.index = None

    def getLevel(self):
        """
        Get nest-level of this port
        """
        lvl = 0
        p = self
        while True:
            p = p.parent
            if not isinstance(p, LPort):
                break
            lvl += 1
        return lvl

    def iterEdges(self, filterSelfLoops=False):
        it = chain(self.incomingEdges, self.outgoingEdges)
        if filterSelfLoops:
            for e in it:
                if not e.isSelfLoop:
                    yield e
        else:
            yield from it

    def _getDebugName(self) -> List[str]:
        names = []
        p = self
        while True:
            if p is None:
                break
            name = p.name
            if name is None:
                if isinstance(p, LPort) and p.parent is not None:
                    index = p.parent.getPortSideView(p.side).index(p)
                    name = "[%d]" % (index)
                else:
                    name = "<Unnamed>"
            names.append(name)
            p = p.parent
        return list(reversed(names))

    def toElkJson(self, idStore):
        props = {
            "portSide": self.side.name,
        }

        if self.parentNode.portConstraints.isOrderFixed():
            assert isinstance(self.index, int), self.index
            props["portIndex"] = self.index

        return {
            "id": str(idStore[self]),
            "hwt": {
                "level": self.getLevel(),
                "name": self.name,
            },
            "direction": self.direction.name,
            "properties": props,
        }

    def __repr__(self):
        return "<{0} {1:#018x} {2}>".format(
            self.__class__.__name__, id(self), ".".join(self._getDebugName()))
