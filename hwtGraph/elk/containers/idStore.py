from hwtGraph.elk.containers.lNode import LNode
from hwtGraph.elk.containers.lPort import LPort
from hwtGraph.elk.containers.lEdge import LEdge


class ElkIdStore(dict):
    """
    :attention: First register nodes then register ports
        otherwise id will not be generated correctly
    """

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.reverseDict = {v: k for k, v in self.items()}

    def register(self, obj):
        if obj in self:
            return
        k = len(self)
        self[obj] = k
        self.reverseDict[k] = obj

    def getMaxId(self):
        return len(self) - 1

    def registerNode(self, node: LNode):
        self.register(node)

    def registerPort(self, port: LPort):
        self.register(port)

    def registerEdge(self, edge: LEdge):
        self.register(edge)
