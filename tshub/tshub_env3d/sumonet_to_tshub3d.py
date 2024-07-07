'''
@Author: WANG Maonan
@Date: 2024-07-03 16:05:08
@Description: 将 SUMO Net 转换为 glb 文件
这部分修改自, https://github.com/huawei-noah/SMARTS/blob/master/smarts/core/sumo_road_network.py
@LastEditTime: 2024-07-08 01:01:31
'''
import math
import sumolib
import numpy as np

from pathlib import Path
from loguru import logger
from functools import cached_property, lru_cache

from shapely.geometry import Polygon
from shapely.geometry import Point as shPoint
from shapely.ops import nearest_points, snap

from typing import Any, Dict, List, Optional, Tuple

from .vis3d_net.road_map import RoadMap
from .vis3d_utils.geometry import buffered_shape
from .vis3d_utils.coordinates import BoundingBox, Point

from .vis3d_net.lane import Lane
from .vis3d_net.road import Road
from .vis3d_net.feature import Feature # TODO, 确认一下 Feature 是否有用到
from .vis3d_net.glb import make_map_glb, make_line_glb, make_road_glb

class SumoNet3D():
    DEFAULT_LANE_WIDTH = 3.2
    """3.2 is the default Sumo road network lane width if it's not specified
     explicitly in Sumo's NetEdit or the `map.net.xml` file.
    This corresponds on a 1:1 scale to lanes 3.2m wide, which is typical
     in North America (although US highway lanes are wider at ~3.7m).
    """
    def __init__(self, net_file: str):
        self._graph = sumolib.net.readNet(net_file, withInternal=True)
        self._default_lane_width = SumoNet3D.DEFAULT_LANE_WIDTH
        self._surfaces = dict()
        self._lanes: Dict[str, Lane] = dict()
        self._roads: Dict[str, Road] = dict()
        self._features = dict()
        self._rtree_roads = None
        self._load_traffic_lights() # 初始化信号灯

    def to_glb(self, glb_dir:str) -> None:
        """将 SUMO Net 可以转换为 glb 文件 (核心功能)

        Args:
            glb_dir (str): glb 文件输出路径
        """
        polys = self._compute_road_polygons()
        lane_dividers, edge_dividers = self._compute_traffic_dividers()
        map_glb = make_map_glb(
            polygons=polys, 
            bbox=self.bounding_box, 
            lane_dividers=lane_dividers, 
            edge_dividers=edge_dividers
        )
        map_glb.write_glb(Path(glb_dir) / "map.glb")

        road_lines_glb = make_road_glb(edge_dividers)
        road_lines_glb.write_glb(Path(glb_dir) / "road_lines.glb")

        lane_lines_glb = make_line_glb(lane_dividers)
        lane_lines_glb.write_glb(Path(glb_dir) / "lane_lines.glb")
    
    # -------------------- #
    # Step 1, 获得道路的多边形
    # -------------------- #
    def _compute_road_polygons(self) -> List[Tuple[Polygon, Dict[str, Any]]]:
        lane_to_poly = {} # 存储 lane_id 和对应的形状
        for edge in self._graph.getEdges():
            for lane in edge.getLanes():
                shape = buffered_shape(lane.getShape(), lane.getWidth())
                # Check if "shape" is just a point.
                if len(set(shape.exterior.coords)) == 1:
                    logger.debug(
                        f"SIM: Lane:{lane.getID()} has provided non-shape values {lane.getShape()}"
                    )
                    continue

                metadata = {
                    "road_id": edge.getID(),
                    "lane_id": lane.getID(),
                    "lane_index": lane.getIndex(),
                }
                lane_to_poly[lane.getID()] = (shape, metadata)

        # Remove holes created at tight junctions due to crude map geometry
        self._snap_internal_holes(lane_to_poly)
        self._snap_external_holes(lane_to_poly)

        # Remove break in visible lane connections created when lane enters an intersection
        self._snap_internal_edges(lane_to_poly)

        polys = list(lane_to_poly.values())

        for node in self._graph.getNodes():
            line = node.getShape()
            if len(line) <= 2 or len(set(line)) == 1:
                logger.debug(
                    f"SIM: Skipping {node.getType()}-type node with <= 2 vertices"
                )
                continue

            metadata = {"road_id": node.getID()}
            polys.append((Polygon(line), metadata))

        return polys

    def _snap_internal_edges(self, lane_to_poly, snap_threshold=2):
        # HACK: Internal edges that have tight curves, when buffered their ends do not
        #       create a tight seam with the connected lanes. This procedure attempts
        #       to remedy that with snapping.
        for lane_id in lane_to_poly:
            lane = self._graph.getLane(lane_id)

            # Only do snapping for internal edge lanes
            if not lane.getEdge().isSpecial():
                continue

            lane_shape, metadata = lane_to_poly[lane_id]
            incoming = self._graph.getLane(lane_id).getIncoming()[0]
            incoming_shape = lane_to_poly.get(incoming.getID())
            if incoming_shape:
                lane_shape = Polygon(
                    snap(lane_shape, incoming_shape[0], snap_threshold)
                )
                lane_to_poly[lane_id] = (Polygon(lane_shape), metadata)

            outgoing = self._graph.getLane(lane_id).getOutgoing()[0].getToLane()
            outgoing_shape = lane_to_poly.get(outgoing.getID())
            if outgoing_shape:
                lane_shape = Polygon(
                    snap(lane_shape, outgoing_shape[0], snap_threshold)
                )
                lane_to_poly[lane_id] = (Polygon(lane_shape), metadata)

    def _snap_internal_holes(self, lane_to_poly, snap_threshold=2):
        for lane_id in lane_to_poly:
            lane = self._graph.getLane(lane_id)

            # Only do snapping for internal edge lane holes
            if not lane.getEdge().isSpecial():
                continue
            lane_shape, metadata = lane_to_poly[lane_id]
            new_coords = []
            last_added = None
            for x, y in lane_shape.exterior.coords:
                p = shPoint(x, y)
                snapped_to = set()
                moved = True
                thresh = snap_threshold
                while moved:
                    moved = False
                    for nl, dist in self.nearest_lanes(
                        Point(p.x, p.y),
                        include_junctions=False,
                    ):
                        if not nl or nl.lane_id == lane_id or nl in snapped_to:
                            continue
                        nl_shape = lane_to_poly.get(nl.lane_id)
                        if nl_shape:
                            _, npt = nearest_points(p, nl_shape[0])
                            if p.distance(npt) < thresh:
                                p = npt
                                # allow vertices to snap to more than one thing, but
                                # try to avoid infinite loops and making things worse instead of better here...
                                # (so reduce snap dist threshold by an arbitrary amount each pass.)
                                moved = True
                                snapped_to.add(nl)
                                thresh *= 0.75
                if p != last_added:
                    new_coords.append((p.x, p.y))
                    last_added = p
            if new_coords:
                lane_to_poly[lane_id] = (Polygon(new_coords), metadata)

    def _snap_external_holes(self, lane_to_poly, snap_threshold=2):
        for lane_id in lane_to_poly:
            lane = self._graph.getLane(lane_id)

            # Only do snapping for external edge lane holes
            if lane.getEdge().isSpecial():
                continue

            incoming = lane.getIncoming()
            if incoming and incoming[0].getEdge().isSpecial():
                continue

            outgoing = lane.getOutgoing()
            if outgoing:
                outgoing_lane = outgoing[0].getToLane()
                if outgoing_lane.getEdge().isSpecial():
                    continue

            lane_shape, metadata = lane_to_poly[lane_id]
            new_coords = []
            last_added = None
            for x, y in lane_shape.exterior.coords:
                p = shPoint(x, y)
                snapped_to = set()
                moved = True
                thresh = snap_threshold
                while moved:
                    moved = False
                    for nl, dist in self.nearest_lanes(
                        Point(p.x, p.y),
                        include_junctions=False,
                    ):
                        if (
                            not nl
                            or nl.in_junction
                            or nl.lane_id == lane_id
                            or nl in snapped_to
                        ):
                            continue
                        nl_shape = lane_to_poly.get(nl.lane_id)
                        if nl_shape:
                            _, npt = nearest_points(p, nl_shape[0])
                            if p.distance(npt) < thresh:
                                p = npt
                                # allow vertices to snap to more than one thing, but
                                # try to avoid infinite loops and making things worse instead of better here...
                                # (so reduce snap dist threshold by an arbitrary amount each pass.)
                                moved = True
                                snapped_to.add(nl)
                                thresh *= 0.75
                if p != last_added:
                    new_coords.append((p.x, p.y))
                    last_added = p
            if new_coords:
                lane_to_poly[lane_id] = (Polygon(new_coords), metadata)

    @lru_cache(maxsize=1024)
    def nearest_lanes(
        self, point: Point, radius: Optional[float] = None, include_junctions=True
    ) -> List[Tuple[RoadMap.Lane, float]]:
        if radius is None:
            radius = self._default_lane_width
            
        candidate_lanes = []
        for r in self.nearest_roads(point, radius):
            for l in r.lanes:
                l: Lane
                if (distance := l.get_distance(point, radius)) < math.inf:
                    candidate_lanes.append((l._sumo_lane, distance))

        if not include_junctions:
            candidate_lanes = [
                lane for lane in candidate_lanes if not lane[0].getEdge().isSpecial()
            ]
        candidate_lanes.sort(key=lambda lane_dist_tup: lane_dist_tup[1])
        return [(self.lane_by_id(lane.getID()), dist) for lane, dist in candidate_lanes]

    def nearest_roads(self, point: Point, radius: float):
        """Finds the nearest roads to the given point within the given radius.
        """
        x = point[0]
        y = point[1]
        r = radius
        edges: List[sumolib.net.edge.Edge] = sorted(
            self._graph.getEdges(), key=lambda e: e.getID()
        )
        if self._rtree_roads is None:
            self._rtree_roads = self._init_rtree(edges)
        near_roads: List[RoadMap.Road] = []
        for i in self._rtree_roads.intersection((x - r, y - r, x + r, y + r)):
            near_roads.append(self.road_by_id(edges[i].getID()))
        return near_roads
    
    # ------------------- #
    # Step 2, 计算车道分割线
    # ------------------- #
    def _compute_traffic_dividers(self):
        edge_borders = [] # 存储道路边缘的边界, 保存为 road_lines
        lane_dividers = [] # 车道分割线, 保存为 lane_lines

        # 1. 获得道路边界和车道分割线
        for edge in self._graph.getEdges():
            # Omit intersection for now
            if edge.getFunction() == "internal":
                continue

            lanes = edge.getLanes() # 获得所有 edge 的 lane
            for i in range(len(lanes)):
                shape = lanes[i].getShape()
                left_side = sumolib.geomhelper.move2side(
                    shape, -lanes[i].getWidth() / 2
                ) # 获得车道左侧位置
                right_side = sumolib.geomhelper.move2side(
                    shape, lanes[i].getWidth() / 2
                ) # 获得车道右侧位置

                # Edge Board 里面有第一个边和最后一个边
                if i == 0:
                    edge_borders.append(right_side)

                if i == len(lanes) - 1:
                    edge_borders.append(left_side)
                else: # 其他的放在 lane driver 里面, lane 的间隔可以不需要很密
                    lane_dividers.append(SumoNet3D.interpolate_points(
                        points=left_side, 
                        distance=3
                    )
                )
            # 将 road 边缘可以封闭 (例如有路口停车线)
            edge_borders.append(
                [
                    edge_borders[-2][-1], # 新加入的两条边的最后一个点
                    edge_borders[-1][-1]
                ]
            )

        return lane_dividers, edge_borders

    @staticmethod
    def interpolate_points(points, distance=1):
        interpolated_points = []
        for i in range(len(points) - 1):
            start_point = np.array(points[i])
            end_point = np.array(points[i + 1])
            segment_vector = end_point - start_point
            segment_length = np.linalg.norm(segment_vector)
            num_new_points = int(segment_length // distance)
            unit_vector = segment_vector / segment_length
            
            interpolated_points.append(tuple(start_point))
            for j in range(1, num_new_points):
                new_point = start_point + unit_vector * distance * j
                interpolated_points.append(tuple(new_point))
        
        interpolated_points.append(points[-1])  # Add the last point
        return interpolated_points.copy()
    

    # ------- #
    # 工具函数
    # ------- #
    def _init_rtree(
        self, shapeList: List[sumolib.net.edge.Edge], includeJunctions=True
    ):
        import rtree

        result = rtree.index.Index()
        result.interleaved = True
        MAX_VAL = 1e100
        for ri, shape in enumerate(shapeList):
            sumo_lanes: List[sumolib.net.lane.Lane] = shape.getLanes()
            lane_bbs = list(
                lane.getBoundingBox(includeJunctions) for lane in sumo_lanes
            )
            cxmin, cymin, cxmax, cymax = MAX_VAL, MAX_VAL, -MAX_VAL, -MAX_VAL
            for xmin, ymin, xmax, ymax in lane_bbs:
                cxmin = min(cxmin, xmin)
                cxmax = max(cxmax, xmax)
                cymin = min(cymin, ymin)
                cymax = max(cymax, ymax)

            bb = (cxmin, cymin, cxmax, cymax)
            result.add(ri, bb)
        return result

    def _update_rtree(
        self, rtree_, shapeList: List[sumolib.net.edge.Edge], includeJunctions=True
    ):
        import rtree

        rtree_: rtree.index.Index
        MAX_VAL = 1e100
        for ri, shape in enumerate(shapeList):
            sumo_lanes: List[sumolib.net.lane.Lane] = shape.getLanes()
            lane_bbs = list(
                lane.getBoundingBox(includeJunctions) for lane in sumo_lanes
            )
            cxmin, cymin, cxmax, cymax = MAX_VAL, MAX_VAL, -MAX_VAL, -MAX_VAL
            for xmin, ymin, xmax, ymax in lane_bbs:
                cxmin = min(cxmin, xmin)
                cxmax = max(cxmax, xmax)
                cymin = min(cymin, ymin)
                cymax = max(cymax, ymax)

            bb = (cxmin, cymin, cxmax, cymax)
            rtree_.add(ri, bb)

    def _load_traffic_lights(self):
        for tls in self._graph.getTrafficLights():
            tls_id = tls.getID()
            for s, cnxn in enumerate(tls.getConnections()):
                in_lane, to_lane, link_ind = cnxn
                feature_id = f"tls_{tls_id}-{link_ind}"
                via = in_lane.getConnection(to_lane).getViaLaneID()
                via = self.lane_by_id(via)
                feature = Feature(self, feature_id, cnxn)
                self._features[feature_id] = feature
                via._features[feature_id] = feature

    @cached_property
    def bounding_box(self) -> BoundingBox:
        # maps are assumed to start at the origin
        bb = self._graph.getBoundary()  # 2D bbox in format (xmin, ymin, xmax, ymax)
        return BoundingBox(
            min_pt=Point(x=bb[0], y=bb[1]), max_pt=Point(x=bb[2], y=bb[3])
        )

    @property
    def scale_factor(self) -> float:
        # map units per meter
        return self._default_lane_width / SumoNet3D.DEFAULT_LANE_WIDTH

    def lane_by_id(self, lane_id: str) -> Lane:
        lane = self._lanes.get(lane_id)
        if lane:
            return lane
        sumo_lane = self._graph.getLane(lane_id)
        assert (
            sumo_lane
        ), f"SumoNet3D got request for unknown lane_id: '{lane_id}'"
        lane = Lane(lane_id, sumo_lane, self)
        self._lanes[lane_id] = lane
        assert lane_id not in self._surfaces
        self._surfaces[lane_id] = lane
        return lane

    def road_by_id(self, road_id: str) -> Road:
        road = self._roads.get(road_id)
        if road:
            return road
        sumo_edge = self._graph.getEdge(road_id)
        assert (
            sumo_edge
        ), f"SumoNet3D got request for unknown road_id: '{road_id}'"
        road = Road(road_id, sumo_edge, self)
        self._roads[road_id] = road
        if self._rtree_roads is not None:
            self._update_rtree(self._rtree_roads, [road._sumo_edge], False)
        assert road_id not in self._surfaces
        self._surfaces[road_id] = road
        return road

    def feature_by_id(self, feature_id: str) -> Optional[RoadMap.Feature]:
        return self._features.get(feature_id)