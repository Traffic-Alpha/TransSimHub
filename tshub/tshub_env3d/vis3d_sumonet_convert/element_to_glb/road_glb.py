'''
@Author: WANG Maonan
@Date: 2024-07-13 07:27:10
@Description: 生成 road glb 文件
@LastEditTime: 2024-07-13 07:51:47
'''
import math
import warnings
from typing import List, Tuple

import numpy as np
import trimesh.visual

from ...vis3d_utils.colors import Colors
from ..sumonet_convert_utils.glb_data import GLBData

# Suppress trimesh deprecation warning
with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message="Please use `coo_matrix` from the `scipy.sparse` namespace, the `scipy.sparse.coo` namespace is deprecated.",
        category=DeprecationWarning,
    )
    import trimesh  # only suppress the warnings caused by trimesh
    from trimesh.exchange import gltf

def make_road_glb(lines: List[List[Tuple[float, float]]]) -> GLBData:
    """Create a GLB file from a list of road lines (使用实线连接).
    """
    scene = trimesh.Scene()
    for line_pts in lines:
        # Create a list of vertices with a z-coordinate of 0.1
        vertices = np.array([(*pt, 0.1) for pt in line_pts])
        # Create a Path3D directly from the vertices
        path = trimesh.load_path(vertices)
        path.apply_transform(
            trimesh.transformations.rotation_matrix(math.pi / 2, [-1, 0, 0])
        )
        path.visual = trimesh.visual.ColorVisuals(
            vertex_colors=np.array([Colors.White.value for _ in range(len(vertices))])
        )
        scene.add_geometry(path)
    return GLBData(gltf.export_glb(scene))