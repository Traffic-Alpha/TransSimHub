'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: 飞行器动力学 (Dynamics) 工厂.

动力学决定「指令如何转化为状态变化」, 与动作空间 (aircraft_type) 解耦:
- 'kinematic'  : 运动学模型, 无惯性 (默认, 向后兼容);
- 'point_mass' : 点质量双积分器, 含惯性与 v_max / a_max / 风等约束.
@LastEditTime: 2026-06-01 00:00:00
'''
from typing import Any, Dict

from .base_dynamics import AircraftDynamics
from .kinematic import KinematicDynamics
from .point_mass import PointMassDynamics

DYNAMICS_REGISTRY = {
    'kinematic': KinematicDynamics,
    'point_mass': PointMassDynamics,
}


def create_dynamics(dynamics_type: str = 'kinematic',
                    dynamics_params: Dict[str, Any] = None) -> AircraftDynamics:
    """根据类型创建动力学实例.

    Args:
        dynamics_type (str): 动力学类型, 见 DYNAMICS_REGISTRY. Defaults to 'kinematic'.
        dynamics_params (Dict[str, Any], optional): 传给动力学构造函数的参数. Defaults to None.
    """
    if dynamics_type not in DYNAMICS_REGISTRY:
        raise ValueError(
            f"Unknown aircraft dynamics '{dynamics_type}', "
            f"choose from {list(DYNAMICS_REGISTRY)}."
        )
    return DYNAMICS_REGISTRY[dynamics_type](**(dynamics_params or {}))
