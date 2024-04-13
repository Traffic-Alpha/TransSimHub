'''
@Author: WANG Maonan
@Date: 2023-08-28 18:24:40
@Description: 车辆离散动作,
keep_lane: 保持车道, 加速
slow_down: 保持车道, 减速
change_lane_left: 向左变车道
change_lane_right: 向右变车道
@LastEditTime: 2024-04-13 17:11:56
'''
import enum
from .base_vehicle_action import VehicleAction

class LaneActionType(enum.Enum):
    keep_lane = 0
    slow_down = 1
    change_lane_left = 2
    change_lane_right = 3

class LaneAction(VehicleAction):
    def __init__(self, id, vehicle_type, sumo) -> None:
        super().__init__(id, vehicle_type, sumo)

    def execute(self, lane_change:int, target_speed:float, 
                current_speed:float, current_lane_index:int, current_road_id:str) -> None:
        action = LaneActionType(lane_change)
        if action == LaneActionType.keep_lane:
            target_speed = min(current_speed + 3, 15) # 15m/s -- 54km/h
            self.sumo.vehicle.slowDown(self.veh_id, target_speed, duration=1)
        elif action == LaneActionType.slow_down:
            target_speed = max(current_speed - 3, 2)
            self.sumo.vehicle.slowDown(self.veh_id, target_speed, duration=1)
        elif action == LaneActionType.change_lane_left:
            target_speed = max(current_speed - 2, 2)
            self.sumo.vehicle.slowDown(self.veh_id, target_speed, duration=1)
            self.change_lane(-1, current_lane=current_lane_index, current_edge=current_road_id)
        elif action == LaneActionType.change_lane_right:
            target_speed = max(current_speed - 2, 2)
            self.sumo.vehicle.slowDown(self.veh_id, target_speed, duration=1)
            self.change_lane(1, current_lane=current_lane_index, current_edge=current_road_id)
