'''
@Author: WANG Maonan
@Date: 2023-08-28 19:13:31
@Description: 车辆控制基类
@LastEditTime: 2023-11-22 13:15:16
'''
from loguru import logger
from abc import ABC, abstractmethod

class VehicleAction(ABC):
    def __init__(self, id, sumo) -> None:
        super().__init__()
        self.veh_id = id
        self.sumo = sumo

    @abstractmethod
    def execute(self) -> None:
        pass

    def change_lane(self, lane_change:int, 
                    current_lane:int, current_edge:str) -> None:
        if current_edge.startswith(":"):
            logger.info(f'SIM: {self.veh_id} in connection edge {current_edge}.')
        else:
            target_lane = current_lane + lane_change
            if target_lane >= 0 and target_lane < self.sumo.edge.getLaneNumber(current_edge):
                self.sumo.vehicle.changeLane(self.veh_id, target_lane, duration=1)