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
        self.max_id = 0

    def register(self, obj):
        k = self.get(obj, None)
        if k is not None:
            return k
        k = self.max_id
        self[obj] = k
        self.max_id += 1
        return k

    def getMaxId(self):
        return self.max_id - 1

    def registerNode(self, node: LNode):
        return self.register(node)

    def registerPort(self, port: LPort):
        return self.register(port)

    def registerEdge(self, edge: LEdge):
        return self.register(edge)
