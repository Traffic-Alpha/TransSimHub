'''
@Author: WANG Maonan
@Date: 2023-08-29 18:11:40
@Description: 飞翔器水平和垂直同时移动
@LastEditTime: 2023-08-30 16:05:22
'''
import math
from typing import Tuple
from .base_aircraft_action import AircraftAction

class CombinedMovementAction(AircraftAction):
    def __init__(self, id) -> None:
        super().__init__(id)
        AZIMUTHS = [0, 45, 90, 135, 180, 225, 270, 315]  # Eight discrete azimuth angles
        ELEVATIONS = [-90, -45, 0, 45, 90]  # Five discrete elevation angles
        self.combinations = [(azimuth, elevation) 
                        for azimuth in AZIMUTHS 
                        for elevation in ELEVATIONS
                    ]

    def execute(self, 
                position:Tuple[float, float, float], 
                speed: float, heading_index: int) -> None:
        heading_combinations = self.combinations[heading_index]
        heading = self.calculate_heading_3d(*heading_combinations)
        new_position = self.calculate_new_position(position=position, speed=speed, heading=heading)
        return new_position, heading

    def calculate_heading_3d(self, azimuth:float, elevation:float) -> Tuple[float, float, float]:
        # 将方位角和俯仰角转换为弧度
        azimuth_rad = math.radians(azimuth)
        elevation_rad = math.radians(elevation)

        # 计算 heading 向量的 x、y 和 z 分量
        x = math.cos(azimuth_rad) * math.cos(elevation_rad)
        y = math.sin(azimuth_rad) * math.cos(elevation_rad)
        z = math.sin(elevation_rad)

        # 返回 heading 向量作为一个包含 x、y 和 z 分量的元组
        return (x, y, z)
