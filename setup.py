'''
@Author: WANG Maonan
@Date: 2023-08-23 11:03:44
@Description: TransSimHub Install
@LastEditTime: 2023-08-23 11:34:39
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from setuptools import setup, find_packages
import os


here = os.path.abspath(os.path.dirname(__file__))


setup(
    name='tshub',
    version=0.1,
    description='TransSimHub is a lightweight Python library for simulating and controlling transportation systems.',
    author='Traffic-Alpha',
    license='Apache License, Version 2.0',
    keywords='transportation systems',
    packages=find_packages(),
    install_requires=[i.strip() for i in open(os.path.join(os.path.dirname(__file__), 'requirements.txt')).readlines() if i.strip()],
    include_package_data=True,
)