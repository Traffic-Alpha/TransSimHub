'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: 渲染器无关的场景描述层 (Renderer-agnostic scene layer).

把「场景里有什么 (SceneFrame / SceneStatic)」与「用什么渲染 (RendererBackend)」解耦:
- SUMO/tshub 状态 -> SceneFrame (纯数据, 不含任何 panda3d/blender 依赖)
- 各渲染后端 (Panda3D / 未来的 PyTorch3D 等) 实现 RendererBackend, 消费 SceneFrame 出图
@LastEditTime: 2026-06-01 00:00:00
'''
from .scene_elements import ObjectPose, SceneFrame, SceneStatic, RendererBackend
from .scene_builder import build_frame, build_tls_rigs, validate_sensor_config, VALID_SENSORS
from .sensor_rig import (
    CameraRig, CAMERA_RIGS, BASE_CAMERA_RIGS, get_camera_rig, compute_camera_pose,
)
from .vehicle_models import select_vehicle_model_name, vehicle_models_dir
from .aircraft_models import select_aircraft_model_name, aircraft_models_dir
from .seg_classes import (
    SEG_CLASSES, SEG_NAME_TO_ID, SEG_ID_TO_NAME, SEG_ID_TO_COLOR,
    SEG_NAME_TO_COLOR, SEG_RENDER_COLORS, seg_color_to_label, seg_label_to_color,
)

__all__ = [
    'ObjectPose', 'SceneFrame', 'SceneStatic', 'RendererBackend',
    'build_frame', 'build_tls_rigs', 'validate_sensor_config', 'VALID_SENSORS',
    'CameraRig', 'CAMERA_RIGS', 'BASE_CAMERA_RIGS', 'get_camera_rig', 'compute_camera_pose',
    'select_vehicle_model_name', 'vehicle_models_dir',
    'select_aircraft_model_name', 'aircraft_models_dir',
    'SEG_CLASSES', 'SEG_NAME_TO_ID', 'SEG_ID_TO_NAME', 'SEG_ID_TO_COLOR',
    'SEG_NAME_TO_COLOR', 'SEG_RENDER_COLORS', 'seg_color_to_label', 'seg_label_to_color',
]
