from hwt.code import Concat
from hwt.hdl.assignment import Assignment
from hwt.hdl.operator import isConst, Operator
from hwt.hdl.operatorDefs import AllOps
from hwt.synthesizer.rtlLevel.mainBases import RtlSignalBase


def indexedAssignmentsToConcatenation(netlist):
    signalsToReduce = set()

    for s in netlist.signals:
        if len(s.drivers) > 1:
            compatible = True
            for d in s.drivers:
                if not isinstance(d, Assignment)\
                        or len(d.indexes) != 1\
                        or not isConst(d.indexes[0]):
                    compatible = False
                    break

            if compatible:
                signalsToReduce.add(s)

    for s in signalsToReduce:
        inputs = []
        for d in list(s.drivers):
            i = d.indexes[0].staticEval().toPy()
            if isinstance(i, int):
                i = slice(i + 1, i)
            v = d.src
            inputs.append((i, v))
            d._destroy()

        inputs.sort(key=lambda x: x[0].stop)
        s(Concat(*map(lambda x: x[1], inputs)))


def unhideResultsOfIndexingAndConcatOnPublicSignals(netlist):
    openset = set([s for s in netlist.signals if not s.hidden])
    epsToReplace = []
    while openset:
        s = openset.pop()
        for ep in s.endpoints:
            # search for index ops
            if isinstance(ep, Operator) and ep.operator == AllOps.INDEX and ep.operands[0] is s:
                if ep.result.hidden:
                    epsToReplace.append(ep)

        for ep in epsToReplace:
            r = ep.result
            assert len(r.drivers) == 1, r
            r.hidden = False
            i = ep.operands[1]
            # update operator cache of signal
            k = (AllOps.INDEX, i)
            _r = s._usedOps.pop(k)
            assert r is _r
            for o in ep.operands:
                if isinstance(o, RtlSignalBase):
                    o.endpoints.discard(ep)
            r.origin = None
            r.drivers.clear()

            # instantiate new hidden signal for result of index
            new_r = s[i]
            assert new_r is not r, r
            # and instantiate Assignment to this new signal from the
            # old one
            r(new_r)
            openset.add(r)
        epsToReplace.clear()
