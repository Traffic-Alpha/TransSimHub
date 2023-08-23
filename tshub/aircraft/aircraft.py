'''
@Author: WANG Maonan
@Date: 2023-08-23 20:13:01
@Description: Aircraft Infomation
@LastEditTime: 2023-08-23 21:15:13
'''
from dataclasses import dataclass
from typing import Tuple

@dataclass
class AircraftInfo:
    id: str
    position: tuple[float, float, float]
    speed: tuple[float, float, float]
    heading: tuple[float, float, float]
    communication_range: float

    @classmethod
    def create(cls, 
            id:str, 
            position: Tuple[float, float, float], 
            speed: float, 
            heading: Tuple[float, float, float], 
            communication_range: float
        ):
        """
        创建 AircraftInfo 实例。

        Args:
            id (str): aircraft ID。
            position (Tuple[float, float, float]): aircraft 的位置坐标。
            speed (float): aircraft 的速度。
            heading (Tuple[float, float, float]): aircraft 的航向。
            communication_range (float): aircraft 的通信范围。

        Returns:
            AircraftInfo: 创建的 AircraftInfo 实例。
        """
        return cls(id, position, speed, heading, communication_range)
