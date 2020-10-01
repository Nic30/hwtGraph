from hwt.hdl.operator import Operator
from hwt.hdl.portItem import HdlPortItem
from hwt.pyUtils.uniqList import UniqList


def walkSignalEndpointsToStatements(sig):
    assert sig.hidden, sig
    for ep in sig.endpoints:
        if isinstance(ep, Operator):
            yield from walkSignalEndpointsToStatements(ep.result)
        else:
            yield ep


def connectSignalToStatements(s, toL, stmPorts, root, reducedStatements):
    driverPorts = UniqList()
    endpointPorts = UniqList()

    def addEndpoint(ep):
        if isinstance(ep, HdlPortItem):
            dst = toL[ep]
            endpointPorts.append(dst)
        elif ep in reducedStatements:
            raise NotImplementedError()
        else:
            laStm = toL[ep]
            dst = stmPorts[laStm].getOutside(s)
            endpointPorts.append(dst)

    # connect all drivers of this signal with all endpoints
    for stm in s.drivers:
        node = toL[stm]
        if isinstance(stm, HdlPortItem):
            src = node
        elif isinstance(stm, Operator):
            continue
        elif stm in reducedStatements:
            src = node.east[0]
        else:
            src = stmPorts[node].getOutside(s)

        assert src.parentNode.parent == root, (s, node)
        driverPorts.append(src)

    for stm in s.endpoints:
        if isinstance(stm, Operator):
            for ep in walkSignalEndpointsToStatements(stm.result):
                addEndpoint(ep)
        else:
            addEndpoint(stm)

    if not (driverPorts and endpointPorts):
        print("Warning signal endpoints/drivers not discovered", s)

    root.addHyperEdge(driverPorts, endpointPorts, name=s.name, originObj=s)
