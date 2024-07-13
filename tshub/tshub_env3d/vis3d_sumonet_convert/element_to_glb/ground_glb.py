'''
@Author: WANG Maonan
@Date: 2024-07-13 07:26:31
@Description: 生成 ground glb 文件
@LastEditTime: 2024-07-13 07:51:33
'''
import math
import warnings
import numpy as np
from typing import Any, Dict, List, Tuple
from shapely.geometry import Polygon, MultiPolygon

from . import OLD_TRIMESH
from ...vis3d_utils.colors import Colors
from ..sumonet_convert_utils.glb_data import GLBData
from ..sumonet_convert_utils.geometry import triangulate_polygon

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
    

def create_ground(bbox) -> MultiPolygon:
    """创建 bbox 的 Polygon 对象
    """
    bbox_polygon = Polygon([
        (bbox.min_pt.x, bbox.min_pt.y), 
        (bbox.min_pt.x, bbox.max_pt.y), 
        (bbox.max_pt.x, bbox.max_pt.y), 
        (bbox.max_pt.x, bbox.min_pt.y)]
    )

    return bbox_polygon

def make_ground_glb(bbox) -> GLBData:
    ground_poly = create_ground(bbox)
    meshes = _generate_meshes_from_ground_polygons([ground_poly, ])
    material = PBRMaterial(
        name="GroundDefault",
        baseColorFactor=Colors.GreenTransparent.value,
        metallicFactor=0.1, # 高金属感
        roughnessFactor=0.8, # 低粗糙度，更光滑
    )
    scene = trimesh.Scene()
    for mesh in meshes:
        mesh.visual.material = material
        if OLD_TRIMESH:
            scene.add_geometry(mesh, "ground")
        else:
            scene.add_geometry(mesh, "ground", geom_name="ground")
    return GLBData(gltf.export_glb(scene, include_normals=True))


def _generate_meshes_from_ground_polygons(
    polygons: List[Tuple[Polygon, Dict[str, Any]]],
) -> List[trimesh.Trimesh]:
    """Creates a mesh out of a list of polygons.
    """
    meshes = []

    for poly in polygons:
        vertices, faces = [], []
        point_dict = dict()
        current_point_index = 0

        for x, y in poly.exterior.coords:
            p = (x, y, 0)
            if p not in point_dict:
                vertices.append(p)
                point_dict[p] = current_point_index
                current_point_index += 1

        triangles = triangulate_polygon(poly)
        for triangle in triangles:
            face = np.array(
                [point_dict.get((x, y, 0), -1) for x, y in triangle.exterior.coords]
            )
            if -1 not in face:
                faces.append(face)

        if not vertices or not faces:
            continue

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

        # Normalize the normals
        mesh.vertex_normals = trimesh.util.unitize(mesh.vertex_normals)

        mesh.apply_transform(
            trimesh.transformations.rotation_matrix(math.pi / 2, [-1, 0, 0])
        )
        meshes.append(mesh)
    return meshes