'''
@Author: WANG Maonan
@Date: 2026-08-15
@Description: 仿真状态 -> 渲染器无关的场景数据.

- scene_elements: 数据结构 (ObjectPose / SceneFrame / SceneStatic);
- scene_builder : 从 tshub 观测构建这些数据 (build_frame / build_tls_rigs) 与配置校验.
@LastEditTime: 2026-08-15
'''
from .scene_elements import ObjectPose, SceneFrame, SceneStatic
from .scene_builder import (
    build_frame, build_tls_rigs, validate_sensor_config, VALID_SENSORS,
)

__all__ = [
    'ObjectPose', 'SceneFrame', 'SceneStatic',
    'build_frame', 'build_tls_rigs', 'validate_sensor_config', 'VALID_SENSORS',
]
