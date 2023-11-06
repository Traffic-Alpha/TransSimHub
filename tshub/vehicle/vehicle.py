'''
@Author: WANG Maonan
@Date: 2023-08-23 15:20:12
@Description: VehicleInfo 的数据类，它包含了车辆的各种信息
@LastEditTime: 2023-11-06 21:08:53
'''
import traci
from typing import Dict, Any
from loguru import logger
from dataclasses import dataclass, fields
from typing import List, Tuple

from .vehicle_action_type import vehicle_action_type
from .vehicle_type.lane import LaneAction
from .vehicle_type.lane_with_continuous_speed import LaneWithContinuousSpeedAction

@dataclass
class VehicleInfo:
    """
    Represents information about a vehicle.
    """
    id: str  # The ID of the vehicle
    action_type:str # 车辆的动作控制类型
    vehicle_type:str # 车辆类型, ego or other
    position: Tuple[float]  # The position of the vehicle
    speed: float  # The current speed of the vehicle
    road_id: str  # The ID of the road the vehicle is on
    lane_id: str  # The ID of the lane the vehicle is on
    lane_index: int # 目前的车所在的车道 index
    edges: List[str]  # The edges the vehicle has traversed
    waiting_time: float  # The waiting time of the vehicle
    accumulated_waiting_time: float # 累积等待时间
    distance: float # 车辆行驶距离
    leader: Tuple[str, float] # 车辆的前车信息, (vehicle_id, distance)
    next_tls: List[str]  # The IDs of the next traffic lights the vehicle will encounter
    sumo: traci.connection.Connection

    def __post_init__(self) -> None:
        _action = vehicle_action_type(self.action_type)
        if _action == vehicle_action_type.Lane:
            self.vehicle_action = LaneAction(id=self.id, sumo=self.sumo)
        elif _action == vehicle_action_type.LaneWithContinuousSpeed:
            self.vehicle_action = LaneWithContinuousSpeedAction(id=self.id, sumo=self.sumo)

        # 订阅车辆
        self.sumo.vehicle.subscribe(
                self.id,
                [
                    traci.constants.VAR_POSITION, traci.constants.VAR_SPEED,
                    traci.constants.VAR_ROAD_ID, traci.constants.VAR_LANE_ID,
                    traci.constants.VAR_EDGES, traci.constants.VAR_LANE_INDEX,
                    traci.constants.VAR_WAITING_TIME, traci.constants.VAR_NEXT_TLS,
                    traci.constants.VAR_ACCUMULATED_WAITING_TIME, 
                    traci.constants.VAR_DISTANCE,     
                ]
            )
        self.sumo.vehicle.subscribeLeader(self.id, dist=0) # vehicle id together with the distance

    @classmethod
    def create_vehicle(cls, id: str, action_type:str, vehicle_type:str,
                       sumo:traci.connection.Connection,
                       position: Tuple[float], speed: float,
                       road_id: str, lane_id: str, 
                       lane_index:int, edges: List[str], 
                       waiting_time: float, accumulated_waiting_time:float,
                       distance:float, leader: Tuple[str, float],
                       next_tls: List[str]):
        logger.info(f'SIM: Init Vehicle: {vehicle_type}: {id}')
        return cls(id=id, action_type=action_type, vehicle_type=vehicle_type,
                   sumo=sumo, position=position, speed=speed,   
                   road_id=road_id, lane_id=lane_id, lane_index=lane_index,
                   edges=edges, waiting_time=waiting_time,
                   accumulated_waiting_time=accumulated_waiting_time,
                   distance=distance, leader=leader,
                   next_tls=next_tls
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
            'lane_index': 82,
            'edges': 84,
            'waiting_time': 122,
            'next_tls': 112,
            'accumulated_waiting_time': 135,
            'distance': 132,
            'leader': 104,
        }
        return feature_mapping.get(feature, -1)
    
    def update_features(self, vehicle_info:Dict[int, Any]) -> None:
        self.position=vehicle_info.get(VehicleInfo.get_feature_index('position'), None)
        self.speed=vehicle_info.get(VehicleInfo.get_feature_index('speed'), None)
        self.road_id=vehicle_info.get(VehicleInfo.get_feature_index('road_id'), None)
        self.lane_id=vehicle_info.get(VehicleInfo.get_feature_index('lane_id'), None)
        self.lane_index=vehicle_info.get(VehicleInfo.get_feature_index('lane_index'), None)
        self.edges=vehicle_info.get(VehicleInfo.get_feature_index('edges'), None)
        self.waiting_time=vehicle_info.get(VehicleInfo.get_feature_index('waiting_time'), None)
        self.accumulated_waiting_time=vehicle_info.get(VehicleInfo.get_feature_index('accumulated_waiting_time'), None)
        self.distance=vehicle_info.get(VehicleInfo.get_feature_index('distance'), None)
        self.leader=vehicle_info.get(VehicleInfo.get_feature_index('leader'), None)
        self.next_tls=vehicle_info.get(VehicleInfo.get_feature_index('next_tls'), None)

    def get_features(self):
        output_dict = {}
        for field in fields(self):
            field_name = field.name
            field_value = getattr(self, field_name)
            if field_name != 'sumo':
                output_dict[field_name] = field_value
        return output_dict

    def control_vehicle(self, lane_change, target_speed) -> None:
        current_speed = self.speed # 目前车辆的速度
        current_lane_index = self.lane_index # 目前车辆所在的 index
        current_road_id = self.road_id # 目前所在的 road id
        self.vehicle_action.execute(
            lane_change=lane_change, target_speed=target_speed, 
            current_speed=current_speed, current_lane_index=current_lane_index, current_road_id=current_road_id
        )