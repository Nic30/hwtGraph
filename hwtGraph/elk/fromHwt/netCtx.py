from typing import Union

from hwt.pyUtils.uniqList import UniqList
from hwt.synthesizer.rtlLevel.mainBases import RtlSignalBase
from hwtGraph.elk.containers.constants import PortType
from hwtGraph.elk.containers.lNode import LNode
from hwtGraph.elk.containers.lPort import LPort


class NetCtxs(dict):
    """
    Dictionary of NetCtx instances
    """

    def __init__(self, parentNode):
        dict.__init__(self)
        self.parentNode = parentNode

    def applyConnections(self, root):
        seen = set()
        for sig, net in sorted(self.items(), key=lambda x: x[1].seqNo):
            if net in seen:
                continue
            seen.add(net)

            if net.endpoints:
                assert net.drivers

            if not net.endpoints:
                # unconnected input or constant which was replaced by value
                # assert not sig.endpoints\
                #        or isConst(sig), (sig, sig.endpoints)
                continue

            if len(net.actualKeys) == 1:
                originObj = net.actualKeys[0]
            else:
                originObj = tuple(net.actualKeys)
            root.addHyperEdge(list(net.drivers), list(net.endpoints),
                              name=repr(sig), originObj=originObj)

    def joinNetsByKey(self, k0, k1):
        v0, _ = self.getDefault(k0)
        v1, _ = self.getDefault(k1)
        if v0 is v1:
            return v0

        v0.extend(v1)
        v0.actualKeys.extend(v1.actualKeys)

        self[k1] = v0
        return v0

    def joinNetsByKeyVal(self, k0, v1: "NetCtx"):
        v0, _ = self.getDefault(k0)
        if v0 is v1:
            return v0

        v0.extend(v1)
        v0.actualKeys.extend(v1.actualKeys)

        for k in v1.actualKeys:
            self[k] = v0

        return v0

    def joinNetsByValKey(self, v0: "NetCtx", k1):
        v1, _ = self.getDefault(k1)
        if v0 is v1:
            return v0

        v0.extend(v1)
        v0.actualKeys.extend(v1.actualKeys)

        for k in v1.actualKeys:
            self[k] = v0

        return v0

    def getDefault(self, k):
        """
        :return: tuple (value, True if key was there before else False)
        """
        try:
            return self[k], True
        except KeyError:
            v = self[k] = NetCtx(self, k, len(self))
            return v, False


class NetCtx():

    def __init__(self, others: NetCtxs, actualKey, seqNo: int):
        """
        :param seqNo: sequential number used to sustain determinism while iterating over instances of this class in dictionary

        """
        self.parentNode = others.parentNode
        assert isinstance(self.parentNode, LNode), self.parentNode
        self.actualKeys = [actualKey, ]
        self.others = others
        self.drivers = UniqList()
        self.endpoints = UniqList()
        self.seqNo = seqNo

    def extend(self, other: "NetCtx"):
        self.drivers.extend(other.drivers)
        self.endpoints.extend(other.endpoints)

    def addDriver(self, src: Union[RtlSignalBase, LPort]):
        if isinstance(src, RtlSignalBase):
            return self.others.joinNetsByKeyVal(src, self)
        else:
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

            return self.drivers.append(src)

    def addEndpoint(self, dst: Union[RtlSignalBase, LPort]):
        if isinstance(dst, RtlSignalBase):
            return self.others.joinNetsByValKey(self, dst)
        else:
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

            return self.endpoints.append(dst)
