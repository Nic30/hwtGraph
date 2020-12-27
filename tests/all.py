#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from unittest import TestLoader, TextTestRunner, TestSuite

from tests.conversibility_test import Conversibility_TC


def testSuiteFromTCs(*tcs):
    loader = TestLoader()
    loadedTcs = [loader.loadTestsFromTestCase(tc) for tc in tcs]
    suite = TestSuite(loadedTcs)
    return suite


suite = testSuiteFromTCs(
    Conversibility_TC,
)

if __name__ == '__main__':
    if "--with-xunit" in sys.argv:
        # junit xml output for CI
        import xmlrunner
        runner = xmlrunner.XMLTestRunner(output='test-reports')
    else:
        runner = TextTestRunner(verbosity=2)

    try:
        from concurrencytest import ConcurrentTestSuite, fork_for_tests
        useParallerlTest = True
    except ImportError:
        # concurrencytest is not installed, use regular test runner
        useParallerlTest = False

    if useParallerlTest:
        # Run same tests across 4 processes
        concurrent_suite = ConcurrentTestSuite(suite, fork_for_tests())
        runner.run(concurrent_suite)
    else:
        sys.exit(not runner.run(suite).wasSuccessful())
