'''
@Author: WANG Maonan
@Date: 2024-07-05 20:41:55
@Description: SUMO Road
@LastEditTime: 2024-07-13 07:34:39
'''
import sumolib
from shapely.geometry import Polygon
from typing import List, Optional, Tuple
from functools import cached_property, lru_cache

from .surface import Surface
from .base_road_map import RoadMap
from ..sumonet_convert_utils.geometry import buffered_shape
from ...vis3d_utils.coordinates import Point

class Road(RoadMap.Road, Surface):
    """This is akin to a 'road segment' in real life.
    Many of these might correspond to a single named road in reality."""

    def __init__(
        self,
        road_id: str,
        sumo_edge: sumolib.net.edge.Edge,
        road_map,
    ):
        super().__init__(road_id, road_map)
        self._road_id = road_id
        self._sumo_edge = sumo_edge

    def __hash__(self) -> int:
        return hash(self.road_id) + hash(self._map)

    @cached_property
    def is_junction(self) -> bool:
        return self._sumo_edge.isSpecial()

    @property
    def _to_node(self):
        return self._sumo_edge.getToNode()

    @property
    def _from_node(self):
        return self._sumo_edge.getFromNode()

    @cached_property
    def length(self) -> float:
        return self._sumo_edge.getLength()

    @property
    def road_id(self) -> str:
        return self._road_id

    @cached_property
    def incoming_roads(self) -> List[RoadMap.Road]:
        return [
            self._map.road_by_id(edge.getID())
            for edge in self._sumo_edge.getIncoming().keys()
        ]

    @cached_property
    def outgoing_roads(self) -> List[RoadMap.Road]:
        return [
            self._map.road_by_id(edge.getID())
            for edge in self._sumo_edge.getOutgoing().keys()
        ]

    @cached_property
    def entry_surfaces(self) -> List[RoadMap.Surface]:
        # TAI:  also include lanes here?
        return self.incoming_roads

    @cached_property
    def exit_surfaces(self) -> List[RoadMap.Surface]:
        # TAI:  also include lanes here?
        return self.outgoing_roads

    @lru_cache(maxsize=16)
    def oncoming_roads_at_point(self, point: Point) -> List[RoadMap.Road]:
        result = []
        for lane in self.lanes:
            offset = lane.to_lane_coord(point).s
            result += [
                ol.road
                for ol in lane.oncoming_lanes_at_offset(offset)
                if ol.road != self
            ]
        return result

    @cached_property
    def parallel_roads(self) -> List[RoadMap.Road]:
        from_node, to_node = (
            self._sumo_edge.getFromNode(),
            self._sumo_edge.getToNode(),
        )
        # XXX: not that in most junctions from_node==to_node, so the following will
        # include ALL internal edges within a junction (even those crossing this one).
        return [
            self._map.road_by_id(edge.getID())
            for edge in from_node.getOutgoing()
            if self.road_id != edge.getID()
            and edge.getToNode().getID() == to_node.getID()
        ]

    @cached_property
    def lanes(self) -> List[RoadMap.Lane]:
        return [
            self._map.lane_by_id(sumo_lane.getID())
            for sumo_lane in self._sumo_edge.getLanes()
        ]

    def lane_at_index(self, index: int) -> RoadMap.Lane:
        return self.lanes[index]

    @lru_cache(maxsize=8)
    def contains_point(self, point: Point) -> bool:
        # TAI:  could use (cached) self._sumo_edge.getBoundingBox(...) as a quick first-pass check...
        for lane in self.lanes:
            if lane.contains_point(point):
                return True
        return False

    @lru_cache(maxsize=8)
    def _edges_at_point(self, point: Point) -> Tuple[Point, Point]:
        """Get the boundary points perpendicular to the center of the road closest to the given
            world coordinate.
        Args:
            point:
                A world coordinate point.
        Returns:
            A pair of points indicating the left boundary and right boundary of the road.
        """
        lanes = self.lanes
        _, right_edge = lanes[0]._edges_at_point(point)
        left_edge, _ = lanes[-1]._edges_at_point(point)
        return left_edge, right_edge

    @lru_cache(maxsize=4)
    def shape(
        self, buffer_width: float = 0.0, default_width: Optional[float] = None
    ) -> Polygon:
        new_width = buffer_width
        if default_width:
            new_width += default_width
        assert new_width >= 0.0
        if new_width > 0:
            return buffered_shape(self._sumo_edge.getShape(), new_width)
        line = self._sumo_edge.getShape()
        bline = buffered_shape(line, 0.0)
        return line if bline.is_empty else bline