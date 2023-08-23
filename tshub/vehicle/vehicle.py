'''
@Author: WANG Maonan
@Date: 2023-08-23 15:20:12
@Description: VehicleInfo 的数据类，它包含了车辆的各种信息
@LastEditTime: 2023-08-23 17:52:39
'''
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class VehicleInfo:
    """
    Represents information about a vehicle.
    """
    id: str  # The ID of the vehicle
    position: Tuple[float]  # The position of the vehicle
    speed: float  # The current speed of the vehicle
    road_id: str  # The ID of the road the vehicle is on
    lane_id: str  # The ID of the lane the vehicle is on
    edges: List[str]  # The edges the vehicle has traversed
    waiting_time: float  # The waiting time of the vehicle
    next_tls: List[str]  # The IDs of the next traffic lights the vehicle will encounter
    
    @classmethod
    def from_subscription_result(cls, veh_id:str, result: dict) -> 'VehicleInfo':
        """
        Create a VehicleInfo object from a subscription result dictionary.
        Args:
            result: A dictionary containing the subscription result for a vehicle.
        Returns:
            A VehicleInfo object.
        """
        return cls(
            id=veh_id,
            position=result[VehicleInfo.get_feature_index('position')],
            speed=result[VehicleInfo.get_feature_index('speed')],
            road_id=result[VehicleInfo.get_feature_index('road_id')],
            lane_id=result[VehicleInfo.get_feature_index('lane_id')],
            edges=result[VehicleInfo.get_feature_index('edges')],
            waiting_time=result[VehicleInfo.get_feature_index('waiting_time')],
            next_tls=result[VehicleInfo.get_feature_index('next_tls')]
        )

    @staticmethod
    def get_feature_index(feature: str) -> int:
        """
        Get the index of a feature in the subscription result.
        Args:
            feature: The name of the feature.
        Returns:
            The index of the feature.
        """
        feature_mapping = {
            'position': 66,
            'speed': 64,
            'road_id': 80,
            'lane_id': 81,
            'edges': 84,
            'waiting_time': 122,
            'next_tls': 112
        }
        return feature_mapping.get(feature, -1)