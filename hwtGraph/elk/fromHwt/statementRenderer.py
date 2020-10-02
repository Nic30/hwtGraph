from itertools import chain
from typing import Union, List, Optional, Tuple

from hwt.hdl.assignment import Assignment
from hwt.hdl.ifContainter import IfContainer
from hwt.hdl.operator import Operator, isConst
from hwt.hdl.operatorDefs import AllOps
from hwt.hdl.statement import HdlStatement
from hwt.hdl.switchContainer import SwitchContainer
from hwt.hdl.types.array import HArray
from hwt.hdl.value import HValue
from hwt.pyUtils.arrayQuery import arr_any
from hwt.synthesizer.rtlLevel.mainBases import RtlSignalBase
from hwtGraph.elk.containers.constants import PortType, PortSide
from hwtGraph.elk.containers.lNode import LNode
from hwtGraph.elk.containers.lPort import LPort
from hwtGraph.elk.fromHwt.netCtx import NetCtx, NetCtxs
from hwtGraph.elk.fromHwt.statementRendererUtils import VirtualLNode, \
    walkStatementsForSig, Signal2stmPortCtx
from hwtGraph.elk.fromHwt.utils import ValueAsLNode, \
    isUselessTernary, isUselessEq


FF = "FF"
MUX = "MUX"
LATCHED_MUX = "LATCHED_MUX"
RAM_WRITE = "RAM_WRITE"
RAM_READ = "RAM_READ"
CONNECTION = "CONNECTION"
ITEM_SET = "ITEM_SET"

#                     __________
# if rising(clk): clk-|>       |
#     a(1)         1--|in   out|---a
#
#                              __________
# if rising(clk):  1-|-\   clk-|>       |
#     if b:          |  >------|in   out|---a
#        a(1)      2-|-/
#     else:           |
#        a(2)         b
#


def detectRamPorts(stm: IfContainer, current_en: RtlSignalBase):
    """
    Detect RAM ports in If statement

    :param stm: statement to detect the ram ports in
    :param current_en: current en/clk signal
    """
    if stm.ifFalse or stm.elIfs:
        return
    for _stm in stm.ifTrue:
        if isinstance(_stm, IfContainer):
            yield from detectRamPorts(_stm, _stm.cond & current_en)
        elif isinstance(_stm, Assignment):
            if isinstance(_stm.dst._dtype, HArray):
                assert len(_stm.indexes) == 1, "one address per RAM port"
                w_addr = _stm.indexes[0]
                mem = _stm.dst
                yield (RAM_WRITE, mem, w_addr, current_en, _stm.src)
            elif _stm.src.hidden and len(_stm.src.drivers) == 1:
                op = _stm.src.drivers[0]
                mem = op.operands[0]
                if isinstance(mem._dtype, HArray) and op.operator == AllOps.INDEX:
                    r_addr = op.operands[1]
                    if _stm.indexes:
                        raise NotImplementedError()
                    yield (RAM_READ, mem, r_addr, current_en, _stm.dst)


class StatementRenderer():
    """
    Render nodes of statement into node or parent node
    """

    def __init__(self, node: Union[LNode, VirtualLNode], toL,
                 portCtx: Optional[Signal2stmPortCtx], rootNetCtxs: NetCtx):
        """
        :param node: node where nodes of this statement should be rendered
        :param toL: dictionary for mapping of HDL object to layout objects
        :param portCtx: optional instance of Signal2stmPortCtx
            for resolving of component port for RtlSignal/Interface instance
        :param rootNetCtxs: NetCtx of parent node for lazy net connection
        """
        self.stm = node.originObj
        self.toL = toL
        self.portCtx = portCtx
        self.rootNetCtxs = rootNetCtxs
        self.isVirtual = isinstance(node, VirtualLNode)

        if self.isVirtual:
            assert portCtx is None
            self.node = node.parent
            self.netCtxs = rootNetCtxs
        else:
            assert portCtx is not None
            self.node = node
            self.netCtxs = NetCtxs(node)

    def addInputPort(self, node, name,
                     i: Union[HValue, RtlSignalBase],
                     side=PortSide.WEST):
        """
        Add and connect input port on subnode

        :param node: node where to add input port
        :param name: name of newly added port
        :param i: input value
        :param side: side where input port should be added
        """
        root = self.node
        port = node.addPort(name, PortType.INPUT, side)
        netCtxs = self.netCtxs

        if isinstance(i, LPort):
            root.addEdge(i, port)
        elif isConst(i):
            i = i.staticEval()
            c, wasThereBefore = self.netCtxs.getDefault(i)
            if not wasThereBefore:
                v = ValueAsLNode(root, i).east[0]
                c.addDriver(v)
            c.addEndpoint(port)
        elif i.hidden:
            # later connect driver of this signal to output port
            ctx, wasThereBefore = netCtxs.getDefault(i)
            if not wasThereBefore:
                self.lazyLoadNet(i)
            ctx.addEndpoint(port)
        else:
            portCtx = self.portCtx
            rootCtx, _ = self.rootNetCtxs.getDefault(i)

            if self.isVirtual:
                # later connect signal in root to input port or input port of
                # wrap node
                rootCtx.addEndpoint(port)
            else:
                # spot input port on this wrap node if required
                isNewlySpotted = (i, PortType.INPUT) not in portCtx.data
                src = portCtx.register(i, PortType.INPUT)
                # connect input port on wrap node with specified output port
                ctx, _ = netCtxs.getDefault(i)
                ctx.addDriver(src)
                ctx.addEndpoint(port)

                if isNewlySpotted:
                    # get input port from parent view
                    _port = portCtx.getOutside(i, PortType.INPUT)
                    rootCtx.addEndpoint(_port)

    def addOutputPort(self, node: LNode, name: str,
                      out: Optional[Union[RtlSignalBase, LPort]],
                      origObj: Union[RtlSignalBase, LPort],
                      side=PortSide.EAST):
        """
        Add and connect output port on subnode
        """
        oPort = node.addPort(name, PortType.OUTPUT, side, originObj=origObj)
        if out is not None:
            if isinstance(out, LPort):
                self.node.addEdge(oPort, out)
            elif out.hidden:
                raise ValueError("Hidden signals should not be connected to outside", name)
            elif self.isVirtual:
                # This node is inlined inside of parent.
                # Mark that this output of subnode should be connected
                # to output of parent node.
                ctx, _ = self.netCtxs.getDefault(out)
                ctx.addDriver(oPort)
            else:
                # connect my signal to my output port
                _out = self.portCtx.getInside(out, PortType.OUTPUT)
                self.node.addEdge(oPort, _out, originObj=out)
                # mark connection of output port to parent net
                ooPort = self.portCtx.getOutside(out, PortType.OUTPUT)
                ctx, _ = self.rootNetCtxs.getDefault(out)
                ctx.addDriver(ooPort)

        return oPort

    def createRamWriteNode(self,
                           mem: RtlSignalBase,
                           clk: Optional[RtlSignalBase],
                           addr: RtlSignalBase,
                           inp: RtlSignalBase,
                           connectOut):
        n = self.node.addNode(RAM_WRITE, cls="Operator")
        if clk is not None:
            self.addInputPort(n, "clk", clk)

        self.addInputPort(n, "addr", addr)
        self.addInputPort(n, "in", inp)

        memPort = self.addOutputPort(n, "mem", mem if connectOut else None, origObj=mem)

        return n, memPort

    def createRamReadNode(self,
                          mem: RtlSignalBase,
                          clk: Optional[RtlSignalBase],
                          addr: RtlSignalBase,
                          out: RtlSignalBase,
                          connectOut):
        n = self.node.addNode(RAM_READ, cls="Operator")
        if clk is not None:
            self.addInputPort(n, "clk", clk)

        self.addInputPort(n, "addr", addr)
        self.addInputPort(n, "mem", mem)

        readPort = self.addOutputPort(n, "out", out if connectOut else None, origObj=out)

        return n, readPort

    def createFFNode(self,
                     o: RtlSignalBase,
                     clk: RtlSignalBase,
                     i: RtlSignalBase,
                     connectOut):
        n = self.node.addNode(FF, cls="Operator")
        self.addInputPort(n, "clk", clk)
        self.addInputPort(n, "i", i)

        oPort = self.addOutputPort(n, "o", o if connectOut else None, origObj=o)

        return n, oPort

    def createMux(self,
                  output: RtlSignalBase,
                  inputs: List[Union[RtlSignalBase, HValue]],
                  control: Union[RtlSignalBase, List[RtlSignalBase]],
                  connectOut,
                  latched=True):
        if latched:
            node_type = LATCHED_MUX
        else:
            node_type = MUX

        root = self.node
        addInputPort = self.addInputPort

        n = root.addNode(node_type, cls="Operator")
        if isinstance(control, (RtlSignalBase, HValue)):
            control = [control, ]
        else:
            assert isinstance(control, (list, tuple))

        for c in control:
            addInputPort(n, "", c, PortSide.SOUTH)

        assert isinstance(inputs, (list, tuple))
        for i in inputs:
            addInputPort(n, "", i)

        oPort = self.addOutputPort(n, "",
                                   output if connectOut else None,
                                   origObj=output)

        return n, oPort

    def createAssignment(self, assig: Assignment, connectOut: bool):
        pctx = self.portCtx
        src = assig.src
        inputs = [src, ]
        isBitToVectorConv = False
        if assig.indexes:
            # if len(assig.indexes) > 1:
            #    raise NotImplementedError()
            i = assig.indexes[0]
            if len(assig.indexes) == 1\
                    and isConst(i)\
                    and assig.dst._dtype.bit_length() == src._dtype.bit_length() == 1:
                # bit to vector conversion
                isBitToVectorConv = True
            else:
                inputs.extend(assig.indexes)

        for s in inputs:
            if (not isConst(s)
                    and s.hidden
                    and s not in self.netCtxs):
                self.lazyLoadNet(s)

        if not isBitToVectorConv and assig.indexes:
            if len(assig.indexes) == 1 and not isConst(assig.indexes[0]):
                # assignments to separate bites are extracted
                # by indexedAssignmentsToConcatenation as concatenation
                # this has to be kind of MUX
                controls = [assig.indexes[0], ]
                return self.createMux(assig.dst, inputs, controls, connectOut,
                                      latched=False)
            else:
                for i in assig.indexes:
                    assert isConst(i), (i, "It is expected that this is staticaly indexed connection to items of array")
                body_text = "".join(["[%d]" % int(i) for i in assig.indexes])
                n = self.node.addNode(ITEM_SET, cls="Operator", bodyText=body_text)
                self.addInputPort(n, "", assig.src)
                oPort = self.addOutputPort(n, "",
                                           assig.dst if connectOut else None,
                                           oriObj=assig.dst)
                return n, oPort

        elif connectOut:
            dst = assig.dst
            rootNetCtxs = self.rootNetCtxs
            if pctx is None:
                # connect to original dst signal directly
                ctx, _ = rootNetCtxs.getDefault(dst)
                ctx.addDriver(src)
                assert rootNetCtxs[dst] is rootNetCtxs[src]
                return None, dst
            else:
                # connect src to dst port on this wrap
                dstPort = pctx.getInside(dst,
                                         PortType.OUTPUT)
                raise NotImplementedError()
                # connect original signal from port on this wrap

                odstPort = pctx.getOutside(dst)
                ctx, _ = rootNetCtxs.getDefault(dst)
                ctx.addDriver(odstPort)
                return None, dstPort
        else:
            return None, assig.src

    def getInputNetCtx(self, signal: RtlSignalBase) -> NetCtx:
        netCtxs = self.netCtxs
        if signal.hidden:
            # later connect driver of this signal to output port
            ctx, wasThereBefore = netCtxs.getDefault(signal)
            if not wasThereBefore:
                self.lazyLoadNet(signal)

        else:
            portCtx = self.portCtx
            ctx, _ = netCtxs.getDefault(signal)
            rootCtx, _ = self.rootNetCtxs.getDefault(signal)

            if not self.isVirtual:
                # spot input port on this wrap node if required
                isNewlySpotted = (signal, PortType.INPUT) not in portCtx.data
                src = portCtx.register(signal, PortType.INPUT)
                # connect input port on wrap node with specified output port
                ctx.addDriver(src)

                if isNewlySpotted:
                    # get input port from parent view
                    _port = portCtx.getOutside(signal, PortType.INPUT)
                    # later connect signal in root to input port or input port
                    # of wrap node
                    rootCtx.addEndpoint(_port)

        return ctx

    def lazyLoadNet(self, signal: RtlSignalBase):
        """
        :param signal: top signal of hidden operator tree
        :note: operator tree is constrained by signals with hidden==False
        :note: statement nodes are not connected automatically
        """
        d_cnt = len(signal.drivers)
        if d_cnt == 1:
            driver = signal.drivers[0]
            if isinstance(driver, Operator):
                d = self.addOperatorAsLNode(driver)

                if isinstance(d, LNode):
                    c, _ = self.netCtxs.getDefault(signal)
                    c.addDriver(d.east[0])
                else:
                    self.netCtxs.joinNetsByKeyVal(signal, d)

        elif d_cnt == 0 and signal.def_val._isFullVld():
            raise AssertionError("Value of this net should have been already rendered")
        else:
            raise AssertionError(signal, signal.drivers)

    def addOperatorAsLNode(self, op: Operator) -> Union[LNode, NetCtx]:
        root = self.node
        if isUselessTernary(op) or isUselessEq(op):
            # is in format 1 if cond else 0
            # return NetCtx of cond directly
            s = op.operands[0]
            net_ctx = self.getInputNetCtx(s)
            #self.netCtxs.joinNetsByValKey(net_ctx, op.result)
            return net_ctx

        if op.operator == AllOps.INDEX:
            inputNames = ["in", "index"]
        elif op.operator == AllOps.CONCAT:
            inputNames = []
            bit_offset = 0
            for o in op.operands:
                w = o._dtype.bit_length()
                if w > 1:
                    name = "[%d:%d]" % (w + bit_offset, bit_offset)
                else:
                    name = "[%d]" % bit_offset
                inputNames.append(name)
                bit_offset += w
        else:
            inputNames = [None for _ in op.operands]

        u = root.addNode(originObj=op, name=op.operator.id, cls="Operator")
        u.addPort(None, PortType.OUTPUT, PortSide.EAST)

        for inpName, _op in zip(inputNames, op.operands):
            self.addInputPort(u, inpName, _op)

        return u

    def renderContent(self):
        """
        Walk from outputs to inputs
        for each public signal register port of wrap node if required
        lazy load all operator and statement nodes for signals
        """
        stm = self.stm
        portCtx = self.portCtx
        # for each inputs and outputs render expression trees

        # walk statements and render muxs and memories
        for o in stm._outputs:
            if not self.isVirtual:
                portCtx.register(o, PortType.OUTPUT)

        canHaveRamPorts = isinstance(stm, IfContainer) and arr_any(
            chain(stm._inputs, stm._outputs),
            lambda s: isinstance(s._dtype, HArray))
        # render RAM ports
        consumedOutputs = set()
        if canHaveRamPorts:
            for pType, memSig, addrSig, enSig, io in detectRamPorts(stm, stm.cond):
                if pType == RAM_READ:
                    self.createRamReadNode(memSig, enSig, addrSig,
                                           io, True)
                    consumedOutputs.add(io)

                elif pType == RAM_WRITE:
                    self.createRamWriteNode(memSig, enSig, addrSig,
                                            io, True)
                    consumedOutputs.add(memSig)

                else:
                    raise TypeError()

        for o in stm._outputs:
            if o not in consumedOutputs:
                self.renderForSignal(stm, o, True)

        if not self.isVirtual:
            self.netCtxs.applyConnections(self.node)

    def renderEventDepIfContainer(self, ifStm: IfContainer,
                                  s: RtlSignalBase, connectOut):
        assert not ifStm.ifFalse, ifStm
        if ifStm.elIfs:
            raise NotImplementedError(MUX)

        subStms = list(walkStatementsForSig(ifStm.ifTrue, s))
        assert len(subStms) == 1, subStms
        subStm = subStms[0]

        assig = None
        clk_spec = [ifStm.cond, ]
        subStm_tmp = subStm
        while True:
            if isinstance(subStm_tmp, IfContainer):
                clk_spec.append(subStm.cond)
                subStm_tmp = list(walkStatementsForSig(subStm_tmp.ifTrue, s))
                assert len(subStm_tmp) == 1, subStm_tmp
                subStm_tmp = subStm_tmp[0]
                continue

            elif isinstance(subStm_tmp, Assignment):
                if subStm_tmp.indexes:
                    assig = subStm_tmp
                    break

            break

        if assig is None:
            _, _in = self.renderForSignal(subStm, s, False)
            return self.createFFNode(s, ifStm.cond, _in, connectOut)

        if len(assig.indexes) != 1:
            raise NotImplementedError()

        addr = assig.indexes[0]
        # ram write port
        # collect clk and clk_en

        if len(clk_spec) > 1:
            raise NotImplementedError(ifStm, clk_spec)
        else:
            clk = clk_spec[0]
        return self.createRamWriteNode(assig.dst, clk, addr,
                                       assig.src, connectOut)

    def renderForSignal(self, stm: Union[HdlStatement, List[HdlStatement]],
                        s: RtlSignalBase,
                        connectOut) -> Optional[Tuple[LNode, Union[RtlSignalBase, LPort]]]:
        """
        Walk statement and render nodes which are representing
        hardware components (MUX, LATCH, FF, ...) for specified signal
        """
        # filter statements for this signal only if required
        if not isinstance(stm, HdlStatement):
            stm = list(walkStatementsForSig(stm, s))
            if not stm:
                return None
            elif len(stm) != 1:
                raise NotImplementedError("deduced MUX")
            else:
                stm = stm[0]

        # render assignment instances
        if isinstance(stm, Assignment):
            return self.createAssignment(stm, connectOut)

        encl = stm._enclosed_for
        full_ev_dep = stm._event_dependent_from_branch == 0
        par = stm.parentStm
        parent_ev_dep = par is not None and par._event_dependent_from_branch is not None

        # render IfContainer instances
        if isinstance(stm, IfContainer):
            if full_ev_dep and not parent_ev_dep:
                # FF with optional MUX
                return self.renderEventDepIfContainer(stm, s, connectOut)

            else:
                latched = par is None and not parent_ev_dep and s not in encl
                # MUX/LATCH/MUX+LATCH
                controls = [stm.cond]
                ren = self.renderForSignal(stm.ifTrue, s, False)
                if ren is not None:
                    inputs = [ren[1]]
                else:
                    inputs = []

                for c, stms in stm.elIfs:
                    controls.append(c)
                    ren = self.renderForSignal(stms, s, False)
                    if ren is not None:
                        inputs.append(ren[1])

                if stm.ifFalse:
                    ren = self.renderForSignal(stm.ifFalse, s, False)
                    if ren is not None:
                        inputs.append(ren[1])

                return self.createMux(s, inputs, controls, connectOut,
                                      latched=latched)

        # render SwitchContainer instances
        elif isinstance(stm, SwitchContainer):
            latched = s not in encl
            inputs = []
            for _, stms in stm.cases:
                d = self.renderForSignal(stms, s, False)
                if d is not None:
                    _, port = d
                    inputs.append(port)
                else:
                    assert latched, (s, stm)

            if stm.default:
                d = self.renderForSignal(stm.default, s, False)
                if d is not None:
                    _, port = d
                    inputs.append(port)
                else:
                    assert latched, (s, stm)

            return self.createMux(s, inputs, stm.switchOn, connectOut,
                                  latched=latched)
        else:
            raise TypeError(stm)
