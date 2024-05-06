'''
@Author: WANG Maonan
@Date: 2023-08-28 19:13:31
@Description: 车辆控制基类
@LastEditTime: 2024-05-05 15:14:33
'''
from loguru import logger
from abc import ABC, abstractmethod

class VehicleAction(ABC):
    def __init__(self, id, vehicle_type, sumo) -> None:
        super().__init__()
        self.veh_id = id
        self.sumo = sumo

        # 如果是 ego 车辆, 那么可以自由控制对应的速度, 不受到 car-following 的限制
        # speed mode: https://sumo.dlr.de/docs/TraCI/Change_Vehicle_State.html#speed_mode_0xb3
        # lane change mode: https://sumo.dlr.de/docs/TraCI/Change_Vehicle_State.html#lane_change_mode_0xb6
        # Collisions: https://sumo.dlr.de/docs/Simulation/Safety.html#collisions, 发生碰撞之后车辆消失, 还是继续仿真
        if 'ego' in vehicle_type:
            self.sumo.vehicle.setSpeedMode(self.veh_id, 0)
            logger.info(f"SIM: Set {self.veh_id} speedmode to 0.")
            self.sumo.vehicle.setLaneChangeMode(self.veh_id, 1109)
            logger.info(f"SIM: Set {self.veh_id} lanechangemode to 1109 (0b010001010101).")


    @abstractmethod
    def execute(self) -> None:
        pass

    def change_lane(self, lane_change:int, 
                    current_lane:int, current_edge:str) -> None:
        if current_edge.startswith(":"):
            logger.info(f'SIM: {self.veh_id} in connection edge {current_edge}.')
        else:
            target_lane = current_lane + lane_change
            lane_number = self.sumo.edge.getLaneNumber(current_edge) # 获得 edge 的 lane 的个数
            if target_lane >= 0 and target_lane < lane_number:
                self.sumo.vehicle.changeLane(self.veh_id, target_lane, duration=1)
            else:
                logger.info(f'SIM: Target Lane is: {target_lane}; Exceed to Lanes in this Edge: {lane_number}; Keep Current Lane: {current_lane}.')
                self.sumo.vehicle.changeLane(self.veh_id, current_lane, duration=1)