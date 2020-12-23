from hwt.code import Concat
from hwt.hdl.assignment import Assignment
from hwt.hdl.operator import isConst, Operator
from hwt.hdl.operatorDefs import AllOps
from hwt.hdl.statement import HdlStatement
from hwt.hdl.types.array import HArray
from hwt.hdl.types.bits import Bits
from hwt.pyUtils.arrayQuery import arr_all
from hwt.pyUtils.uniqList import UniqList
from hwt.synthesizer.rtlLevel.netlist import RtlNetlist
from hwt.serializer.utils import RtlSignal_sort_key


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
            ep._destroy()

            # instantiate new hidden signal for result of index
            new_r = s[i]
            assert new_r is not r, r
            # and instantiate Assignment to this new signal from the
            # old one
            r(new_r)
            openset.append(r)

        epsToReplace.clear()
