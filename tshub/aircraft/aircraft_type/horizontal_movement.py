'''
@Author: WANG Maonan
@Date: 2023-08-29 18:11:04
@Description: 飞翔器水平方向移动, 不能垂直移动
@LastEditTime: 2023-08-29 20:44:28
'''
import math
from typing import Tuple
from .base_aircraft_action import AircraftAction

class HorizontalMovementAction(AircraftAction):
    ANGLES = [0, 45, 90, 135, 180, 225, 270, 315]  # Eight discrete angles

    def __init__(self, id, ) -> None:
        super().__init__(id)

    def execute(self, 
                position:Tuple[float, float, float], 
                speed: float, heading_index: int) -> None:
        heading_angle = self.ANGLES[heading_index]
        heading = self.calculate_heading(heading_angle)
        new_position = self.calculate_new_position(position=position, speed=speed, heading=heading)
        return new_position

    def calculate_heading(self, angle: float) -> Tuple[float, float, float]:
        # Convert the angle to radians
        angle_rad = math.radians(angle)

        # Calculate the heading vector components
        heading = (
            math.cos(angle_rad),
            math.sin(angle_rad),
            0  # Assuming no change in altitude for horizontal movement
        )

        return heading
