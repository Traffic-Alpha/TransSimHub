'''
@Author: WANG Maonan
@Date: 2023-08-28 19:13:31
@Description: 车辆控制基类
@LastEditTime: 2023-08-28 20:14:40
'''
from abc import ABC, abstractmethod

class VehicleAction(ABC):
    def __init__(self, id, sumo) -> None:
        super().__init__()
        self.veh_id = id
        self.sumo = sumo

    @abstractmethod
    def execute(self, action_id) -> None:
        pass

    def change_lane(self, lane_change) -> bool:
        current_lane = self.sumo.vehicle.getLaneIndex(self.veh_id)
        current_edge = self.sumo.vehicle.getRoadID(self.veh_id)
        target_lane = current_lane + lane_change
        if target_lane >= 0 and target_lane < self.sumo.edge.getLaneNumber(current_edge):
            self.sumo.vehicle.changeLane(self.veh_id, target_lane, duration=1)
            return True
        return False