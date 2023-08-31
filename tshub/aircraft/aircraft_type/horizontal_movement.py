'''
@Author: WANG Maonan
@Date: 2023-08-29 18:11:04
@Description: 飞翔器水平方向移动, 不能垂直移动
@LastEditTime: 2023-08-30 15:27:51
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
        """
        Executes the horizontal movement action.

        Args:
            position (Tuple[float, float, float]): The current position of the aircraft.
            speed (float): The speed of the aircraft.
            heading_index (int): The index of the desired heading angle.

        Returns:
            Tuple[float, float, float]: The new position of the aircraft after the movement.
        """
        heading_angle = self.ANGLES[heading_index]
        heading = self.calculate_heading(heading_angle)
        new_position = self.calculate_new_position(position=position, speed=speed, heading=heading)
        return new_position, heading

    def calculate_heading(self, angle: float) -> Tuple[float, float, float]:
        """
        Calculates the heading vector based on the given angle.
        0 度：向右飞行: ->
        45 度：右上方飞行: ↗
        90 度：向上飞行: ↑
        135 度：左上方飞行: ↖
        180 度：向左飞行: <-
        225 度：左下方飞行: ↙
        270 度：向下飞行: ↓
        315 度：右下方飞行: ↘

        Args:
            angle (float): The angle in degrees.

        Returns:
            Tuple[float, float, float]: The heading vector components.
        """
        # Convert the angle to radians
        angle_rad = math.radians(angle)

        # Calculate the heading vector components
        heading = (
            math.cos(angle_rad),
            math.sin(angle_rad),
            0  # Assuming no change in altitude for horizontal movement
        )

        return heading
