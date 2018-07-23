#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from setuptools import setup, find_packages


setup(name='hwtGraph',
      version='0.0.1',
      description='Library for conversion of HWT hardware representation '
                  'to graph formats for visualization purposes',
      url='https://github.com/Nic30/hwtGraph',
      author='Michal Orsak',
      author_email='michal.o.socials@gmail.com',
      install_requires=[
          'hwt',
      ],
      tests_require=[
          'hwtLib'
      ],
      license='MIT',
      packages=find_packages(),
      zip_safe=False)
