#!/usr/bin/env python
# -*- coding: utf8 -*-
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='PyNBT',
    version='1.3.3',
    description='Tiny, liberally-licensed NBT library (Minecraft).',
    author='Tyler Kennedy',
    author_email='tk@tkte.ch',
    url='https://github.com/TkTech/PyNBT',
    packages=[
        'pynbt'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License'
    ]
)
