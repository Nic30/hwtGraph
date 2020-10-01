from hwt.code import Concat
from hwt.hdl.assignment import Assignment
from hwt.hdl.operator import isConst, Operator
from hwt.hdl.operatorDefs import AllOps
from hwt.hdl.statement import HdlStatement
from hwt.hdl.types.array import HArray
from hwt.hdl.types.bits import Bits
from hwt.pyUtils.arrayQuery import arr_all
from hwt.pyUtils.uniqList import UniqList
from hwt.synthesizer.rtlLevel.mainBases import RtlSignalBase
from hwt.synthesizer.rtlLevel.netlist import RtlNetlist
from hwt.serializer.utils import RtlSignal_sort_key


def indexedAssignmentsToConcatenation(netlist: RtlNetlist):
    signalsToReduce = set()

    for s in sorted(netlist.signals, key=RtlSignal_sort_key):
        if len(s.drivers) > 1 and isinstance(s._dtype, Bits):
            compatible = True
            for d in s.drivers:
                if not isinstance(d, Assignment)\
                        or len(d.indexes) != 1\
                        or not isConst(d.indexes[0]):
                    compatible = False
                    break

            if compatible:
                signalsToReduce.add(s)

    for s in sorted(signalsToReduce, key=RtlSignal_sort_key):
        inputs = []
        # list() because a collection may change during the iteration
        for d in list(s.drivers):
            i = d.indexes[0].staticEval().to_py()
            if isinstance(i, int):
                i = slice(i + 1, i)
            v = d.src
            inputs.append((i, v))
            d._destroy()

        inputs.sort(key=lambda x: x[0].stop)
        s(Concat(*[x[1] for x in inputs]))


def unhideResultsOfIndexingAndConcatOnPublicSignals(netlist):
    openset = UniqList(sorted(
        (s for s in netlist.signals if not s.hidden),
        key=RtlSignal_sort_key
    ))
    epsToReplace = []
    while openset:
        s = openset.pop()
        for ep in s.endpoints:
            # search for index ops
            if isinstance(ep, Operator)\
                    and ep.operator == AllOps.INDEX\
                    and ep.operands[0] is s:
                isIndexInBramWrite = isinstance(s._dtype, HArray)\
                    and arr_all(ep.result.endpoints,
                                lambda ep: isinstance(ep, HdlStatement)\
                                           and ep._event_dependent_from_branch == 0)
                if not isIndexInBramWrite and ep.result.hidden:
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
            openset.append(r)
        epsToReplace.clear()
