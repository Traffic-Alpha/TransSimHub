'''
@Author: WANG Maonan
@Date: 2024-07-13 07:26:57
@Description: 生成 map glb 文件
@LastEditTime: 2024-07-13 07:51:43
'''
import math
import warnings
from typing import Any, Dict, List, Tuple

import numpy as np
import trimesh.visual
from shapely.geometry import Polygon

from . import OLD_TRIMESH
from ...vis3d_utils.colors import Colors
from ...vis3d_utils.coordinates import BoundingBox
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


def make_map_glb(
    polygons: List[Tuple[Polygon, Dict[str, Any]]],
    bbox: BoundingBox,
    lane_dividers,
    edge_dividers,
) -> GLBData:
    """Create a GLB file from a list of road polygons.
    """
    # Attach additional information for rendering as metadata in the map glb
    metadata = {
        "bounding_box": (
            bbox.min_pt.x,
            bbox.min_pt.y,
            bbox.max_pt.x,
            bbox.max_pt.y,
        ),
        "lane_dividers": lane_dividers,
        "edge_dividers": edge_dividers,
    }
    scene = trimesh.Scene(metadata=metadata)

    meshes = _generate_meshes_from_polygons(polygons)
    material = PBRMaterial(
        name="RoadDefault",
        baseColorFactor=Colors.DarkGrey.value,
        metallicFactor=0.8, # 高金属感
        roughnessFactor=0.8, # 低粗糙度，更光滑
    )

    for mesh in meshes:
        mesh.visual.material = material
        road_id = mesh.metadata["road_id"]
        lane_id = mesh.metadata.get("lane_id")
        name = str(road_id)
        if lane_id is not None:
            name += f"-{lane_id}"
        if OLD_TRIMESH:
            scene.add_geometry(mesh, name, extras=mesh.metadata)
        else:
            scene.add_geometry(mesh, name, geom_name=name, metadata=mesh.metadata)
    return GLBData(gltf.export_glb(scene, include_normals=True))

def _generate_meshes_from_polygons(
    polygons: List[Tuple[Polygon, Dict[str, Any]]],
) -> List[trimesh.Trimesh]:
    """Creates a mesh out of a list of polygons.
    """
    meshes = []

    # Trimesh's API require a list of vertices and a list of faces, where each
    # face contains three indexes into the vertices list. Ideally, the vertices
    # are all unique and the faces list references the same indexes as needed.
    for poly, metadata in polygons:
        vertices, faces = [], []
        point_dict = dict()
        current_point_index = 0

        # Collect all the points on the shape to reduce checks by 3 times
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
            # Add face if not invalid
            if -1 not in face:
                faces.append(face)

        if not vertices or not faces:
            continue

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, metadata=metadata)

        # Trimesh doesn't support a coordinate-system="z-up" configuration, so we
        # have to apply the transformation manually.
        mesh.apply_transform(
            trimesh.transformations.rotation_matrix(math.pi / 2, [-1, 0, 0])
        )
        meshes.append(mesh)
    return meshes