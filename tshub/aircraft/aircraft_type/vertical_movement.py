'''
@Author: WANG Maonan
@Date: 2023-08-29 18:11:22
@Description: 飞翔器垂直方向移动
@LastEditTime: 2023-08-29 20:44:33
'''
from typing import Tuple
from .base_aircraft_action import AircraftAction

class VerticalMovementAction(AircraftAction):
    HEADINGS = {
        0: (0, 0, 0),    # No change
        1: (0, 0, 1),    # Upward movement
        2: (0, 0, -1)    # Downward movement
    }

    def __init__(self, id) -> None:
        super().__init__(id)

    def execute(self, position:Tuple[float, float, float], 
                speed: float, heading_index: int) -> None:
        heading = self.HEADINGS[heading_index]
        new_position = self.calculate_new_position(position=position, speed=speed, heading=heading)
        return new_position

