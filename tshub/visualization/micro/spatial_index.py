'''
@Author: WANG Maonan
@Date: 2026-08-12 10:00:00
@Description: 多边形的均匀网格空间索引, 用于局部可视化只取视野内的路网元素.

为什么需要它: 局部视角每帧只画很小一块, 但如果不做空间查询, 每帧仍要遍历整个路网
(香港九龙有 2927 条车道、3 万多条线段), 于是渲染耗时与路网规模成正比 —— 明明只看
100 米见方的一块。建一次网格索引之后, 每帧的代价只与「视野内的元素数」有关,
与路网规模无关。

只用标准库: rtree/shapely 都在 3D extra 里, 可视化不应该被它们绑定。
@LastEditTime: 2026-08-12 10:00:00
'''
from typing import Any, Dict, Iterable, List, Tuple


class PolygonGridIndex:
    """把多边形按包围盒登记到均匀网格, 支持矩形范围查询.

    多边形跨多个格子时会在每个覆盖到的格子里都登记一次, 查询时用集合去重。
    """

    def __init__(self, polygons: Dict[str, Any], cell_size: float = 100.0) -> None:
        """
        Args:
            polygons: {id: {'shape': [(x, y), ...], ...}}, 与 map builder 的输出一致.
            cell_size (float, optional): 网格边长 (m)。取值接近典型视野尺寸即可,
                过小则索引本身变大, 过大则查询会带回很多无用元素。Defaults to 100.0.
        """
        self.cell_size = float(cell_size)
        self._cells: Dict[Tuple[int, int], List[str]] = {}
        self._polygons = polygons
        self._bounds = None  # 整个路网的包围盒, 顺便算出来

        x_min = y_min = float('inf')
        x_max = y_max = float('-inf')
        for polygon_id, polygon_info in polygons.items():
            shape = polygon_info.get('shape')
            if not shape:
                continue
            xs = [point[0] for point in shape]
            ys = [point[1] for point in shape]
            px_min, px_max = min(xs), max(xs)
            py_min, py_max = min(ys), max(ys)
            x_min, x_max = min(x_min, px_min), max(x_max, px_max)
            y_min, y_max = min(y_min, py_min), max(y_max, py_max)
            for cell in self._cells_covering(px_min, py_min, px_max, py_max):
                self._cells.setdefault(cell, []).append(polygon_id)

        if x_min <= x_max:
            self._bounds = (x_min, y_min, x_max, y_max)

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """整个路网的包围盒 (x_min, y_min, x_max, y_max)"""
        return self._bounds

    def _cells_covering(self, x_min: float, y_min: float,
                        x_max: float, y_max: float) -> Iterable[Tuple[int, int]]:
        cell = self.cell_size
        for ix in range(int(x_min // cell), int(x_max // cell) + 1):
            for iy in range(int(y_min // cell), int(y_max // cell) + 1):
                yield (ix, iy)

    def query(self, x_min: float, y_min: float,
              x_max: float, y_max: float) -> Dict[str, Any]:
        """返回包围盒与查询矩形相交的多边形 {id: info}"""
        hit_ids = set()
        for cell in self._cells_covering(x_min, y_min, x_max, y_max):
            hit_ids.update(self._cells.get(cell, ()))
        return {polygon_id: self._polygons[polygon_id] for polygon_id in hit_ids}
