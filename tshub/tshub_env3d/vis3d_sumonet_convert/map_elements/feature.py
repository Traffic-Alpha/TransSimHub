'''
@Author: WANG Maonan
@Date: 2024-07-05 20:29:47
@Description: Features for SUMO Network (信号灯)
@LastEditTime: 2024-07-13 05:07:55
'''
import numpy as np
from functools import cached_property
from typing import Any, List, Optional

from .base_road_map import RoadMap
from ...vis3d_utils.coordinates import Point, RefLinePoint

class Feature(RoadMap.Feature):
    """Feature representation for Sumo road networks
    """
    def __init__(
        self,
        road_map,
        feature_id: str,
        feat_data,
        feat_type=RoadMap.FeatureType.FIXED_LOC_SIGNAL,
    ) -> None:
        self._map = road_map
        self._feature_id = feature_id
        self._feat_data = feat_data
        # we only know how to get traffic light signals out of Sumo maps so far...
        self._type = feat_type

    @property
    def feature_id(self) -> str:
        return self._feature_id

    @property
    def type(self) -> RoadMap.FeatureType:
        return self._type

    @property
    def type_as_str(self) -> str:
        return self._type.name

    @cached_property
    def geometry(self) -> List[Point]:
        assert isinstance(self._feat_data, list), f"{self._feat_data}"
        in_lane = self._map.lane_by_id(self._feat_data[0].getID())
        stop_pos = in_lane.from_lane_coord(RefLinePoint(s=in_lane.length))
        return [stop_pos]

    @cached_property
    def type_specific_info(self) -> Optional[Any]:
        # the only type we currently handle is FIXED_LOC_SIGNAL
        in_lane, to_lane, _ = self._feat_data
        via_id = in_lane.getConnection(to_lane).getViaLaneID()
        return self._map.lane_by_id(via_id)

    def min_dist_from(self, point: Point) -> float:
        return np.linalg.norm(self.geometry[0].as_np_array - point.as_np_array)