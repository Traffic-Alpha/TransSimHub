'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: 运动学模型 (无惯性), 飞行器默认动力学.

速度瞬间等于目标速度, 位置按速度积分:
    new_velocity = velocity_command
    new_position = position + new_velocity * dt

当 dt=1.0 时, 与历史实现 `new_position = position + speed * heading` 完全一致,
因此作为默认动力学可保证向后兼容.
@LastEditTime: 2026-06-01 00:00:00
'''
from typing import List, Tuple

from .base_dynamics import AircraftDynamics, Vector3


class KinematicDynamics(AircraftDynamics):
    def step(self,
             position: Vector3, velocity: Vector3,
             velocity_command: Vector3, dt: float
        ) -> Tuple[List[float], List[float]]:
        new_velocity = list(velocity_command)
        new_position = [
            position[0] + new_velocity[0] * dt,
            position[1] + new_velocity[1] * dt,
            position[2] + new_velocity[2] * dt,
        ]
        return self._apply_ground_constraint(position, new_position, new_velocity)
