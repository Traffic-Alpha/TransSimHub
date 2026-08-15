'''
@Author: WANG Maonan
@Date: 2023-08-29 20:18:04
@Description: Base Aircraft Action

Action 只负责动作空间: 将 (speed, heading_index) 映射为目标速度向量 velocity_command.
状态如何随该指令演化交由 dynamics (tshub.aircraft.dynamics) 处理.
@LastEditTime: 2026-06-01 00:00:00
'''
from typing import Tuple
from abc import ABC, abstractmethod


class AircraftAction(ABC):
    def __init__(self, id) -> None:
        super().__init__()
        self.aircraft_id = id

    @abstractmethod
    def execute(self, speed: float, heading_index: int) -> Tuple[float, float, float]:
        """将 (speed, heading_index) 映射为目标速度向量 (vx, vy, vz)."""
        raise NotImplementedError

    @staticmethod
    def _scale(unit_heading: Tuple[float, float, float], speed: float) -> Tuple[float, float, float]:
        """目标速度 = 速度大小 * 单位航向向量."""
        return (speed * unit_heading[0], speed * unit_heading[1], speed * unit_heading[2])
