'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: 渲染器无关的「相机 rig」规格 (carrier-mounted camera spec).

把"相机挂在哪个载体上、相对位姿、fov、可见性(mask)"从具体渲染器中抽出来,
做成声明式数据 + 一个把 (载体世界位姿 + rig) 算成 (eye, target) 世界坐标的纯函数,
这样各渲染后端共用同一套相机定义, 不必各自硬编码.

坐标约定: 世界坐标为 tshub/SUMO 系 (x, y 为地面, z 为高度, heading 为角度).
各后端再把 (eye, target) 转换到自己的坐标系 (例如 Y-up 的后端).
@LastEditTime: 2026-06-01 00:00:00
'''
import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

Vec3 = Tuple[float, float, float]


@dataclass(frozen=True)
class CameraRig:
    """一个挂载在载体上的相机的渲染器无关规格.

    几何 (非俯视): 相机置于载体沿"看向"方向后退 pull_back 处、高度 height,
    注视点在载体前方 look_distance 处、高度 look_height. "看向"方向 = 载体
    heading + yaw_offset_deg. 俯视相机 (top_down) 则垂直向下看载体正下方.
    """
    name: str # 基础相机名, 如 'front_left' / 'junction_front' / 'bev'
    carrier: str # 'vehicle' | 'tls' | 'aircraft'
    yaw_offset_deg: float = 0.0 # 看向相对载体 heading 的偏转
    pull_back: float = 0.0 # 相机相对载体沿看向反方向后退的距离; 负值表示向看向方向前移
    look_distance: float = 10.0 # 注视点相对载体沿看向前方的距离
    height: float = 2.0 # 相机相对载体的高度偏移 (tls 用 rig 的 tls_camera_height 覆盖)
    look_height: float = 1.0 # 注视点高度 (相对载体; top_down 时为绝对地面高度)
    look_height_frac: float = None # 若设置, 注视点高度 = 相机高度 * 该比例 (路口相机用 1/3)
    pitch_deg: float = 0.0 # 俯仰角 (>0 向前下方看, 用于无人机 FPV 斜视)
    top_down: bool = False # 是否俯视 (bev / aircraft)
    fov_deg: float = 90.0
    ortho_size: Optional[float] = None # 俯视正交镜头覆盖的纵向世界尺寸 (米)
    modality: str = 'rgb' # 'rgb' (正常出图, H×W×3) | 'seg' (语义分割, 每类一个标签色 -> H×W label-id)
    set_heading: bool = False # 渲染时是否在 lookAt 后把相机水平朝向对齐到 (载体航向+yaw_offset)。
                              # 主要用于 top-down 车载 BEV, 让图像上方稳定对齐车头。
    body_clearance: float = 0.25 # 车载透视相机离开车辆包围盒后的额外安全距离。


# 基础相机几何 (modality 维度在下方按 _rgb / _seg 自动展开)
_BASE_RIGS = {
    # --- 车载 6 向 (由 eye/target 决定朝向; perspective 相机不再额外 setH) ---
    'front': CameraRig(
        'front', 'vehicle',
        yaw_offset_deg=0, pull_back=-1.8, look_distance=25,
        height=1.35, look_height=1.15, fov_deg=65,
    ),
    'front_left': CameraRig(
        'front_left', 'vehicle',
        yaw_offset_deg=-30, pull_back=-1.8, look_distance=25,
        height=1.35, look_height=1.15, fov_deg=65,
    ),
    'front_right': CameraRig(
        'front_right', 'vehicle',
        yaw_offset_deg=+30, pull_back=-1.8, look_distance=25,
        height=1.35, look_height=1.15, fov_deg=65,
    ),
    'back': CameraRig(
        'back', 'vehicle',
        yaw_offset_deg=180, pull_back=-1.8, look_distance=18,
        height=1.35, look_height=1.15, fov_deg=70,
    ),
    'back_left': CameraRig(
        'back_left', 'vehicle',
        yaw_offset_deg=150, pull_back=-1.8, look_distance=18,
        height=1.35, look_height=1.15, fov_deg=70,
    ),
    'back_right': CameraRig(
        'back_right', 'vehicle',
        yaw_offset_deg=210, pull_back=-1.8, look_distance=18,
        height=1.35, look_height=1.15, fov_deg=70,
    ),
    # --- 车载鸟瞰 (top_down 但仍 setH 使图像上方对齐车头) ---
    'bev': CameraRig(
        'bev', 'vehicle',
        height=35, look_height=0, top_down=True, ortho_size=42, set_heading=True,
    ),
    # --- 路口 (挂在 tls 停车线; front 看向 incoming 上游车辆, back 看向路口内侧) ---
    'junction_front': CameraRig(
        'junction_front', 'tls',
        yaw_offset_deg=180, pull_back=12, look_distance=20,
        height=9, look_height=0.8, fov_deg=50,
    ),
    'junction_back': CameraRig(
        'junction_back', 'tls',
        yaw_offset_deg=0, pull_back=0, look_distance=18,
        height=8, look_height=3.0, fov_deg=55,
    ),
    # --- 路口俯视 (一个路口一个, 架在整个交叉口中心正上方往下看全路口; 高度由 junction_bev_height 给出) ---
    'junction_bev': CameraRig(
        'junction_bev', 'tls',
        top_down=True, look_height=0, ortho_size=90,
    ),
    # --- 飞行器俯视 (相机置于飞行器处, 高度偏移 0, 看正下方地面) ---
    'aircraft': CameraRig(
        'aircraft', 'aircraft',
        height=0, look_height=0, top_down=True, ortho_size=80,
    ),
    # --- 飞行器前下斜视 (FPV: 沿飞行方向看前下方, 穿梭于建筑之间的感觉) ---
    'aircraft_front': CameraRig(
        'aircraft_front', 'aircraft',
        height=0, look_distance=55, pitch_deg=25, fov_deg=65,
    ),
    # --- 飞行器外部跟拍 (可看到飞行器本体与前方场景, 用于穿梭展示) ---
    'aircraft_chase': CameraRig(
        'aircraft_chase', 'aircraft',
        pull_back=30, height=10, look_distance=8,
        look_height=2.2, fov_deg=60,
    ),
}

# 基础相机几何 (base name -> CameraRig), 供后端按相机几何引用 (可见性无关)
BASE_CAMERA_RIGS: Dict[str, CameraRig] = dict(_BASE_RIGS)

# sensor_type 字符串 -> CameraRig (展开 _rgb / _seg 两种模态)
from dataclasses import replace
CAMERA_RIGS: Dict[str, CameraRig] = {}
for _base, _rig in _BASE_RIGS.items():
    CAMERA_RIGS[f'{_base}_rgb'] = replace(_rig, name=f'{_base}_rgb', modality='rgb')
    CAMERA_RIGS[f'{_base}_seg'] = replace(_rig, name=f'{_base}_seg', modality='seg')


def get_camera_rig(sensor_type: str) -> CameraRig:
    """按 sensor_type (如 'front_left_all') 取相机 rig."""
    if sensor_type not in CAMERA_RIGS:
        raise KeyError(f"Unknown sensor_type '{sensor_type}'. Known: {sorted(CAMERA_RIGS)}")
    return CAMERA_RIGS[sensor_type]


def compute_camera_pose(rig: CameraRig,
                        carrier_xy: Tuple[float, float],
                        carrier_heading_deg: float,
                        height_override: float = None,
                        carrier_z: float = 0.0,
                        carrier_dimensions: Optional[Vec3] = None,
    ) -> Tuple[Vec3, Vec3]:
    """把载体世界位姿 + rig 算成 (eye, target) 世界坐标 (tshub/SUMO 系, z 为高度).

    Args:
        rig: 相机规格.
        carrier_xy: 载体 (x, y).
        carrier_heading_deg: 载体航向 (度).
        height_override: 覆盖相机高度偏移 (tls 用 rig 自带的 tls_camera_height).
        carrier_z: 载体自身高度 (车辆≈0, 飞行器为飞行高度).
        carrier_dimensions: 载体模型包围盒尺寸 (length, width, height). 车辆透视相机
            会用它把 eye 推到车体包围盒外, 避免相机落在车辆模型内部。
    Returns:
        (eye, target), 均为 (x, y, z).
    """
    cx, cy = float(carrier_xy[0]), float(carrier_xy[1])
    height = rig.height if height_override is None else float(height_override)
    eye_z = carrier_z + height

    if rig.top_down: # 俯视: 在载体正上方往正下方看 (注视点为绝对地面高度)
        return (cx, cy, eye_z), (cx, cy, rig.look_height)

    look_deg = carrier_heading_deg + rig.yaw_offset_deg
    rad = math.radians(look_deg)
    # Heading follows tshub/SMARTS convention: 0 deg points to +Y and
    # positive rotation turns counter-clockwise.
    dx, dy = -math.sin(rad), math.cos(rad)
    pull_back = rig.pull_back
    if rig.carrier == 'vehicle' and carrier_dimensions is not None:
        pull_back = _vehicle_safe_pull_back(rig, carrier_dimensions)
    eye = (cx - pull_back * dx, cy - pull_back * dy, eye_z)
    if rig.pitch_deg: # 前下斜视 (FPV): 注视点沿前方且按俯仰角下压
        pr = math.radians(rig.pitch_deg)
        horiz = rig.look_distance * math.cos(pr)
        target = (cx + horiz * dx, cy + horiz * dy, eye_z - rig.look_distance * math.sin(pr))
        return eye, target
    if rig.look_height_frac is not None:
        target_z = eye_z * rig.look_height_frac
    else:
        target_z = carrier_z + rig.look_height
    target = (cx + rig.look_distance * dx, cy + rig.look_distance * dy, target_z)
    return eye, target


def _vehicle_safe_pull_back(rig: CameraRig, dimensions: Vec3) -> float:
    """Keep exterior vehicle cameras outside the vehicle model footprint.

    Negative ``pull_back`` means the eye is moved forward along the viewing ray.
    The existing vehicle perspective rigs use that convention.  For those rigs,
    enforce at least the distance from the vehicle center to the rectangular
    footprint boundary along the ray, plus ``body_clearance``.
    """
    if rig.top_down or rig.pull_back >= 0:
        return rig.pull_back

    length, width, _height = (float(v) for v in dimensions)
    if length <= 0 or width <= 0:
        return rig.pull_back

    half_length = length * 0.5
    half_width = width * 0.5
    yaw = math.radians(rig.yaw_offset_deg)
    forward_component = abs(math.cos(yaw))
    lateral_component = abs(math.sin(yaw))
    candidates = []
    if forward_component > 1e-6:
        candidates.append(half_length / forward_component)
    if lateral_component > 1e-6:
        candidates.append(half_width / lateral_component)
    if not candidates:
        return rig.pull_back

    boundary_distance = min(candidates)
    safe_distance = boundary_distance + max(0.0, rig.body_clearance)
    current_distance = -rig.pull_back
    if current_distance >= safe_distance:
        return rig.pull_back
    return -safe_distance
