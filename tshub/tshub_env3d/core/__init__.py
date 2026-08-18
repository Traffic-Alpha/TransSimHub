'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: tshub_env3d 的核心定义层 (渲染器无关, 不 import panda3d / bpy).

这里是「仿真」与「渲染」之间的契约: Tshub3DEnvironment 每一步都要用到, 各渲染后端
(Panda 在线 / Blender 离线) 也都消费同一份定义, 保证两条路径可比. 按职责分子包:
- state/           : 仿真状态 -> 场景数据 (SceneFrame / SceneStatic / build_frame ...)
- sensors/         : 传感器定义 (相机 rig、语义分割类别与调色板)
- models/          : 物体类型 -> 3D 模型 (车辆 / 飞行器)
- export/          : 把一局仿真导出成剧集 JSON, 供离线 Blender 渲染
- utils/           : 坐标 / 数学等纯工具
- renderer_backend : 渲染后端需要实现的接口

对照另外两个包: `scene/` 负责「生成」静态场景产物 (glb / .blend),
`renderers/` 负责「渲染」.

本文件保持扁平的对外 API (`from tshub.tshub_env3d.core import X`), 上层代码
无需关心内部分包.
@LastEditTime: 2026-08-17
'''
from .renderer_backend import RendererBackend
from .state import (
    ObjectPose, SceneFrame, SceneStatic,
    build_frame, build_tls_rigs, validate_sensor_config, VALID_SENSORS,
)
from .sensors import (
    CameraRig, CAMERA_RIGS, BASE_CAMERA_RIGS, get_camera_rig, compute_camera_pose,
    SEG_CLASSES, SEG_NAME_TO_ID, SEG_ID_TO_NAME, SEG_ID_TO_COLOR,
    SEG_NAME_TO_COLOR, SEG_RENDER_COLORS, seg_color_to_label, seg_label_to_color,
)
from .models import (
    select_vehicle_model_name, vehicle_models_dir,
    select_aircraft_model_name, aircraft_models_dir,
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
