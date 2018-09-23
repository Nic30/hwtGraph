import unittest

from hwt.synthesizer.dummyPlatform import DummyPlatform
from hwtGraph.elk.fromHwt.convertor import UnitToLNode
from hwtGraph.elk.fromHwt.extractSplits import extractSplits
from hwtGraph.elk.fromHwt.flattenTrees import flattenTrees
from hwtGraph.elk.fromHwt.mergeSplitsOnInterfaces import mergeSplitsOnInterfaces
from hwtGraph.elk.fromHwt.netlistPreprocessors import indexedAssignmentsToConcatenation,\
    unhideResultsOfIndexingAndConcatOnPublicSignals
from hwtLib.examples.hdlObjLists.listOfInterfaces0 import ListOfInterfacesSample0SliceOnly,\
    ListOfInterfacesSample0ConcatOnly
from hwtLib.examples.hdlObjLists.listOfInterfaces1 import ListOfInterfacesSample1
from hwtLib.examples.simple import SimpleUnit
from hwtLib.tests.synthesizer.interfaceLevel.subunitsSynthesisTC import synthesised
import json
from hwtGraph.elk.containers.idStore import ElkIdStore
from hwtGraph.elk.fromHwt.flattenPorts import flattenPorts


def_optimizations = [
    lambda root: flattenTrees(root, lambda node: node.name == "CONCAT"),
    extractSplits,
    mergeSplitsOnInterfaces,
    flattenPorts
]

plat = DummyPlatform()
plat.beforeHdlArchGeneration.extend([
    indexedAssignmentsToConcatenation,
    unhideResultsOfIndexingAndConcatOnPublicSignals,
])


# def unitToLayout(u):
#     synthesised(u, targetPlatform=plat)
#     root = UnitToLNode(u, optimizations=def_optimizations)
#     idStore = ElkIdStore()
#     with open("../../../d3-hwschematic/examples/schemes/" + u._name + ".json", "w") as f:
#         json.dump(root.toElkJson(idStore), f)
#     return root

# [TODO] interface arrays removed in hwt 2.5, but maybe this functionalyty is usefull
#class MergeSplitsOnInterfacesTC(unittest.TestCase):
#    def test_simple_nop(self):
#        u = SimpleUnit()
#        root = unitToLayout(u)
#
#        self.assertEqual(len(root.children), 2)
#        self.assertEqual(
#            root.children[0].east[0].outgoingEdges[0].dst,
#            root.children[1].west[0])
#
#    def test_triple_slice(self):
#        u = ListOfInterfacesSample0SliceOnly()
#        root = unitToLayout(u)
#
#        # there is clk and reset port
#        self.assertEqual(len(root.children),
#                         2 + 1 + 1 + 3)
#
#    def test_triple_concat(self):
#        u = ListOfInterfacesSample0ConcatOnly()
#        root = unitToLayout(u)
#
#        # there is clk and reset port
#        self.assertEqual(len(root.children),
#                         2 + 3 + 1 + 1)
#
#    def test_triple_slice_triple_concat(self):
#        u = ListOfInterfacesSample1()
#        root = unitToLayout(u)
#
#        # there is clk and reset port
#        self.assertEqual(len(root.children),
#                         2 + 1 + 3 + 1 + 1)
#
#
#if __name__ == "__main__":
#    suite = unittest.TestSuite()
#    suite.addTest(MergeSplitsOnInterfacesTC('test_triple_concat'))
#    # suite.addTest(unittest.makeSuite(MergeSplitsOnInterfacesTC))
#    runner = unittest.TextTestRunner(verbosity=3)
#    runner.run(suite)
#