'''
@Author: WANG Maonan
@Date: 2023-08-23 15:20:12
@Description: VehicleInfo 的数据类，它包含了车辆的各种信息
@LastEditTime: 2024-08-11 19:18:19
'''
import traci
from typing import Dict, Any
from loguru import logger
from dataclasses import dataclass, fields
from typing import List, Tuple

from .vehicle_action_type import vehicle_action_type
from .vehicle_type import (
    LaneAction,
    SpeedAction,
    LaneWithContinuousSpeedAction,
)

@dataclass
class VehicleInfo:
    """
    Represents information about a vehicle.
    """
    id: str  # The ID of the vehicle
    action_type:str # 车辆的动作控制类型
    vehicle_type:str # 车辆类型, ego or other
    length: float # the length of the vehicles [m]
    width: float # the width of this vehicle [m]
    heading: float # the angle of the named vehicle within the last step [°]
    position: Tuple[float]  # The position of the vehicle
    speed: float  # The current speed of the vehicle
    road_id: str  # The ID of the road the vehicle is on
    lane_id: str  # The ID of the lane the vehicle is on
    lane_index: int # 目前的车所在的车道 index
    lane_position: float # The position of the vehicle along the lane (the distance from the front bumper to the start of the lane in [m])
    edges: List[str]  # The edges the vehicle has traversed
    waiting_time: float  # The waiting time of the vehicle
    accumulated_waiting_time: float # 累积等待时间
    distance: float # 车辆行驶距离
    co2_emission: float # 车辆每一个 step 的 co2 的排放 (mg/s)
    fuel_consumption: float # 车辆每一个 step 的油耗, mg/s
    speed_without_traci: float # 如果不使用 sumo 控制车辆会行驶的速度
    leader: Tuple[str, float] # 车辆的前车信息, (vehicle_id, distance)
    next_tls: List[str]  # The IDs of the next traffic lights the vehicle will encounter
    sumo: traci.connection.Connection

    def __post_init__(self) -> None:
        _action = vehicle_action_type(self.action_type)
        if _action == vehicle_action_type.Lane:
            self.vehicle_action = LaneAction(id=self.id, vehicle_type=self.vehicle_type, sumo=self.sumo)
        elif _action == vehicle_action_type.Speed:
            self.vehicle_action = SpeedAction(id=self.id, vehicle_type=self.vehicle_type, sumo=self.sumo)
        elif _action == vehicle_action_type.LaneWithContinuousSpeed:
            self.vehicle_action = LaneWithContinuousSpeedAction(id=self.id, vehicle_type=self.vehicle_type, sumo=self.sumo)

        # 订阅车辆
        self.sumo.vehicle.subscribe(
                self.id,
                [
                    traci.constants.VAR_POSITION, traci.constants.VAR_SPEED,
                    traci.constants.VAR_ROAD_ID, traci.constants.VAR_LANE_ID,
                    traci.constants.VAR_EDGES, traci.constants.VAR_LANE_INDEX,
                    traci.constants.VAR_LANEPOSITION,
                    traci.constants.VAR_WAITING_TIME, traci.constants.VAR_NEXT_TLS,
                    traci.constants.VAR_ACCUMULATED_WAITING_TIME, 
                    traci.constants.VAR_DISTANCE, traci.constants.VAR_ANGLE,
                    traci.constants.VAR_CO2EMISSION, traci.constants.VAR_FUELCONSUMPTION,
                    traci.constants.VAR_SPEED_WITHOUT_TRACI
                ]
            )
        self.sumo.vehicle.subscribeLeader(self.id, dist=0) # vehicle id together with the distance

    @classmethod
    def create_vehicle(cls, id: str, action_type:str, vehicle_type:str,
                       length:float, width: float, heading: float,
                       sumo:traci.connection.Connection,
                       position: Tuple[float], speed: float,
                       road_id: str, lane_id: str, lane_position:float,
                       lane_index:int, edges: List[str], 
                       waiting_time: float, accumulated_waiting_time:float,
                       co2_emission: float, fuel_consumption: float,
                       distance:float, speed_without_traci: float,
                       leader: Tuple[str, float],
                       next_tls: List[str]
                    ):
        logger.info(f'SIM: Init Vehicle: {vehicle_type}: {id}')
        return cls(id=id, action_type=action_type, vehicle_type=vehicle_type,
                   length=length, width=width, heading=heading,
                   sumo=sumo, position=position, speed=speed,   
                   road_id=road_id, lane_id=lane_id, lane_index=lane_index, lane_position=lane_position,
                   edges=edges, waiting_time=waiting_time,
                   accumulated_waiting_time=accumulated_waiting_time,
                   co2_emission=co2_emission, fuel_consumption=fuel_consumption,
                   speed_without_traci=speed_without_traci,
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
            'lane_position': 86,
            'edges': 84,
            'waiting_time': 122,
            'next_tls': 112,
            'accumulated_waiting_time': 135,
            'distance': 132,
            'heading': 67,
            'co2_emission': 96,
            'fuel_consumption': 101,
            'speed_without_traci': 177,
            'leader': 104,
        }
        return feature_mapping.get(feature, -1)
    
    def update_features(self, vehicle_info:Dict[int, Any]) -> None:
        self.position=vehicle_info.get(VehicleInfo.get_feature_index('position'), None)
        self.heading=vehicle_info.get(VehicleInfo.get_feature_index('heading'), None)
        self.speed=vehicle_info.get(VehicleInfo.get_feature_index('speed'), None)
        self.road_id=vehicle_info.get(VehicleInfo.get_feature_index('road_id'), None)
        self.lane_id=vehicle_info.get(VehicleInfo.get_feature_index('lane_id'), None)
        self.lane_position=vehicle_info.get(VehicleInfo.get_feature_index('lane_position'), None)
        self.lane_index=vehicle_info.get(VehicleInfo.get_feature_index('lane_index'), None)
        self.edges=vehicle_info.get(VehicleInfo.get_feature_index('edges'), None)
        self.waiting_time=vehicle_info.get(VehicleInfo.get_feature_index('waiting_time'), None)
        self.accumulated_waiting_time=vehicle_info.get(VehicleInfo.get_feature_index('accumulated_waiting_time'), None)
        self.distance=vehicle_info.get(VehicleInfo.get_feature_index('distance'), None)
        self.leader=vehicle_info.get(VehicleInfo.get_feature_index('leader'), None)
        self.next_tls=vehicle_info.get(VehicleInfo.get_feature_index('next_tls'), None)
        self.co2_emission=vehicle_info.get(VehicleInfo.get_feature_index('co2_emission'), None)
        self.fuel_consumption=vehicle_info.get(VehicleInfo.get_feature_index('fuel_consumption'), None)
        self.speed_without_traci=vehicle_info.get(VehicleInfo.get_feature_index('speed_without_traci'), None)
        
        
    def get_features(self):
        output_dict = {}
        for field in fields(self):
            field_name = field.name
            field_value = getattr(self, field_name)
            if field_name != 'sumo':
                output_dict[field_name] = field_value
        return output_dict


    def control_vehicle(self, vehicle_actions:Dict[str, float],) -> None:
        current_speed = self.speed # 目前车辆的速度
        current_lane_index = self.lane_index # 目前车辆所在的 index
        current_road_id = self.road_id # 目前所在的 road id
        self.vehicle_action.execute(
            **vehicle_actions,
            current_speed=current_speed, 
            current_lane_index=current_lane_index, 
            current_road_id=current_road_id
        )