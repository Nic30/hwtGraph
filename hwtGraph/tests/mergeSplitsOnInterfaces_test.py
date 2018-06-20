import unittest

from hwt.synthesizer.dummyPlatform import DummyPlatform
from hwtGraph.elk.fromHwt.convertor import UnitToLNode
from hwtGraph.elk.fromHwt.extractSplits import extractSplits
from hwtGraph.elk.fromHwt.flattenTrees import flattenTrees
from hwtGraph.elk.fromHwt.mergeSplitsOnInterfaces import mergeSplitsOnInterfaces
from hwtGraph.elk.fromHwt.netlistPreprocessors import indexedAssignmentsToConcatenation,\
    unhideResultsOfIndexingAndConcatOnPublicSignals
from hwtLib.samples.intfArray.interfaceArray0 import InterfaceArraySample0SliceOnly,\
    InterfaceArraySample0ConcatOnly
from hwtLib.samples.intfArray.interfaceArray1 import InterfaceArraySample1
from hwtLib.samples.simple import SimpleUnit
from hwtLib.tests.synthesizer.interfaceLevel.subunitsSynthesisTC import synthesised


def_optimizations = [
    lambda root: flattenTrees(root, lambda node: node.name == "CONCAT"),
    extractSplits,
    mergeSplitsOnInterfaces
]

plat = DummyPlatform()
plat.beforeHdlArchGeneration.extend([
    indexedAssignmentsToConcatenation,
    unhideResultsOfIndexingAndConcatOnPublicSignals,
])


def unitToLayout(u):
    synthesised(u, targetPlatform=plat)
    root = UnitToLNode(u, optimizations=def_optimizations)
    return root


class MergeSplitsOnInterfacesTC(unittest.TestCase):
    def test_simple_nop(self):
        u = SimpleUnit()
        root = unitToLayout(u)

        self.assertEqual(len(root.children), 2)
        self.assertEqual(
            root.children[0].east[0].outgoingEdges[0].dst,
            root.children[1].west[0])

    def test_triple_slice(self):
        u = InterfaceArraySample0SliceOnly()
        root = unitToLayout(u)

        # there is clk and reset port
        self.assertEqual(len(root.children),
                         2 + 1 + 1 + 3)

    def test_triple_concat(self):
        u = InterfaceArraySample0ConcatOnly()
        root = unitToLayout(u)

        # there is clk and reset port
        self.assertEqual(len(root.children),
                         2 + 3 + 1 + 1)

    def test_triple_slice_triple_concat(self):
        u = InterfaceArraySample1()
        root = unitToLayout(u)

        # there is clk and reset port
        self.assertEqual(len(root.children),
                         2 + 1 + 3 + 1 + 1)


if __name__ == "__main__":
    suite = unittest.TestSuite()
    # suite.addTest(MergeSplitsOnInterfacesTC('test_triple_concat'))
    suite.addTest(unittest.makeSuite(MergeSplitsOnInterfacesTC))
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
