import unittest

from hwtGraph.elk.containers.idStore import ElkIdStore
from hwtGraph.elk.fromHwt.convertor import UnitToLNode
from hwtGraph.elk.fromHwt.defauts import DEFAULT_PLATFORM, DEFAULT_LAYOUT_OPTIMIZATIONS
from hwtLib.amba.axi4_rDatapump import Axi_rDatapump
from hwtLib.amba.axi4_streamToMem import Axi4streamToMem
from hwtLib.amba.axiLite_comp.reg import AxiLiteReg
from hwtLib.amba.axi_comp.tester import AxiTester
from hwtLib.samples.ipCoreCompatibleWrap import ArrayIntfExample
from hwtLib.structManipulators.arrayBuff_writer import ArrayBuff_writer
from hwtLib.structManipulators.arrayItemGetter import ArrayItemGetter
from hwtLib.tests.synthesizer.interfaceLevel.subunitsSynthesisTC import synthesised
from hwtLib.amba.axi4_wDatapump import Axi_wDatapump
from hwtLib.mem.cam import Cam
from hwtLib.mem.clkSynchronizer import ClkSynchronizer
from hwtLib.clocking.clkDivider import ClkDiv3
from hwtLib.samples.statements.constDriver import ConstDriverUnit
from hwtLib.logic.crc import Crc
from hwtLib.logic.crcComb import CrcComb
from hwtLib.logic.binToOneHot import BinToOneHot
from hwtLib.mem.cuckooHashTable import CuckooHashTable
from hwtLib.logic.cntrGray import GrayCntr
from hwtLib.i2c.masterBitCntrl import I2cMasterBitCtrl
from hwtLib.samples.operators.indexing import IndexingInernJoin,\
    IndexingInernRangeSplit, IndexingInernSplit
from hwtLib.samples.mem.reg import Latch
from hwtLib.structManipulators.mmu_2pageLvl import MMU_2pageLvl
from hwtLib.logic.bitonicSorter import BitonicSorter
from hwtLib.mem.lutRam import RAM64X1S
from hwtLib.mem.ram import Ram_dp
from hwtLib.logic.segment7 import Segment7
from hwtLib.samples.showcase0 import Showcase0


def convert(u):
    synthesised(u, DEFAULT_PLATFORM)
    g = UnitToLNode(u, optimizations=DEFAULT_LAYOUT_OPTIMIZATIONS)
    idStore = ElkIdStore()
    data = g.toElkJson(idStore)
    return g, data


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


if __name__ == "__main__":
    suite = unittest.TestSuite()
    # suite.addTest(Conversibility_TC('test_ArrayBuff_writer'))
    suite.addTest(unittest.makeSuite(Conversibility_TC))
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
