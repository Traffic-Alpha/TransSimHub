'''
@Author: WANG Maonan
@Date: 2023-08-28 18:24:56
@Description: 变车道+连续速度控制
@LastEditTime: 2023-08-28 20:12:21
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

    def execute(self, lane_change:int, target_speed:float):
        lane_change = LaneChangeActionType(lane_change)
        if lane_change == LaneChangeActionType.keep_lane:
            self.change_lane(0)
        elif lane_change == LaneChangeActionType.change_lane_left:
            self.change_lane(-1)
        elif lane_change == LaneChangeActionType.change_lane_right:
            self.change_lane(1)
        self.sumo.vehicle.slowDown(self.veh_id, target_speed, duration=1)
