'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: 点质量双积分器 (L2 物理模型).

将 velocity_command 视为「目标速度」, 通过有界加速度逼近, 从而引入惯性:
    a_des = (velocity_command - velocity) / dt   # 一步到位所需加速度
    a     = clip_norm(a_des, max_accel)          # 限制最大加速度
    v_new = clip_norm(velocity + a * dt, max_speed)
    (可选) 限制垂直速度 |vz| <= max_climb_rate
    (可选) 叠加恒定风速 wind
    p_new = position + v_new * dt

相比运动学模型, 飞行器不能瞬间改变速度, 转向/加减速更平滑, 对强化学习控制更友好.
@LastEditTime: 2026-06-01 00:00:00
'''
from typing import List, Tuple

from loguru import logger
from .base_dynamics import AircraftDynamics, Vector3


class PointMassDynamics(AircraftDynamics):
    def __init__(self,
                 max_speed: float = 20.0,
                 max_accel: float = 5.0,
                 max_climb_rate: float = None,
                 wind: Vector3 = (0.0, 0.0, 0.0)
        ) -> None:
        """
        Args:
            max_speed (float): 最大速度模长 (m/s). Defaults to 20.0.
            max_accel (float): 最大加速度模长 (m/s^2). Defaults to 5.0.
            max_climb_rate (float, optional): 最大垂直速度 (m/s), None 表示不限制. Defaults to None.
            wind (Vector3): 恒定风速向量 (m/s), 直接叠加到速度上. Defaults to (0, 0, 0).
        """
        self.max_speed = max_speed
        self.max_accel = max_accel
        self.max_climb_rate = max_climb_rate
        self.wind = wind

    def step(self,
             position: Vector3, velocity: Vector3,
             velocity_command: Vector3, dt: float
        ) -> Tuple[List[float], List[float]]:
        if dt <= 0:
            raise ValueError(f'SIM: Aircraft dynamics dt 必须为正数, 当前为 {dt}.')

        # 1. 计算受限加速度并积分得到新速度
        a_des = [(velocity_command[i] - velocity[i]) / dt for i in range(3)]
        a = self._clip_norm(a_des, self.max_accel)
        v_new = [velocity[i] + a[i] * dt for i in range(3)]

        # 2. 限制最大速度
        v_new = self._clip_norm(v_new, self.max_speed)

        # 3. 限制垂直爬升/下降速度
        if self.max_climb_rate is not None:
            v_new[2] = max(-self.max_climb_rate, min(self.max_climb_rate, v_new[2]))

        # 4. 叠加风速
        v_new = [v_new[i] + self.wind[i] for i in range(3)]

        # 5. 按新速度积分位置
        new_position = [position[i] + v_new[i] * dt for i in range(3)]

        new_position, v_new = self._apply_ground_constraint(position, new_position, v_new)
        if new_position[2] == position[2] and velocity_command[2] < 0:
            logger.warning(f'SIM: Aircraft 触地 (高度 {position[2]}), 垂直方向停止下降.')
        return new_position, v_new
