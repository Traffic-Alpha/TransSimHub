'''
@Author: WANG Maonan
@Date: 2023-08-29 20:18:04
@Description: Base Aircraft Action
@LastEditTime: 2023-08-30 18:18:56
'''
from loguru import logger
from typing import Tuple
from abc import ABC, abstractmethod

class AircraftAction(ABC):
    def __init__(self, id) -> None:
        super().__init__()
        self.aircraft_id = id

    @abstractmethod
    def execute(self) -> None:
        pass

    def calculate_new_position(self, 
                               position:Tuple[float, float, float], 
                               speed: float, heading:Tuple[float, float, float]
                            ) -> Tuple[float, float, float]:
        new_position = [
            position[0] + speed * heading[0],
            position[1] + speed * heading[1],
            position[2] + speed * heading[2]
        ]
        if new_position[2] <= 0:
            logger.warning(f'SIM: Aircraft 的高度不能小于 0, 现在高度为 {new_position[2]}.')
            logger.warning('SIM: Aircraft 的位置不变.')
            new_position[2] = position[2] # 保持原来的高度不变
        return new_position