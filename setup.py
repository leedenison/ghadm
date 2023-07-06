#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='ghadm',
    version='0.1',
    packages=find_packages(),
    entry_points = {
        'console_scripts': ['ghadm=ghadm.command:main'],
    }
)
