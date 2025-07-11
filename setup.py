'''
@Author: WANG Maonan
@Date: 2023-08-23 11:03:44
@Description: TransSimHub Install
LastEditTime: 2025-05-28 13:13:46
'''
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from setuptools import setup, find_packages
import os

here = os.path.abspath(os.path.dirname(__file__))

extras_require={
    'doc':[
        "sphinx",
        "sphinx_rtd_theme",
    ], # 文档生成
    'scene':[
        'matplotlib',
        'opencv-python'
    ], # 场景生成
    'rl':[
        'stable-baselines3',
        'tensorboard',
        'torchrl',
        'pettingzoo',
        'supersuit',
        'tqdm'
    ],
    '3D': [
        'rtree',
        'shapely',
        'trimesh',
        'Panda3D',
        'panda3d-gltf',
        'panda3d-simplepbr',
        'panda3d-blend2bam',         
    ]
}

# 使用列表推导式将所有的依赖项合并到一个列表中
all_deps = [item for sublist in extras_require.values() for item in sublist]

# 将合并后的列表添加到 'all' 键中
extras_require['all'] = all_deps

setup(
    name='tshub',
    version=1.3,
    description='TransSimHub is a lightweight Python library for simulating and controlling transportation systems.',
    author='Traffic-Alpha',
    license='Apache License, Version 2.0',
    keywords=['V2X', 'transportation systems', 'reinforcement learning'],
    python_requires='>=3.9',
    packages=find_packages(),
    install_requires=[
        i.strip()
        for i in open(os.path.join(os.path.dirname(__file__), 'requirements.txt')).readlines() 
        if i.strip()
    ],
    extras_require=extras_require,
    include_package_data=True,
)