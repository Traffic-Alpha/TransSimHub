'''
@Author: WANG Maonan
@Date: 2024-07-03 16:13:17
@Description: 路网转换的小工具
Reference, https://github.com/huawei-noah/SMARTS/blob/master/smarts/core/utils/geometry.py
@LastEditTime: 2024-07-13 07:21:38
'''
from shapely.ops import triangulate
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.geometry.base import CAP_STYLE, JOIN_STYLE

def buffered_shape(shape, width: float = 1.0) -> Polygon:
    """收一个形状（shape）和一个宽度（width）作为参数，
    然后生成一个在原始形状周围添加了宽度为 width 的缓冲区的新形状
    """
    ls = LineString(shape).buffer(
        width / 2,
        1,
        cap_style=CAP_STYLE.flat,
        join_style=JOIN_STYLE.round,
        mitre_limit=5.0,
    )
    if isinstance(ls, MultiPolygon):
        # Sometimes it oddly outputs a MultiPolygon and then we need to turn it into a convex hull
        ls = ls.convex_hull # 将其转换为凸包（convex hull）
    elif not isinstance(ls, Polygon):
        raise RuntimeError("Shapely `object.buffer` behavior may have changed.")
    return ls


def triangulate_polygon(polygon: Polygon):
    """Attempts to convert a polygon into triangles.
    """
    # XXX: shapely.ops.triangulate current creates a convex fill of triangles.
    return [
        tri_face
        for tri_face in triangulate(polygon)
        if tri_face.centroid.within(polygon)
    ]