from copy import deepcopy

from hwt.hdl.statements.assignmentContainer import HdlAssignmentContainer
from hwt.hdl.statements.codeBlockContainer import HdlStmCodeBlockContainer
from hwt.hdl.statements.ifContainter import IfContainer
from hwt.hdl.statements.statement import HdlStatement
from hwt.hdl.statements.switchContainer import SwitchContainer
from hwt.hdl.statements.utils.listOfHdlStatements import ListOfHdlStatement
from hwt.synthesizer.rtlLevel.netlist import RtlNetlist
from hwt.synthesizer.rtlLevel.rtlNetlistPass import RtlNetlistPass
from hwt.synthesizer.rtlLevel.rtlSignal import RtlSignal


class HdlStatementCopier():

    def __init__(self, stm: HdlStatement):
        self.stm = stm

    def __call__(self) -> HdlStatement:
        stm = deepcopy(self.stm)
        assert stm.parentStm is None, stm
        return stm


def propagatePresets_stm_list(stm_list: ListOfHdlStatement, output_sig: RtlSignal):
    """
    If multiple statements are driving output_sig merge them into just one.
    """
    currently_last_driver = None
    removed = []
    for i, stm in enumerate(stm_list):
        stm: HdlStatement
        if output_sig in stm._outputs:
            if currently_last_driver is None:
                currently_last_driver = (i, stm)
            else:
                prev_i, prev_stm = currently_last_driver
                prev_stm: HdlStatement
                stm._discover_enclosure()
                stm._fill_enclosure({output_sig: HdlStatementCopier(prev_stm)})
                stm._clean_signal_meta()
                removed.append((prev_i, prev_stm))
                currently_last_driver = (i, stm)

    if removed:
        for i, stm in reversed(removed):
            if stm.parentStm is not None:
                stm.parentStm._replace_child_statement(stm, [], False)
            else:
                # we must pop from the end in order to not break the indexing
                stm_list.pop(i)

    for stm in stm_list:
        propagatePresets_stm(stm)


def propagatePresets_stm(stm: HdlStatement):
    if isinstance(stm, HdlAssignmentContainer):
        pass

    elif isinstance(stm, IfContainer):
        stm: IfContainer
        for output_sig in stm._outputs:
            propagatePresets_stm_list(stm.ifTrue, output_sig)
            for _, stms in stm.elIfs:
                propagatePresets_stm_list(stms, output_sig)
            if stm.ifFalse:
                propagatePresets_stm_list(stm.ifFalse, output_sig)

    elif isinstance(stm, SwitchContainer):
        stm: SwitchContainer
        for output_sig in stm._outputs:
            for _, stms in stm.cases:
                propagatePresets_stm_list(stms, output_sig)
            if stm.default is not None:
                propagatePresets_stm_list(stm.default, output_sig)

    elif isinstance(stm, HdlStmCodeBlockContainer):
        stm: HdlStmCodeBlockContainer
        for output_sig in stm._outputs:
            propagatePresets_stm_list(stm.statements, output_sig)

    else:
        raise NotImplementedError(stm)


class RtlNetlistPassPropagatePresets(RtlNetlistPass):

    def runOnRtlNetlist(self, netlist: RtlNetlist):
        """
        Converts the format of statement branches into a format where each output
        is driven just by a single statement.
    
        :note: The example bellow is with a simple if and assignment but this function
            should convert any number of any statements.
    
        .. code-block::
    
            c = 0
            if b:
                c = 1
    
            # to
    
            if b:
                c = 1
            else:
                c = 0
    
    
        """

        for stm in netlist.statements:
            propagatePresets_stm(stm)

