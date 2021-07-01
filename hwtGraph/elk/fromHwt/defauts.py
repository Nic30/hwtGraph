from hwt.synthesizer.dummyPlatform import DummyPlatform
from hwtGraph.elk.fromHwt.extractSplits import extractSplits
from hwtGraph.elk.fromHwt.flattenTrees import flattenTrees
from hwtGraph.elk.fromHwt.mergeSplitsOnInterfaces import mergeSplitsOnInterfaces
from hwtGraph.elk.fromHwt.netlistPreprocessors import unhideResultsOfIndexingAndConcatOnPublicSignals
from hwtGraph.elk.fromHwt.reduceUselessAssignments import reduceUselessAssignments
from hwtGraph.elk.fromHwt.resolveSharedConnections import resolveSharedConnections
from hwtGraph.elk.fromHwt.sortStatementPorts import sortStatementPorts
from hwtGraph.elk.fromHwt.propagatePresets import propagatePresets


DEFAULT_PLATFORM = DummyPlatform()
DEFAULT_PLATFORM.beforeHdlArchGeneration.extend([
    unhideResultsOfIndexingAndConcatOnPublicSignals,
    propagatePresets,
])

DEFAULT_LAYOUT_OPTIMIZATIONS = [
    # optimizations
    reduceUselessAssignments,
    extractSplits,
    lambda root: flattenTrees(root, lambda node: node.cls == "Operator" and node.name == "CONCAT", True),
    mergeSplitsOnInterfaces,
    resolveSharedConnections,
    # prettyfications
    sortStatementPorts,
]
