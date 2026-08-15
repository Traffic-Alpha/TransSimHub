'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: 飞行器动力学 (Dynamics) 基类

将「动作 (Action)」与「动力学 (Dynamics)」解耦:
- Action  : (speed, heading_index) -> velocity_command (目标速度向量, m/s), 只负责动作空间;
- Dynamics: (position, velocity, velocity_command, dt) -> (new_position, new_velocity), 只负责状态如何演化.

这样可以独立替换运动学/物理模型, 而不改动动作空间.
@LastEditTime: 2026-06-01 00:00:00
'''
import math
from abc import ABC, abstractmethod
from typing import List, Sequence, Tuple

Vector3 = Sequence[float]


class AircraftDynamics(ABC):
    @abstractmethod
    def step(self,
             position: Vector3, velocity: Vector3,
             velocity_command: Vector3, dt: float
        ) -> Tuple[List[float], List[float]]:
        """根据目标速度 velocity_command 推进一步, 更新飞行器状态.

        Args:
            position (Vector3): 当前位置 (x, y, z).
            velocity (Vector3): 当前速度 (vx, vy, vz), m/s.
            velocity_command (Vector3): Action 给出的目标速度 (vx, vy, vz), m/s.
            dt (float): 时间步长, 秒.

        Returns:
            (new_position, new_velocity)
        """
        raise NotImplementedError

    @staticmethod
    def _norm(vec: Vector3) -> float:
        return math.sqrt(vec[0] * vec[0] + vec[1] * vec[1] + vec[2] * vec[2])

    @classmethod
    def _clip_norm(cls, vec: Vector3, max_norm: float) -> List[float]:
        """将向量模长限制在 max_norm 以内 (max_norm 为 None 时不限制)."""
        if max_norm is None:
            return list(vec)
        n = cls._norm(vec)
        if n > max_norm and n > 0:
            scale = max_norm / n
            return [c * scale for c in vec]
        return list(vec)

    @staticmethod
    def _apply_ground_constraint(prev_position: Vector3,
                                 new_position: List[float],
                                 new_velocity: List[float]
        ) -> Tuple[List[float], List[float]]:
        """飞行器高度不能小于 0; 触地时保持原高度, 垂直速度清零."""
        if new_position[2] <= 0:
            new_position[2] = prev_position[2]
            new_velocity[2] = 0.0
        return new_position, new_velocity
