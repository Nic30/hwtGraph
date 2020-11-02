#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from os import path
from setuptools import setup, find_packages


this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='hwtGraph',
      version='2.0',
      description='Library for conversion of HWT hardware representation '
                  'to graph formats for visualization purposes',
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='https://github.com/Nic30/hwtGraph',
      author='Michal Orsak',
      author_email='michal.o.socials@gmail.com',
      install_requires=[
          'hwt>=3.7',
      ],
      tests_require=[
          'hwtLib'
      ],
      classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
        "Topic :: System :: Hardware",
        "Topic :: Utilities",
      ],
      license='MIT',
      packages=find_packages(),
      zip_safe=False)
