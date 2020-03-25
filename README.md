# hwtGraph
[![Build Status](https://travis-ci.org/Nic30/hwtGraph.svg?branch=master)](https://travis-ci.org/Nic30/hwtGraph)
[![Coverage Status](https://coveralls.io/repos/github/Nic30/hwtGraph/badge.svg?branch=master)](https://coveralls.io/github/Nic30/hwtGraph?branch=master)
[![PyPI version](https://badge.fury.io/py/hwtGraph.svg)](http://badge.fury.io/py/hwtGraph) 
[![Documentation Status](https://readthedocs.org/projects/hwtGraph/badge/?version=latest)](http://hwtGraph.readthedocs.io/en/latest/?badge=latest) 
[![Python version](https://img.shields.io/pypi/pyversions/hwtGraph.svg)](https://img.shields.io/pypi/pyversions/hwtGraph.svg)

Library for conversion of HWT hardware representation to graph formats for visualization purposes.

Use `sudo pip3 install hwtGraph` or download this repo and run `python3 setup.py install` to install this library.

## Features

* Convert HWT hardware description to [ELK json](https://www.eclipse.org/elk/documentation/tooldevelopers/graphdatastructure/jsonformat.html) for visualization.

* suppor for additional graph transofrmations in all transformation phases (conversion is specified as sequence of transofrmations and user can modify it)


## Similar software

* [myhdl2dot](https://github.com/harboleas/myhdl2dot)