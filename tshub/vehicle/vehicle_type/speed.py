'''
@Author: WANG Maonan
@Date: 2024-08-11 18:38:39
@Description: 控制速度, 变道由 SUMO 控制
@LastEditTime: 2024-08-11 19:35:01
'''
import enum
from loguru import logger
from .base_vehicle_action import VehicleAction

class SpeedActionType(enum.Enum):
    accelerate = 0 # 加速
    decelerate = 1 # 减速
    maintain_speed = 2 # 保持不变

class SpeedAction(VehicleAction):
    def __init__(self, id, vehicle_type, sumo) -> None:
        super().__init__(id, vehicle_type, sumo)

    def execute(self, 
                current_speed: float, speed_action: SpeedActionType,
                acceleration_rate:float=2, # m/s
                *args, **kwargs,
        ) -> None:
        action = SpeedActionType(speed_action)
        # Speed control logic
        if action == SpeedActionType.accelerate:
            new_speed = current_speed + acceleration_rate
            logger.info(f'SIM: 车辆 {self.veh_id} 加速到 {new_speed}.')
            self.sumo.vehicle.setSpeed(self.veh_id, new_speed)
        elif action == SpeedActionType.decelerate:
            new_speed = max(1, current_speed - acceleration_rate)  # Prevent negative speed
            logger.info(f'SIM: 车辆 {self.veh_id} 减速到 {new_speed}.')
            self.sumo.vehicle.setSpeed(self.veh_id, new_speed)
        elif action == SpeedActionType.maintain_speed:
            # No change to the vehicle's speed
            pass
        else:
            logger.debug(f'SIM: SUMO Speed Action Unknown')
