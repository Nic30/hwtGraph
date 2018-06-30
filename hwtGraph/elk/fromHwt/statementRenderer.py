from typing import Union, List, Optional, Tuple

from hwt.hdl.assignment import Assignment
from hwt.hdl.ifContainter import IfContainer
from hwt.hdl.operator import Operator, isConst
from hwt.hdl.operatorDefs import AllOps
from hwt.hdl.statements import HdlStatement
from hwt.hdl.switchContainer import SwitchContainer
from hwt.hdl.types.array import HArray
from hwt.hdl.value import Value
from hwt.synthesizer.rtlLevel.mainBases import RtlSignalBase
from hwt.synthesizer.rtlLevel.netlist import walk_assignments
from hwtGraph.elk.containers.constants import PortType, PortSide
from hwtGraph.elk.containers.lNode import LNode
from hwtGraph.elk.containers.lPort import LPort
from hwtGraph.elk.fromHwt.statementRendererUtils import VirtualLNode, \
    walkStatementsForSig
from hwtGraph.elk.fromHwt.utils import ValueAsLNode,\
    isUselessTernary, isUselessEq, NetCtxs, NetCtx


FF = "FF"
MUX = "MUX"
LATCHED_MUX = "LATCHED_MUX"
RAM_WRITE = "RAM_WRITE"
RAM_READ = "RAM_READ"
CONNECTION = "CONNECTION"

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


class StatementRenderer():
    def __init__(self, node: LNode, toL, portCtx, rootNetCtxs):
        self.stm = node.originObj
        self.toL = toL
        self.portCtx = portCtx
        self.rootNetCtxs = rootNetCtxs
        self.isVirtual = isinstance(node, VirtualLNode)

        if self.isVirtual:
            self.node = node.parent
            self.netCtxs = rootNetCtxs
        else:
            self.node = node
            self.netCtxs = NetCtxs()

    def addInputPort(self, node, name,
                     inpValue: Union[Value, RtlSignalBase],
                     side=PortSide.WEST):
        """
        Add and connect input port on subnode
        """
        root = self.node
        port = node.addPort(name, PortType.INPUT, side)
        if isinstance(inpValue, Value):
            v = ValueAsLNode(root, inpValue).east[0]
            root.addEdge(v, port)
        else:
            if isinstance(inpValue, LPort):
                root.addEdge(inpValue, port)
            else:
                self.connectInput(inpValue, port)

    def addOutputPort(self, node: LNode, name: str,
                      out: Optional[RtlSignalBase],
                      side=PortSide.EAST):
        """
        Add and connect output port on subnode
        """
        oPort = node.addPort(name, PortType.OUTPUT, side)
        if out is not None:
            if isinstance(out, LPort):
                self.node.addEdge(oPort, out)
            elif out.hidden:
                raise NotImplementedError()
            else:
                if self.portCtx is None:
                    ctx, _ = self.rootNetCtxs.getDefault(out)
                    ctx.addDriver(oPort)
                else:
                    _out = self.portCtx.getInside(out, PortType.OUTPUT)
                    self.node.addEdge(oPort, _out)
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
        n = self.node.addNode(RAM_WRITE)
        if clk is not None:
            self.addInputPort(n, "clk", clk)

        self.addInputPort(n, "addr", addr)
        self.addInputPort(n, "in", inp)

        memPort = self.addOutputPort(n, "mem", mem if connectOut else None)

        return n, memPort

    def createRamReadNode(self,
                          mem: RtlSignalBase,
                          clk: Optional[RtlSignalBase],
                          addr: RtlSignalBase,
                          out: RtlSignalBase,
                          connectOut):
        n = self.node.addNode(RAM_WRITE)
        if clk is not None:
            self.addInputPort(n, "clk", clk)

        self.addInputPort(n, "addr", addr)
        self.addInputPort(n, "mem", mem)

        readPort = self.addOutputPort(n, "out", out if connectOut else None)

        return n, readPort

    def createFFNode(self,
                     o: RtlSignalBase,
                     clk: RtlSignalBase,
                     i: RtlSignalBase,
                     connectOut):
        n = self.node.addNode(FF)
        self.addInputPort(n, "clk", clk)
        self.addInputPort(n, "i", i)

        oPort = self.addOutputPort(n, "o", o if connectOut else None)

        return n, oPort

    def createMux(self,
                  output: RtlSignalBase,
                  inputs: List[Union[RtlSignalBase, Value]],
                  control: Union[RtlSignalBase, List[RtlSignalBase]],
                  connectOut,
                  latched=True):
        if latched:
            node_type = LATCHED_MUX
        else:
            node_type = MUX

        root = self.node
        addInputPort = self.addInputPort

        n = root.addNode(node_type)
        if isinstance(control, (RtlSignalBase, Value)):
            control = [control, ]

        for c in control:
            addInputPort(n, "", c, PortSide.SOUTH)

        for i in inputs:
            addInputPort(n, "", i)

        oPort = self.addOutputPort(n, "",
                                   output if connectOut else None)

        return n, oPort

    def createAssignment(self, assig: Assignment, connectOut: bool):
        pctx = self.portCtx
        src = assig.src
        inputs = [src, ]
        if assig.indexes:
            inputs.extend(assig.indexes)

        for s in inputs:
            if (isinstance(s, RtlSignalBase)
                    and s.hidden
                    and s not in self.netCtxs):
                self.lazyLoadNet(s)

        if assig.indexes:
            raise ValueError("This assignment should be processed before")
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

    def connectInput(self, signal: RtlSignalBase, port: LPort):
        """
        :param signal: signal to connect to specified port
        :param port: input port which should be connected with specified signal
        """
        netCtxs = self.netCtxs
        if signal.hidden:
            # later connect driver of this signal to output port
            ctx, wasThereBefore = netCtxs.getDefault(signal)
            if not wasThereBefore:
                self.lazyLoadNet(signal)
            ctx.addEndpoint(port)
        else:
            portCtx = self.portCtx
            rootCtx, _ = self.rootNetCtxs.getDefault(signal)

            if portCtx is None:
                # later connect signal in root to input port or input port of
                # wrap node
                rootCtx.addEndpoint(port)
            else:
                # spot input port on this wrap node if required
                isNewlySpotted = (signal, PortType.INPUT) not in portCtx.data
                src = portCtx.register(signal, PortType.INPUT)
                # connect input port on wrap node with specified output port
                ctx, _ = netCtxs.getDefault(signal)
                ctx.addDriver(src)
                ctx.addEndpoint(port)

                if isNewlySpotted:
                    # get input port from parent view
                    _port = portCtx.getOutside(signal, PortType.INPUT)
                    rootCtx.addEndpoint(_port)

    def getInputNetCtx(self, signal: RtlSignalBase):
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

            if portCtx is not None:
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
        assert len(signal.drivers) == 1, signal
        driver = signal.drivers[0]
        if isinstance(driver, Operator):
            d = self.addOperatorAsLNode(driver)
            if isinstance(d, LNode):
                c, _ = self.netCtxs.getDefault(signal)
                c.addDriver(d.east[0])
            else:
                self.netCtxs.joinNetsByKeyVal(signal, d)

    def addOperatorAsLNode(self, op: Operator) -> Union[LNode, NetCtx]:
        root = self.node
        if isUselessTernary(op):
            # is in format 1 if cond else 0
            # retunr NetCtx of cond directly
            cond = op.operands[0]
            return self.getInputNetCtx(cond)
        elif isUselessEq(op):
            s = op.operands[0]
            return self.getInputNetCtx(s)

        if op.operator == AllOps.INDEX:
            inputNames = ["in", "index"]
        else:
            inputNames = [None for _ in op.operands]

        u = root.addNode(originObj=op, name=op.operator.id)
        u.addPort(None, PortType.OUTPUT, PortSide.EAST)

        for inpName, op in zip(inputNames, op.operands):
            p = u.addPort(inpName,  PortType.INPUT,  PortSide.WEST)

            if isConst(op):
                op = op.staticEval()
                v = ValueAsLNode(root, op).east[0]
                root.addEdge(v, p)
            else:
                self.connectInput(op, p)

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
            if portCtx is not None:
                portCtx.register(o, PortType.OUTPUT)
            self.renderForSignal(stm, o, True)

        if not self.isVirtual:
            self.netCtxs.applyConnections(self.node)

    def renderEventDepIfContainer(self, ifStm: IfContainer, s: RtlSignalBase, connectOut):
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
            raise NotImplementedError()
        else:
            clk = clk_spec[0]
        return self.createRamWriteNode(assig.dst, clk, addr,
                                       assig.src, connectOut)

    def renderForSignal(self, stm: Union[HdlStatement, List[HdlStatement]],
                        s: RtlSignalBase,
                        connectOut) -> Tuple[LNode, Union[RtlSignalBase, LPort]]:
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
        full_ev_dep = stm._is_completly_event_dependent
        par = stm.parentStm
        parent_ev_dep = par is not None and par._now_is_event_dependent

        # render IfContainer instances
        if isinstance(stm, IfContainer):
            if isinstance(s._dtype, HArray):
                # ram output port
                # [TODO]
                clk = stm.cond
                for a in walk_assignments(stm, s):
                    assert len(a.indexes) == 1, "one address per RAM port"
                    addr = a.indexes[0]
                return self.createRamWriteNode(s, clk, addr,
                                               a.src, connectOut)

            elif full_ev_dep and not parent_ev_dep:
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
            latched = s in encl
            inputs = []
            for _, stms in stm.cases:
                inputs.append(self.renderForSignal(stms, s, False)[1])

            if stm.default:
                inputs.append(self.renderForSignal(
                    stm.default, s, False)[1])

            return self.createMux(s, inputs, stm.switchOn, connectOut,
                                  latched=latched)
        else:
            raise TypeError(stm)
