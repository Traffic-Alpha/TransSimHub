'''
@Author: WANG Maonan
@Date: 2023-08-23 11:03:44
@Description: TransSimHub Install
@LastEditTime: 2023-09-01 15:59:24
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from setuptools import setup, find_packages
import os

here = os.path.abspath(os.path.dirname(__file__))


setup(
    name='tshub',
    version=0.6,
    description='TransSimHub is a lightweight Python library for simulating and controlling transportation systems.',
    author='Traffic-Alpha',
    license='Apache License, Version 2.0',
    keywords=['V2X', 'transportation systems', 'reinforcement learning'],
    python_requires='>=3.7',
    packages=find_packages(),
    install_requires=[
        i.strip() 
        for i in open(os.path.join(os.path.dirname(__file__), 'requirements.txt')).readlines() 
        if i.strip()
    ],
    extras_require={
        'doc':[
            "sphinx",
            "sphinx_rtd_theme",
        ], # 文档生成
        'scene':[
            'matplotlib',
            'scipy'
        ] # 场景生成
    },
    include_package_data=True,
)