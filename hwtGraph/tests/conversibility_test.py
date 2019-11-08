import unittest

from hwt.code import If
from hwt.interfaces.std import Signal
from hwt.synthesizer.unit import Unit
from hwtGraph.elk.containers.idStore import ElkIdStore
from hwtGraph.elk.fromHwt.convertor import UnitToLNode
from hwtGraph.elk.fromHwt.defauts import DEFAULT_PLATFORM, \
    DEFAULT_LAYOUT_OPTIMIZATIONS
from hwtLib.amba.axiLite_comp.reg import AxiLiteReg
from hwtLib.amba.axi_comp.axi4_rDatapump import Axi_rDatapump
from hwtLib.amba.axi_comp.axi4_streamToMem import Axi4streamToMem
from hwtLib.amba.axi_comp.axi4_wDatapump import Axi_wDatapump
from hwtLib.amba.axi_comp.tester import AxiTester
from hwtLib.amba.interconnect.rStricOrder import RStrictOrderInterconnect
from hwtLib.clocking.clkDivider import ClkDiv3
from hwtLib.clocking.clkSynchronizer import ClkSynchronizer
from hwtLib.examples.builders.ethAddrUpdater import EthAddrUpdater
from hwtLib.examples.hierarchy.unitWrapper_test import ArrayIntfExample
from hwtLib.examples.mem.ram import SimpleAsyncRam
from hwtLib.examples.mem.reg import Latch
from hwtLib.examples.operators.indexing import IndexingInernJoin, \
    IndexingInernRangeSplit, IndexingInernSplit
from hwtLib.examples.showcase0 import Showcase0
from hwtLib.examples.simpleAxiStream import SimpleUnitAxiStream
from hwtLib.examples.statements.constDriver import ConstDriverUnit
from hwtLib.logic.binToOneHot import BinToOneHot
from hwtLib.logic.bitonicSorter import BitonicSorter
from hwtLib.logic.cntrGray import GrayCntr
from hwtLib.logic.crc import Crc
from hwtLib.logic.crcComb import CrcComb
from hwtLib.mem.cam import Cam
from hwtLib.mem.cuckooHashTable import CuckooHashTable
from hwtLib.mem.lutRam import RAM64X1S
from hwtLib.mem.ram import Ram_dp
from hwtLib.peripheral.i2c.masterBitCntrl import I2cMasterBitCtrl
from hwtLib.peripheral.segment7 import Segment7
from hwtLib.peripheral.spi.master import SpiMaster
from hwtLib.structManipulators.arrayBuff_writer import ArrayBuff_writer
from hwtLib.structManipulators.arrayItemGetter import ArrayItemGetter
from hwtLib.structManipulators.mmu_2pageLvl import MMU_2pageLvl
from hwtLib.tests.synthesizer.interfaceLevel.subunitsSynthesisTC import synthesised


def convert(u):
    synthesised(u, DEFAULT_PLATFORM)
    g = UnitToLNode(u, optimizations=DEFAULT_LAYOUT_OPTIMIZATIONS)
    idStore = ElkIdStore()
    data = g.toElkJson(idStore)
    # import json
    # from pprint import pprint
    # with open("../../../d3-hwschematic/examples/schemes/" + u._name + ".json", "w") as fp:
    #     json.dump(data, fp)
    # pprint(data)
    return g, data


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

    def test_AxiLiteReg(self):
        u = AxiLiteReg()
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

    def test_ClkSynchronizer(self):
        u = ClkSynchronizer()
        convert(u)

    def test_ClkDiv3(self):
        u = ClkDiv3()
        convert(u)

    def test_ConstDriverUnit(self):
        u = ConstDriverUnit()
        convert(u)

    def test_Crc(self):
        u = Crc()
        convert(u)

    def test_CrcComb(self):
        u = CrcComb()
        convert(u)

    def test_CuckooHashTable(self):
        u = CuckooHashTable()
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

    def test_IndexingInernSplit(self):
        u = IndexingInernSplit()
        convert(u)

    def test_Latch(self):
        u = Latch()
        convert(u)

    def test_MMU_2pageLvl(self):
        u = MMU_2pageLvl()
        convert(u)

    def test_RAM64X1S(self):
        u = RAM64X1S()
        convert(u)

    def test_Ram_dp(self):
        u = Ram_dp()
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


if __name__ == "__main__":
    suite = unittest.TestSuite()
    # suite.addTest(Conversibility_TC('test_EthAddrUpdater'))
    suite.addTest(unittest.makeSuite(Conversibility_TC))
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
