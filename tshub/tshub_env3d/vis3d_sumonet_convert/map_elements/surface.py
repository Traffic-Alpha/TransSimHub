'''
@Author: WANG Maonan
@Date: 2024-07-05 19:10:34
@Description: 定义 SUMO Surface
@LastEditTime: 2024-07-13 05:10:54
'''
import itertools
from typing import List, Optional

from .base_road_map import RoadMap
from ...vis3d_utils.coordinates import Pose

class Surface(RoadMap.Surface):
    """Describes a Sumo surface (lane & road).
    """
    def __init__(self, surface_id: str, road_map):
        self._surface_id = surface_id
        self._map = road_map
        self._features = dict()

    @property
    def surface_id(self) -> str:
        return self._surface_id

    @property
    def is_drivable(self) -> bool:
        # all surfaces on SUMO road networks are drivable
        return True

    @property
    def features(self) -> List[RoadMap.Feature]:
        return list(self._features.values())

    def features_near(self, pose: Pose, radius: float) -> List[RoadMap.Feature]:
        pt = pose.point
        return [
            feat
            for feat in self._features.values()
            if radius >= feat.min_dist_from(pt)
        ]

    def surface_by_id(self, surface_id: str) -> Optional[RoadMap.Surface]:
        return self._surfaces.get(surface_id)
    
    @staticmethod
    def pairwise(iterable):
        """Generates pairs of neighboring elements.
        >>> list(pairwise('ABCDEFG'))
        [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'E'), ('E', 'F'), ('F', 'G')]
        """
        a, b = itertools.tee(iterable)
        next(b, None)
        return zip(a, b)