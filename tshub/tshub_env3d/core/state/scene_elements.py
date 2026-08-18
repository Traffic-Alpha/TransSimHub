'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: 渲染器无关的场景描述数据结构.

这些类型不依赖任何具体渲染引擎 (无 panda3d / blender import), 是 tshub 状态
与渲染后端之间的契约:
- ObjectPose : 单个可渲染物体的位姿 (车辆 / 飞行器);
- SceneFrame : 某一仿真步的全量快照 (当前所有车辆与飞行器);
- SceneStatic: 一局仿真中不变的场景信息 (地图 glb 目录、传感器配置、路口相机 rig).
消费这些数据的后端接口见 scene/renderer_backend.py.
@LastEditTime: 2026-08-15
'''
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


@dataclass
class ObjectPose:
    """单个可渲染物体在某一帧的位姿信息.

    heading 的格式按 category 而定, 与各渲染元素 update_node 的期望保持一致:
    - vehicle : 沿用 SUMO/tshub 观测中的原始 heading;
    - aircraft: 已转换为角度 (degrees, 0~360).
    """
    object_id: str
    category: str # 'vehicle' | 'aircraft'
    position: Tuple[float, float, float]
    heading: Any
    object_type: str = None # 车辆类型 (vehicle_type), 用于选择 3D 模型
    length: float = None # 车辆长度


@dataclass
class SceneFrame:
    """某一仿真步的场景全量快照 (渲染器无关).

    采用「全量快照」而非「增量」: 每帧给后端当前所有物体, 由后端自行与其节点缓存对账
    (新建 / 更新 / 移除), 这样接口最简单, 生命周期由后端各自管理.
    """
    vehicles: Dict[str, ObjectPose] = field(default_factory=dict)
    aircraft: Dict[str, ObjectPose] = field(default_factory=dict)


@dataclass
class SceneStatic:
    """一局仿真中不变的场景信息 (reset 时构建一次).

    Attributes:
        scenario_glb_dir: 场景 3D 模型 (glb) 所在目录.
        sensor_config: 各 object 挂载哪些传感器 (来自用户配置, 渲染器无关).
        tls_rigs: 每个路口相机的位姿/参数, 见 build_tls_rigs 的返回值.
    """
    scenario_glb_dir: str = None
    sensor_config: Dict[str, Any] = field(default_factory=dict)
    tls_rigs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
