from hwt.synthesizer.dummyPlatform import DummyPlatform
from hwtGraph.elk.fromHwt.extractSplits import extractSplits
from hwtGraph.elk.fromHwt.flattenPorts import flattenPorts
from hwtGraph.elk.fromHwt.flattenTrees import flattenTrees
from hwtGraph.elk.fromHwt.mergeSplitsOnInterfaces import mergeSplitsOnInterfaces
from hwtGraph.elk.fromHwt.netlistPreprocessors import indexedAssignmentsToConcatenation, \
    unhideResultsOfIndexingAndConcatOnPublicSignals
from hwtGraph.elk.fromHwt.reduceUselessAssignments import reduceUselessAssignments
from hwtGraph.elk.fromHwt.resolveSharedConnections import resolveSharedConnections
from hwtGraph.elk.fromHwt.sortStatementPorts import sortStatementPorts


DEFAULT_PLATFORM = DummyPlatform()
DEFAULT_PLATFORM.beforeHdlArchGeneration.extend([
    indexedAssignmentsToConcatenation,
    unhideResultsOfIndexingAndConcatOnPublicSignals,
])

DEFAULT_LAYOUT_OPTIMIZATIONS = [
    # optimizations
    reduceUselessAssignments,
    extractSplits,
    lambda root: flattenTrees(root, lambda node: node.cls == "Operator" and node.name == "CONCAT"),
    mergeSplitsOnInterfaces,
    resolveSharedConnections,
    # prettyfications
    sortStatementPorts,
    # required for to json conversion
    flattenPorts,
]
