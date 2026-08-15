'''
@Author: WANG Maonan
@Date: 2023-11-12 16:22:16
@Description: 局部视角的路网可视化 (无头、不需要 GPU, 可直接作为 RL 的图像观测)

只支持局部视角 (跟随某辆车或某个路口), 不再提供全局视角 —— 全网态势请用
tshub.visualization.meso (中观大屏), 它在大路网上快得多也清楚得多。

针对大场景做了三件事:
1. **空间索引**: 每帧只取视野内的路网元素, 代价与路网规模无关 (见 spatial_index.py);
2. **预取 + 失效**: 缓存一块比视野大一圈的区域, 视野没移出去就直接复用。
   路口是固定的, 因此整个 episode 只需要查询/构建一次路网图层;
   跟车时窗口逐帧移动, 也只需要隔若干帧重建一次;
3. **持久 figure**: 复用同一个 figure 并只重画车辆, 既避免了 figure 泄漏,
   也省掉每帧创建/销毁 figure 的开销。
@LastEditTime: 2026-08-12 10:00:00
'''
from typing import Any, Dict, Optional, Tuple

import matplotlib.pyplot as plt

from .spatial_index import PolygonGridIndex
from .map_features import make_map_collections
from .vehicles import plot_vehicle


class LocalMapRenderer:
    """局部视角渲染器. 路网索引与 figure 都是长期持有的, 每帧只更新车辆."""

    def __init__(self,
                 map_lanes: Dict[str, Any],
                 map_nodes: Dict[str, Any],
                 figsize: Tuple[float, float] = (6, 6),
                 cell_size: float = 100.0,
                 prefetch_ratio: float = 0.5) -> None:
        """
        Args:
            map_lanes: 车道的静态几何 (obs['lane_shape']).
            map_nodes: 路口的静态几何 (obs['node']).
            figsize: figure 尺寸 (英寸). Defaults to (6, 6).
            cell_size: 空间索引的网格边长 (m). Defaults to 100.0.
            prefetch_ratio: 每次多取视野边长的百分之多少作为缓冲区。
                取 0.5 表示上下左右各多取半个视野, 视野在这块区域里移动时不必重新查询。
                Defaults to 0.5.
        """
        self._lane_index = PolygonGridIndex(map_lanes, cell_size)
        self._node_index = PolygonGridIndex(map_nodes, cell_size)
        self._prefetch_ratio = prefetch_ratio

        self.fig, self.ax = plt.subplots(figsize=figsize)
        self.ax.set_axis_off()
        self.ax.set_aspect('equal')

        self._cached_region: Optional[Tuple[float, float, float, float]] = None
        self._map_artists = []
        self._vehicle_artists = []

    # ---------------- 对外接口 ---------------- #
    def render(self, focus_id: str, vehicles: Dict[str, Any],
               x_range, y_range):
        """渲染一帧, 返回复用的 figure.

        注意 figure 是复用的: 下一次 render 之前要先把它保存/转成数组。
        """
        self._ensure_map_layer(x_range, y_range)
        self._draw_vehicles(focus_id, vehicles, x_range, y_range)
        self.ax.set_xlim(x_range)
        self.ax.set_ylim(y_range)
        return self.fig

    def close(self) -> None:
        plt.close(self.fig)

    # ---------------- 内部 ---------------- #
    def _ensure_map_layer(self, x_range, y_range) -> None:
        """视野还在已缓存的区域内就直接复用, 否则重新查询并重建路网图层"""
        if self._cached_region is not None and self._inside_cached(x_range, y_range):
            return

        # 多取一圈, 这样视野小幅移动时不必重新查询 (路口固定时更是只会走到这里一次)
        width = x_range[1] - x_range[0]
        height = y_range[1] - y_range[0]
        pad_x = width * self._prefetch_ratio
        pad_y = height * self._prefetch_ratio
        region = (x_range[0] - pad_x, y_range[0] - pad_y,
                  x_range[1] + pad_x, y_range[1] + pad_y)

        for artist in self._map_artists:
            artist.remove()
        self._map_artists = []

        visible_lanes = self._lane_index.query(*region)
        visible_nodes = self._node_index.query(*region)
        for collection in make_map_collections(visible_lanes, visible_nodes):
            self.ax.add_collection(collection)
            self._map_artists.append(collection)

        self._cached_region = region

    def _inside_cached(self, x_range, y_range) -> bool:
        x_min, y_min, x_max, y_max = self._cached_region
        return (x_range[0] >= x_min and x_range[1] <= x_max
                and y_range[0] >= y_min and y_range[1] <= y_max)

    def _draw_vehicles(self, focus_id, vehicles, x_range, y_range) -> None:
        for artist in self._vehicle_artists:
            artist.remove()
        # 只画视野内的车辆; 留一点余量, 免得压在边界上的车突然消失
        margin = 0.1 * (x_range[1] - x_range[0])
        visible = {
            veh_id: info for veh_id, info in (vehicles or {}).items()
            if (x_range[0] - margin <= info['position'][0] <= x_range[1] + margin
                and y_range[0] - margin <= info['position'][1] <= y_range[1] + margin)
        }
        self._vehicle_artists = plot_vehicle(self.ax, focus_id, visible)
