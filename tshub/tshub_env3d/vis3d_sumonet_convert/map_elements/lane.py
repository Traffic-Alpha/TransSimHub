'''
@Author: WANG Maonan
@Date: 2024-07-05 19:21:59
@Description: SUMO Lane
@LastEditTime: 2024-07-13 07:34:52
'''
import math
import sumolib
import numpy as np
from shapely.geometry import Polygon
from functools import cached_property, lru_cache
from typing import List, Optional, Set, Tuple, Union, overload

from .surface import Surface
from .base_road_map import RoadMap
from ..sumonet_convert_utils.geometry import buffered_shape
from ...vis3d_utils.coordinates import Point, Pose, RefLinePoint, BoundingBox

class Lane(RoadMap.Lane, Surface):
    """Describes a Sumo lane surface.
    """
    def __init__(
        self,
        lane_id: str,
        sumo_lane: sumolib.net.lane.Lane,
        road_map,
    ) -> None:
        super().__init__(lane_id, road_map)
        self._lane_id = lane_id
        self._sumo_lane = sumo_lane
        self._road = road_map.road_by_id(sumo_lane.getEdge().getID())
        assert self._road

        self._rtree_lane_fragments = None
        self._lane_shape_for_rtree: Optional[List[Tuple[float, float]]] = None

    def __hash__(self) -> int:
        return hash(self.lane_id) ^ hash(self._map)

    def _init_rtree(self, lines):
        import rtree

        rtree.index.Property()
        result = rtree.index.Index()
        result.interleaved = True
        for ri, (s, e) in enumerate(lines):
            result.add(
                ri,
                (
                    min(e[0], s[0]),
                    min(e[1], s[1]),
                    max(e[0], s[0]),
                    max(e[1], s[1]),
                ),
            )
        return result

    def _ensure_rtree(self):
        if self._rtree_lane_fragments is None:
            self._lane_shape_for_rtree = self._sumo_lane.getShape(False)
            lane_fragments = list(Surface.pairwise(self._sumo_lane.getShape(False)))
            self._rtree_lane_fragments = self._init_rtree(lane_fragments)

    @lru_cache(maxsize=128)
    def _segment_offset(self, end_index: int, start_index: int = 0) -> float:
        dist = 0.0
        for index in range(start_index, end_index):
            dist += np.linalg.norm(
                np.subtract(
                    self._lane_shape_for_rtree[index + 1],
                    self._lane_shape_for_rtree[index],
                )
            )
        return dist

    def get_distance(
        self,
        point: Point,
        radius: float,
        get_offset=...,
        perpendicular: bool = False,
    ) -> Union[float, Tuple[float, Optional[float]]]:
        """Get the distance on the lane from the given point within the given radius.
        Specifying to get the offset returns the offset value.
        """
        x = point[0]
        y = point[1]
        r = radius
        self._ensure_rtree()

        dist = math.inf
        INVALID_DISTANCE = -1
        INVALID_INDEX = -1
        found_index = INVALID_INDEX
        for i in self._rtree_lane_fragments.intersection(
            (x - r, y - r, x + r, y + r)
        ):
            d = sumolib.geomhelper.distancePointToLine(
                point,
                self._lane_shape_for_rtree[i],
                self._lane_shape_for_rtree[i + 1],
                perpendicular=perpendicular,
            )

            if d == INVALID_DISTANCE and i != 0 and dist == math.inf:
                # distance to inner corner
                dist = min(
                    sumolib.geomhelper.distance(
                        point, self._lane_shape_for_rtree[i]
                    ),
                    sumolib.geomhelper.distance(
                        point, self._lane_shape_for_rtree[i + 1]
                    ),
                )
                found_index = i
            elif d != INVALID_DISTANCE and (dist is None or d < dist):
                dist = d
                found_index = i

        if get_offset is not ...:
            if get_offset is False:
                return dist, None
            offset = 0.0
            if found_index != INVALID_INDEX:
                offset = self._segment_offset(found_index)
                offset += sumolib.geomhelper.lineOffsetWithMinimumDistanceToPoint(
                    point,
                    self._lane_shape_for_rtree[found_index],
                    self._lane_shape_for_rtree[found_index + 1],
                    False,
                )
                assert isinstance(offset, float)
            return dist, offset
        return dist

    @cached_property
    def bounding_box(self):
        xmin, ymin, xmax, ymax = self._sumo_lane.getBoundingBox(False)
        return BoundingBox(Point(xmin, ymin), Point(xmax, ymax))

    @property
    def lane_id(self) -> str:
        return self._lane_id

    @property
    def road(self):
        return self._road

    @cached_property
    def speed_limit(self) -> Optional[float]:
        return self._sumo_lane.getSpeed()

    @cached_property
    def length(self) -> float:
        # self._sumo_lane.getLength() is not accurate because it gets the length
        # of the outermost lane on the edge, not the lane you query.
        length = 0
        shape = self._sumo_lane.getShape()
        for p1, p2 in zip(shape, shape[1:]):
            length += np.linalg.norm(np.subtract(p2, p1))
        return length

    @cached_property
    def _width(self) -> float:
        return self._sumo_lane.getWidth()

    @property
    def in_junction(self) -> bool:
        return self._road.is_junction

    @cached_property
    def index(self) -> int:
        return self._sumo_lane.getIndex()

    @cached_property
    def lanes_in_same_direction(self) -> List[RoadMap.Lane]:
        if not self.in_junction:
            # When not in an intersection, all SUMO Lanes for an Edge go in the same direction.
            return [l for l in self.road.lanes if l != self]
        result = []
        in_roads = set(il.road for il in self.incoming_lanes)
        out_roads = set(il.road for il in self.outgoing_lanes)
        for lane in self.road.lanes:
            if self == lane:
                continue
            other_in_roads = set(il.road for il in lane.incoming_lanes)
            if in_roads & other_in_roads:
                other_out_roads = set(il.road for il in self.outgoing_lanes)
                if out_roads & other_out_roads:
                    result.append(lane)
        return result

    @cached_property
    def lane_to_left(self) -> Tuple[Optional[RoadMap.Lane], bool]:
        result = None
        for other in self.lanes_in_same_direction:
            if other.index > self.index and (
                not result or other.index < result.index
            ):
                result = other
        return result, True

    @cached_property
    def lane_to_right(self) -> Tuple[Optional[RoadMap.Lane], bool]:
        result = None
        for other in self.lanes_in_same_direction:
            if other.index < self.index and (
                not result or other.index > result.index
            ):
                result = other
        return result, True

    @cached_property
    def incoming_lanes(self) -> List[RoadMap.Lane]:
        # XXX: we bias these to direct connections first, so we don't skip over
        # the internal connection lanes coming into this one.  However, I've
        # encountered bugs with this within "compound junctions", so we
        # also allow for indirect if there are no direct.
        incoming_lanes = self._sumo_lane.getIncoming(
            onlyDirect=True
        ) or self._sumo_lane.getIncoming(onlyDirect=False)
        return sorted(
            (self._map.lane_by_id(incoming.getID()) for incoming in incoming_lanes),
            key=lambda l: l.lane_id,
        )

    @cached_property
    def outgoing_lanes(self) -> List[RoadMap.Lane]:
        return sorted(
            (
                self._map.lane_by_id(
                    outgoing.getViaLaneID() or outgoing.getToLane().getID()
                )
                for outgoing in self._sumo_lane.getOutgoing()
            ),
            key=lambda l: l.lane_id,
        )

    @cached_property
    def entry_surfaces(self) -> List[RoadMap.Surface]:
        return self.incoming_lanes

    @cached_property
    def exit_surfaces(self) -> List[RoadMap.Surface]:
        return self.outgoing_lanes

    @lru_cache(maxsize=16)
    def oncoming_lanes_at_offset(self, offset: float) -> List[RoadMap.Lane]:
        result = []
        radius = 1.1 * self.width_at_offset(offset)[0]
        pt = self.from_lane_coord(RefLinePoint(offset))
        nearby_lanes = self._map.nearest_lanes(pt, radius=radius)
        if not nearby_lanes:
            return result
        my_vect = self.vector_at_offset(offset)
        my_norm = np.linalg.norm(my_vect)
        if my_norm == 0:
            return result
        threshold = -0.995562  # cos(175*pi/180)
        for lane, _ in nearby_lanes:
            if lane == self:
                continue
            lane_refline_pt = lane.to_lane_coord(pt)
            lv = lane.vector_at_offset(lane_refline_pt.s)
            lv_norm = np.linalg.norm(lv)
            if lv_norm == 0:
                continue
            lane_angle = np.dot(my_vect, lv) / (my_norm * lv_norm)
            if lane_angle < threshold:
                result.append(lane)
        return result

    @cached_property
    def foes(self) -> List[RoadMap.Lane]:
        # TODO:  we might do better here since Sumo/Traci determines right-of-way for their connections/links.  See:
        #        https://sumo.dlr.de/pydoc/traci._lane.html#LaneDomain-getFoes
        result = [
            incoming
            for outgoing in self.outgoing_lanes
            for incoming in outgoing.incoming_lanes
            if incoming != self
        ]
        if self.in_junction:
            in_roads = set(il.road for il in self.incoming_lanes)
            for foe in self.road.lanes:
                foe_in_roads = set(il.road for il in foe.incoming_lanes)
                if not bool(in_roads & foe_in_roads):
                    result.append(foe)

            node = self.road._from_node
            int_lanes = node.getInternal()
            try:
                mi = int_lanes.index(self.lane_id)
                for fi, foe_id in enumerate(int_lanes):
                    if node.areFoes(mi, fi):
                        foe = self._map.lane_by_id(foe_id)
                        result.append(foe)
            except ValueError:
                pass

        return list(set(result))

    @lru_cache(maxsize=4)
    def shape(
        self, buffer_width: float = 0.0, default_width: Optional[float] = None
    ) -> Polygon:
        new_width = buffer_width
        if default_width:
            new_width += default_width
        else:
            new_width += self._width

        assert new_width >= 0.0
        assert new_width >= 0.0
        if new_width > 0:
            return buffered_shape(self._sumo_lane.getShape(), new_width)
        line = self._sumo_lane.getShape()
        bline = buffered_shape(line, 0.0)
        return line if bline.is_empty else bline

    @lru_cache(maxsize=8)
    def contains_point(self, point: Point) -> bool:
        # TAI:  could use (cached) self._sumo_lane.getBoundingBox(...) as a quick first-pass check...
        lane_point = self.to_lane_coord(point)
        return (
            abs(lane_point.t) <= self._width / 2 and 0 <= lane_point.s < self.length
        )

    @lru_cache(maxsize=1024)
    def offset_along_lane(self, world_point: Point) -> float:
        shape = self._sumo_lane.getShape(False)
        point = world_point[:2]
        if point not in shape:
            if self._lane_shape_for_rtree is None and len(shape) < 5:
                offset = sumolib.geomhelper.polygonOffsetWithMinimumDistanceToPoint(
                    point, shape, perpendicular=False
                )
            else:
                _, offset = self.get_distance(
                    world_point, 8, get_offset=True, perpendicular=False
                )
            return offset
        # SUMO geomhelper.polygonOffset asserts when the point is part of the shape.
        # We get around the assertion with a check if the point is part of the shape.
        offset = 0
        for i in range(len(shape) - 1):
            if shape[i] == point:
                break
            offset += sumolib.geomhelper.distance(shape[i], shape[i + 1])
        return offset

    def width_at_offset(self, offset: float) -> Tuple[float, float]:
        return self._width, 1.0

    @lru_cache(maxsize=8)
    def project_along(
        self, start_offset: float, distance: float
    ) -> Set[Tuple[RoadMap.Lane, float]]:
        return super().project_along(start_offset, distance)

    @lru_cache(maxsize=1024)
    def from_lane_coord(self, lane_point: RefLinePoint) -> Point:
        shape = self._sumo_lane.getShape(False)
        x, y = sumolib.geomhelper.positionAtShapeOffset(shape, lane_point.s)
        if lane_point.t != 0 and lane_point.t is not None:
            dv = 1 if lane_point.s < self.length else -1
            x2, y2 = sumolib.geomhelper.positionAtShapeOffset(
                shape, lane_point.s + dv
            )
            dx = dv * (x2 - x)
            dy = dv * (y2 - y)
            dd = (lane_point.t or 0) / np.linalg.norm((dx, dy))
            x -= dy * dd
            y += dx * dd
        return Point(x=x, y=y)

    @lru_cache(maxsize=1024)
    def to_lane_coord(self, world_point: Point) -> RefLinePoint:
        return super().to_lane_coord(world_point)

    @lru_cache(maxsize=8)
    def center_at_point(self, point: Point) -> Point:
        return super().center_at_point(point)

    @lru_cache(8)
    def _edges_at_point(self, point: Point) -> Tuple[Point, Point]:
        """Get the boundary points perpendicular to the center of the lane closest to the given
            world coordinate.
        Args:
            point:
                A world coordinate point.
        Returns:
            A pair of points indicating the left boundary and right boundary of the lane.
        """
        offset = self.offset_along_lane(point)
        width, _ = self.width_at_offset(offset)
        left_edge = RefLinePoint(s=offset, t=width / 2)
        right_edge = RefLinePoint(s=offset, t=-width / 2)
        return self.from_lane_coord(left_edge), self.from_lane_coord(right_edge)

    @lru_cache(1024)
    def vector_at_offset(self, start_offset: float) -> np.ndarray:
        return super().vector_at_offset(start_offset)

    @lru_cache(maxsize=8)
    def center_pose_at_point(self, point: Point) -> Pose:
        return super().center_pose_at_point(point)

    @lru_cache(maxsize=1024)
    def curvature_radius_at_offset(
        self, offset: float, lookahead: int = 5
    ) -> float:
        return super().curvature_radius_at_offset(offset, lookahead)