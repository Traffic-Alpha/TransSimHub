'''
@Author: WANG Maonan
@Date: 2024-07-13 07:27:16
@Description: 生成 lane glb 文件
@LastEditTime: 2024-07-13 07:51:39
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
    from trimesh.visual.material import PBRMaterial


def make_line_glb(lines: List[List[Tuple[float, float]]], is_point=False) -> GLBData:
    """Create a GLB file from a list of lane lines (lane 使用虚线连接).
    """
    scene = trimesh.Scene()
    if is_point:
        material = PBRMaterial(
            name="LineDefault",
            baseColorFactor=Colors.White.value, # white color
            metallicFactor=0.8, # 金属感
            roughnessFactor=0.8, # 粗糙度        
        )
        for line_pts in lines:
            vertices = [(*pt, 0.1) for pt in line_pts]
            point_cloud = trimesh.PointCloud(
                vertices=vertices,
            )
            point_cloud.visual.material = material
            point_cloud.apply_transform(
                trimesh.transformations.rotation_matrix(math.pi / 2, [-1, 0, 0])
            )
            scene.add_geometry(point_cloud)
    else:
        for line_pts in lines:
            # Iterate over pairs of points
            for i in range(0, len(line_pts), 2):
                if i+1 < len(line_pts):  # Ensure there is a pair
                    # Create a list of vertices for the pair with a z-coordinate of 0.1
                    vertices = np.array([(*line_pts[i], 0.1), (*line_pts[i+1], 0.1)])
                    # Create a Path3D directly from the vertices
                    path = trimesh.load_path(vertices)
                    path.apply_transform(
                        trimesh.transformations.rotation_matrix(math.pi / 2, [-1, 0, 0])
                    )
                    # Set the color for the path
                    path.visual = trimesh.visual.ColorVisuals(
                        vertex_colors=np.array([Colors.White.value, Colors.White.value])
                    )
                    scene.add_geometry(path)
    return GLBData(gltf.export_glb(scene))
