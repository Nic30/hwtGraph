import unittest

from hwt.code import If
from hwt.hwIOs.std import HwIOSignal
from hwt.hwModule import HwModule
from hwt.pyUtils.typingFuture import override
from hwt.serializer.utils import RtlSignal_sort_key, \
    HdlStatement_sort_key
from hwt.synth import synthesised
from hwtGraph.elk.containers.idStore import ElkIdStore
from hwtGraph.elk.fromHwt.convertor import HwModuleToLNode
from hwtGraph.elk.fromHwt.defauts import DEFAULT_PLATFORM, \
    DEFAULT_LAYOUT_OPTIMIZATIONS
from hwtLib.amba.axi4Lite import Axi4Lite
from hwtLib.amba.axi4s_fullduplex import Axi4StreamFullDuplex
from hwtLib.amba.axiLite_comp.to_axi import AxiLite_to_Axi
from hwtLib.amba.axi_comp.buff import AxiBuff
from hwtLib.amba.axi_comp.cache.tag_array import _example_AxiCacheTagArray
from hwtLib.amba.axi_comp.stream_to_mem import Axi4streamToMem
from hwtLib.amba.axi_comp.tester import AxiTester
from hwtLib.amba.datapump.interconnect.rStricOrder import RStrictOrderInterconnect
from hwtLib.amba.datapump.r import Axi_rDatapump
from hwtLib.amba.datapump.w import Axi_wDatapump
from hwtLib.clocking.cdc import Cdc
from hwtLib.commonHwIO.addr_data_to_Axi import example_AddrDataRdVld_to_Axi
from hwtLib.examples.arithmetic.multiplierBooth import MultiplierBooth
from hwtLib.examples.axi.oooOp.counterHashTable import OooOpExampleCounterHashTable
from hwtLib.examples.builders.ethAddrUpdater import EthAddrUpdater
from hwtLib.examples.hierarchy.hwModuleWrapper_test import HwIOArrayExample
from hwtLib.examples.mem.ram import SimpleAsyncRam
from hwtLib.examples.mem.reg import LatchReg
from hwtLib.examples.operators.indexing import IndexingInernJoin, \
    IndexingInernRangeSplit, IndexingInternSplit
from hwtLib.examples.showcase0 import Showcase0
from hwtLib.examples.simpleHwModuleAxi4Stream import SimpleHwModuleAxi4Stream
from hwtLib.examples.statements.codeBlockStm import BlockStm_complete_override1
from hwtLib.examples.statements.constDriver import ConstDriverHwModule
from hwtLib.examples.statements.ifStm import IfStatementPartiallyEnclosed
from hwtLib.logic.binToOneHot import BinToOneHot
from hwtLib.logic.bitonicSorter import BitonicSorter
from hwtLib.logic.cntrGray import GrayCntr
from hwtLib.logic.crc import Crc
from hwtLib.logic.crcComb import CrcComb
from hwtLib.mem.cam import Cam
from hwtLib.mem.cuckooHashTable import CuckooHashTable
from hwtLib.mem.lutRam import RAM64X1S
from hwtLib.mem.ram import RamMultiClock
from hwtLib.mem.ramXor import RamXorSingleClock
from hwtLib.peripheral.displays.segment7 import Segment7
from hwtLib.peripheral.i2c.masterBitCntrl import I2cMasterBitCtrl
from hwtLib.peripheral.spi.master import SpiMaster
from hwtLib.peripheral.usb.usb2.device_cdc_vcp import Usb2CdcVcp
from hwtLib.structManipulators.arrayBuff_writer import ArrayBuff_writer
from hwtLib.structManipulators.arrayItemGetter import ArrayItemGetter
from hwtLib.structManipulators.mmu_2pageLvl import MMU_2pageLvl


def convert(m: HwModule):
    synthesised(m, DEFAULT_PLATFORM)
    g = HwModuleToLNode(m, optimizations=DEFAULT_LAYOUT_OPTIMIZATIONS)
    idStore = ElkIdStore()
    data = g.toElkJson(idStore)
    # import json
    # import os
    # with open(os.path.join(os.path.dirname(__file__), "..", "..", "d3-hwschematic/examples/schemes/" + u._name + ".json"), "w") as fp:
    #     json.dump(data, fp, indent=2, sort_keys=True)
    # from pprint import pprint
    # pprint(data)
    return g, data


def assert_HwModule_lexical_eq(m0: HwModule, m1: HwModule):
    signals0 = sorted(m0._ctx.signals, key=RtlSignal_sort_key)
    signals1 = sorted(m0._ctx.signals, key=RtlSignal_sort_key)
    assert len(signals0) == len(signals1)
    for s0, s1 in zip(signals0, signals1):
        assert repr(s0) == repr(s1)

    statements0 = sorted(m0._ctx.statements, key=HdlStatement_sort_key)
    statements1 = sorted(m0._ctx.statements, key=HdlStatement_sort_key)
    assert len(statements0) == len(statements1)
    for s0, s1 in zip(statements0, statements1):
        assert repr(s0) == repr(s1)

    if m0._subHwModules is None:
        assert m1._subHwModules is None
    else:
        assert len(m0._subHwModules) == len(m1._subHwModules)
        for c_u0, c_u1 in zip(m0._subHwModules, m1._subHwModules):
            assert c_u0._name == c_u1._name
            assert_HwModule_lexical_eq(c_u0, c_u1)


class DirectFF_sig(HwModule):

    @override
    def hwDeclr(self):
        self.o = HwIOSignal()._m()
        self.clk = HwIOSignal()

    @override
    def hwImpl(self):
        r = self._sig("r", def_val=0)
        If(self.clk._onRisingEdge(),
           r(r)
        )
        self.o(r)


class Axi4StreamFullDuplex_wire(HwModule):

    @override
    def hwDeclr(self):
        self.dataIn = Axi4StreamFullDuplex()
        self.dataOut = Axi4StreamFullDuplex()._m()

    @override
    def hwImpl(self):
        self.dataOut(self.dataIn)


class Axi4StreamFullDuplex_wire_nested(HwModule):

    @override
    def hwDeclr(self):
        Axi4StreamFullDuplex_wire.hwDeclr(self)
        self.core = Axi4StreamFullDuplex_wire()

    @override
    def hwImpl(self):
        self.core.dataIn(self.dataIn)
        self.dataOut(self.core.dataOut)


class Conversibility_TC(unittest.TestCase):

    def test_ArrayBuff_writer(self):
        m = ArrayBuff_writer()
        convert(m)

    def test_HwIOArrayExample(self):
        m = HwIOArrayExample()
        convert(m)

    def test_ArrayItemGetter(self):
        m = ArrayItemGetter()
        convert(m)

    def test_Axi4streamToMem(self):
        m = Axi4streamToMem()
        convert(m)

    def test_Axi4LiteReg(self):
        m = AxiBuff(Axi4Lite)
        convert(m)

    def test_AxiTester(self):
        m = AxiTester()
        convert(m)

    def test_Axi_rDatapump(self):
        m = Axi_rDatapump()
        convert(m)

    def test_Axi_wDatapump(self):
        m = Axi_wDatapump()
        convert(m)

    def test_BinToOneHot(self):
        m = BinToOneHot()
        convert(m)

    def test_BitonicSorter(self):
        m = BitonicSorter()
        convert(m)

    def test_Cam(self):
        m = Cam()
        convert(m)

    def test_Cdc(self):
        m = Cdc()
        convert(m)

    def test_ConstDriverHwModule(self):
        m = ConstDriverHwModule()
        convert(m)

    def test_Crc(self):
        m = Crc()
        m.DATA_WIDTH = 8
        convert(m)

    def test_CrcComb(self):
        m = CrcComb()
        m.DATA_WIDTH = 8
        convert(m)

    def test_CuckooHashTable(self):
        m = CuckooHashTable()
        convert(m)

    def test_OooOpExampleCounterHashTable(self):
        m = OooOpExampleCounterHashTable()
        convert(m)

    def test_GrayCntr(self):
        m = GrayCntr()
        convert(m)

    def test_I2cMasterBitCtrl(self):
        m = I2cMasterBitCtrl()
        convert(m)

    def test_IndexingInernJoin(self):
        m = IndexingInernJoin()
        convert(m)

    def test_IndexingInernRangeSplit(self):
        m = IndexingInernRangeSplit()
        convert(m)

    def test_IndexingInternSplit(self):
        m = IndexingInternSplit()
        g, data = convert(m)
        join, split = g.children[2:]
        self.assertEqual(split.name, "SLICE")
        self.assertEqual(join.name, "CONCAT")
        self.assertIs(split.east[0].outgoingEdges[0].dsts[0], join.west[0])
        self.assertIs(split.east[1].outgoingEdges[0].dsts[0], join.west[1])

    def test_LatchReg(self):
        m = LatchReg()
        convert(m)

    def test_MMU_2pageLvl(self):
        m = MMU_2pageLvl()
        convert(m)

    def test_RAM64X1S(self):
        m = RAM64X1S()
        convert(m)

    def test_RamMultiClock(self):
        m = RamMultiClock()
        convert(m)

    def test_RamXorSingleClock(self):
        m = RamXorSingleClock()
        convert(m)

    def test_Segment7(self):
        m = Segment7()
        convert(m)

    def test_Showcase0(self):
        m = Showcase0()
        convert(m)

    def test_SpiMaster(self):
        m = SpiMaster()
        convert(m)

    def test_DirectFF_sig(self):
        m = DirectFF_sig()
        convert(m)

    def test_EthAddrUpdater(self):
        m = EthAddrUpdater()
        convert(m)

    def test_SimpleHwModuleAxi4Stream(self):
        m = SimpleHwModuleAxi4Stream()
        g = convert(m)
        root = g[0]
        # interface is merged to only single connection
        self.assertEqual(len(root.children), 2)
        self.assertEqual(len(root.children[0].east), 1)
        self.assertEqual(len(root.children[1].west), 1)

    def test_RStrictOrderInterconnect(self):
        m = RStrictOrderInterconnect()
        convert(m)

    def test_SimpleAsyncRam(self):
        m = SimpleAsyncRam()
        convert(m)

    def test_AxiLite_2Axi(self):
        m = AxiLite_to_Axi()
        convert(m)

    def test_Axi4StreamFullDuplex_wire(self):
        m = Axi4StreamFullDuplex_wire()
        convert(m)

    def test_Axi4StreamFullDuplex_wire_nested(self):
        m = Axi4StreamFullDuplex_wire_nested()
        convert(m)

    def test_AddrDataHs_to_Axi(self):
        m = example_AddrDataRdVld_to_Axi()
        convert(m)

    def test_MultiplierBooth(self):
        m = MultiplierBooth()
        convert(m)

    def test_example_AxiCacheTagArray(self):
        m = _example_AxiCacheTagArray()
        convert(m)

    def test_Usb2CdcVcp(self):
        m = Usb2CdcVcp()
        convert(m)

    def test_IfStatementPartiallyEnclosed(self):
        m = IfStatementPartiallyEnclosed()
        convert(m)

    def test_BlockStm_complete_override1(self):
        m = BlockStm_complete_override1()
        convert(m)

    def test_output_is_deterministc(self):
        components = [
            DirectFF_sig,
            Axi4StreamFullDuplex_wire,
            Axi4StreamFullDuplex_wire_nested,
            AxiLite_to_Axi,
            (AxiBuff, (Axi4Lite,)),
            Axi4streamToMem,
            AxiTester,
            RStrictOrderInterconnect,
            Axi_rDatapump,
            Axi_wDatapump,
            Cdc,
            EthAddrUpdater,
            HwIOArrayExample,
            SimpleAsyncRam,
            LatchReg,
            IndexingInernJoin,
            IndexingInernRangeSplit,
            IndexingInternSplit,
            Showcase0,
            SimpleHwModuleAxi4Stream,
            ConstDriverHwModule,
            BinToOneHot,
            BitonicSorter,
            GrayCntr,
            Crc,
            CrcComb,
            Cam,
            CuckooHashTable,
            RAM64X1S,
            RamMultiClock,
            RamXorSingleClock,
            Segment7,
            I2cMasterBitCtrl,
            SpiMaster,
            ArrayBuff_writer,
            ArrayItemGetter,
            MMU_2pageLvl,
            example_AddrDataRdVld_to_Axi,
            MultiplierBooth,
            _example_AxiCacheTagArray,
            Usb2CdcVcp,
            IfStatementPartiallyEnclosed,
            BlockStm_complete_override1,
        ]
        for comp in components:
            if isinstance(comp, tuple):
                comp, args = comp
                u0 = comp(*args)
                u1 = comp(*args)
            else:
                u0 = comp()
                u1 = comp()

            d0 = convert(u0)[1]
            d1 = convert(u1)[1]
            assert_HwModule_lexical_eq(u0, u1)
            self.assertDictEqual(d0, d1, comp.__name__)


if __name__ == "__main__":
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([Conversibility_TC("test_BlockStm_complete_override1")])
    suite = testLoader.loadTestsFromTestCase(Conversibility_TC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
