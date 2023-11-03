'''
@Author: WANG Maonan
@Date: 2023-08-28 18:24:56
@Description: 变车道+连续速度控制
@LastEditTime: 2023-11-03 17:34:13
'''
import enum
from .base_vehicle_action import VehicleAction

class LaneChangeActionType(enum.Enum):
    keep_lane = 0
    change_lane_left = 1
    change_lane_right = 2

class LaneWithContinuousSpeedAction(VehicleAction):
    def __init__(self, id, sumo) -> None:
        super().__init__(id, sumo)

    def execute(self, lane_change:int, target_speed:float, 
                current_speed:float, current_lane_index:int, current_road_id:str) -> None:
        lane_change = LaneChangeActionType(lane_change)
        if lane_change == LaneChangeActionType.keep_lane:
            self.change_lane(0, current_lane=current_lane_index, current_edge=current_road_id)
        elif lane_change == LaneChangeActionType.change_lane_left:
            self.change_lane(-1, current_lane=current_lane_index, current_edge=current_road_id)
        elif lane_change == LaneChangeActionType.change_lane_right:
            self.change_lane(1, current_lane=current_lane_index, current_edge=current_road_id)
        if target_speed != -1: # If we set target speed to -1, then speed of the vehicle will not change
            self.sumo.vehicle.slowDown(self.veh_id, target_speed, duration=1)
