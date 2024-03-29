import unittest

from hwt.code import If
from hwt.interfaces.std import Signal
from hwt.serializer.utils import RtlSignal_sort_key, \
    HdlStatement_sort_key
from hwt.synthesizer.unit import Unit
from hwt.synthesizer.utils import synthesised
from hwtGraph.elk.containers.idStore import ElkIdStore
from hwtGraph.elk.fromHwt.convertor import UnitToLNode
from hwtGraph.elk.fromHwt.defauts import DEFAULT_PLATFORM, \
    DEFAULT_LAYOUT_OPTIMIZATIONS
from hwtLib.amba.axi4Lite import Axi4Lite
from hwtLib.amba.axiLite_comp.to_axi import AxiLite_to_Axi
from hwtLib.amba.axi_comp.buff import AxiBuff
from hwtLib.amba.axi_comp.cache.tag_array import _example_AxiCacheTagArray
from hwtLib.examples.axi.oooOp.counterHashTable import OooOpExampleCounterHashTable
from hwtLib.amba.axi_comp.stream_to_mem import Axi4streamToMem
from hwtLib.amba.axi_comp.tester import AxiTester
from hwtLib.amba.axis_fullduplex import AxiStreamFullDuplex
from hwtLib.amba.datapump.interconnect.rStricOrder import RStrictOrderInterconnect
from hwtLib.amba.datapump.r import Axi_rDatapump
from hwtLib.amba.datapump.w import Axi_wDatapump
from hwtLib.clocking.cdc import Cdc
from hwtLib.common_nonstd_interfaces.addr_data_hs_to_Axi import example_AddrDataHs_to_Axi
from hwtLib.examples.arithmetic.multiplierBooth import MultiplierBooth
from hwtLib.examples.builders.ethAddrUpdater import EthAddrUpdater
from hwtLib.examples.hierarchy.unitWrapper_test import ArrayIntfExample
from hwtLib.examples.mem.ram import SimpleAsyncRam
from hwtLib.examples.mem.reg import LatchReg
from hwtLib.examples.operators.indexing import IndexingInernJoin, \
    IndexingInernRangeSplit, IndexingInternSplit
from hwtLib.examples.showcase0 import Showcase0
from hwtLib.examples.simpleAxiStream import SimpleUnitAxiStream
from hwtLib.examples.statements.constDriver import ConstDriverUnit
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
from hwtLib.examples.statements.codeBlockStm import BlockStm_complete_override1


def convert(u):
    synthesised(u, DEFAULT_PLATFORM)
    g = UnitToLNode(u, optimizations=DEFAULT_LAYOUT_OPTIMIZATIONS)
    idStore = ElkIdStore()
    data = g.toElkJson(idStore)
    # import json
    # import os
    # with open(os.path.join(os.path.dirname(__file__), "..", "..", "d3-hwschematic/examples/schemes/" + u._name + ".json"), "w") as fp:
    #     json.dump(data, fp, indent=2, sort_keys=True)
    # from pprint import pprint
    # pprint(data)
    return g, data


def assert_Unit_lexical_eq(u0: Unit, u1: Unit):
    signals0 = sorted(u0._ctx.signals, key=RtlSignal_sort_key)
    signals1 = sorted(u0._ctx.signals, key=RtlSignal_sort_key)
    assert len(signals0) == len(signals1)
    for s0, s1 in zip(signals0, signals1):
        assert repr(s0) == repr(s1)

    statements0 = sorted(u0._ctx.statements, key=HdlStatement_sort_key)
    statements1 = sorted(u0._ctx.statements, key=HdlStatement_sort_key)
    assert len(statements0) == len(statements1)
    for s0, s1 in zip(statements0, statements1):
        assert repr(s0) == repr(s1)

    if u0._units is None:
        assert u1._units is None
    else:
        assert len(u0._units) == len(u1._units)
        for c_u0, c_u1 in zip(u0._units, u1._units):
            assert c_u0._name == c_u1._name
            assert_Unit_lexical_eq(c_u0, c_u1)


class DirectFF_sig(Unit):

    def _declr(self):
        self.o = Signal()._m()
        self.clk = Signal()

    def _impl(self):
        r = self._sig("r", def_val=0)
        If(self.clk._onRisingEdge(),
           r(r)
        )
        self.o(r)


class AxiStreamFullDuplex_wire(Unit):

    def _declr(self):
        self.dataIn = AxiStreamFullDuplex()
        self.dataOut = AxiStreamFullDuplex()._m()

    def _impl(self):
        self.dataOut(self.dataIn)


class AxiStreamFullDuplex_wire_nested(Unit):

    def _declr(self):
        AxiStreamFullDuplex_wire._declr(self)
        self.core = AxiStreamFullDuplex_wire()

    def _impl(self):
        self.core.dataIn(self.dataIn)
        self.dataOut(self.core.dataOut)


class Conversibility_TC(unittest.TestCase):

    def test_ArrayBuff_writer(self):
        u = ArrayBuff_writer()
        convert(u)

    def test_ArrayIntfExample(self):
        u = ArrayIntfExample()
        convert(u)

    def test_ArrayItemGetter(self):
        u = ArrayItemGetter()
        convert(u)

    def test_Axi4streamToMem(self):
        u = Axi4streamToMem()
        convert(u)

    def test_Axi4LiteReg(self):
        u = AxiBuff(Axi4Lite)
        convert(u)

    def test_AxiTester(self):
        u = AxiTester()
        convert(u)

    def test_Axi_rDatapump(self):
        u = Axi_rDatapump()
        convert(u)

    def test_Axi_wDatapump(self):
        u = Axi_wDatapump()
        convert(u)

    def test_BinToOneHot(self):
        u = BinToOneHot()
        convert(u)

    def test_BitonicSorter(self):
        u = BitonicSorter()
        convert(u)

    def test_Cam(self):
        u = Cam()
        convert(u)

    def test_Cdc(self):
        u = Cdc()
        convert(u)

    def test_ConstDriverUnit(self):
        u = ConstDriverUnit()
        convert(u)

    def test_Crc(self):
        u = Crc()
        u.DATA_WIDTH = 8
        convert(u)

    def test_CrcComb(self):
        u = CrcComb()
        u.DATA_WIDTH = 8
        convert(u)

    def test_CuckooHashTable(self):
        u = CuckooHashTable()
        convert(u)

    def test_OooOpExampleCounterHashTable(self):
        u = OooOpExampleCounterHashTable()
        convert(u)

    def test_GrayCntr(self):
        u = GrayCntr()
        convert(u)

    def test_I2cMasterBitCtrl(self):
        u = I2cMasterBitCtrl()
        convert(u)

    def test_IndexingInernJoin(self):
        u = IndexingInernJoin()
        convert(u)

    def test_IndexingInernRangeSplit(self):
        u = IndexingInernRangeSplit()
        convert(u)

    def test_IndexingInternSplit(self):
        u = IndexingInternSplit()
        g, data = convert(u)
        join, split = g.children[2:]
        self.assertEqual(split.name, "SLICE")
        self.assertEqual(join.name, "CONCAT")
        self.assertIs(split.east[0].outgoingEdges[0].dsts[0], join.west[0])
        self.assertIs(split.east[1].outgoingEdges[0].dsts[0], join.west[1])

    def test_LatchReg(self):
        u = LatchReg()
        convert(u)

    def test_MMU_2pageLvl(self):
        u = MMU_2pageLvl()
        convert(u)

    def test_RAM64X1S(self):
        u = RAM64X1S()
        convert(u)

    def test_RamMultiClock(self):
        u = RamMultiClock()
        convert(u)

    def test_RamXorSingleClock(self):
        u = RamXorSingleClock()
        convert(u)

    def test_Segment7(self):
        u = Segment7()
        convert(u)

    def test_Showcase0(self):
        u = Showcase0()
        convert(u)

    def test_SpiMaster(self):
        u = SpiMaster()
        convert(u)

    def test_DirectFF_sig(self):
        u = DirectFF_sig()
        convert(u)

    def test_EthAddrUpdater(self):
        u = EthAddrUpdater()
        convert(u)

    def test_SimpleUnitAxiStream(self):
        u = SimpleUnitAxiStream()
        g = convert(u)
        root = g[0]
        # interface is merged to only single connection
        self.assertEqual(len(root.children), 2)
        self.assertEqual(len(root.children[0].east), 1)
        self.assertEqual(len(root.children[1].west), 1)

    def test_RStrictOrderInterconnect(self):
        u = RStrictOrderInterconnect()
        convert(u)

    def test_SimpleAsyncRam(self):
        u = SimpleAsyncRam()
        convert(u)

    def test_AxiLite_2Axi(self):
        u = AxiLite_to_Axi()
        convert(u)

    def test_AxiStreamFullDuplex_wire(self):
        u = AxiStreamFullDuplex_wire()
        convert(u)

    def test_AxiStreamFullDuplex_wire_nested(self):
        u = AxiStreamFullDuplex_wire_nested()
        convert(u)

    def test_AddrDataHs_to_Axi(self):
        u = example_AddrDataHs_to_Axi()
        convert(u)

    def test_MultiplierBooth(self):
        u = MultiplierBooth()
        convert(u)

    def test_example_AxiCacheTagArray(self):
        u = _example_AxiCacheTagArray()
        convert(u)

    def test_Usb2CdcVcp(self):
        u = Usb2CdcVcp()
        convert(u)

    def test_IfStatementPartiallyEnclosed(self):
        u = IfStatementPartiallyEnclosed()
        convert(u)

    def test_BlockStm_complete_override1(self):
        u = BlockStm_complete_override1()
        convert(u)

    def test_output_is_deterministc(self):
        components = [
            DirectFF_sig,
            AxiStreamFullDuplex_wire,
            AxiStreamFullDuplex_wire_nested,
            AxiLite_to_Axi,
            (AxiBuff, (Axi4Lite,)),
            Axi4streamToMem,
            AxiTester,
            RStrictOrderInterconnect,
            Axi_rDatapump,
            Axi_wDatapump,
            Cdc,
            EthAddrUpdater,
            ArrayIntfExample,
            SimpleAsyncRam,
            LatchReg,
            IndexingInernJoin,
            IndexingInernRangeSplit,
            IndexingInternSplit,
            Showcase0,
            SimpleUnitAxiStream,
            ConstDriverUnit,
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
            example_AddrDataHs_to_Axi,
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
            assert_Unit_lexical_eq(u0, u1)
            self.assertDictEqual(d0, d1, comp.__name__)


if __name__ == "__main__":
    testLoader = unittest.TestLoader()
    # suite = unittest.TestSuite([Conversibility_TC("test_BlockStm_complete_override1")])
    suite = testLoader.loadTestsFromTestCase(Conversibility_TC)
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
