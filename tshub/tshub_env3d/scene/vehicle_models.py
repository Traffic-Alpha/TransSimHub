'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: 渲染器无关的车辆 3D 模型选择 (veh_type -> glb 相对路径).

把"车辆类型映射到模型"的逻辑从具体渲染器中抽出来, 供各渲染后端共用,
避免各自维护一份映射. 仅依赖 random 与 get_abs_path, 不引入任何渲染引擎.

模型位于 _assets_3d/vehicles/<vehicles_low_poly|vehicles_high_poly>/<相对路径>.
@LastEditTime: 2026-07-11 17:43:01
'''
import random
from tshub.utils.get_abs_path import get_abs_path

_path_convert = get_abs_path(__file__) # 锚定在 scene/ 目录

# 特殊车辆类型 -> 模型相对路径 (event/ 障碍物暂用 crash_vehicle.glb)
_MODEL_MAPPING = {
    'ego': "ego/ego.glb",
    'police': "public_transport/police.glb",
    'emergency': "public_transport/emergency.glb",
    'fire_engine': "public_transport/fire_engine.glb",
    'taxi': "background/taxi.glb",
    'barrier_A': "event/barrier_A.glb",
    'barrier_B': "event/barrier_B.glb",
    'barrier_C': "event/barrier_C.glb",
    'barrier_D': "event/barrier_D.glb",
    'barrier_E': "event/barrier_E.glb",
    'tree_branch_1lane': "event/tree_branch_1lane.glb",
    'tree_branch_3lanes': "event/tree_branch_3lanes.glb",
    'pedestrian': "event/pedestrian.glb",
    'crash_vehicle_1lane': "event/crash_vehicle.glb",
    'crash_vehicle_3lanes': "event/crash_vehicle.glb",
    'other_accidents': "event/other_accidents.glb",
}
# 普通背景车辆 (随机, 带权重, 贴近现实车流分布). 常见车型权重高;
# taxi 城市常见; 跑车/轿跑 (sport/coupe) 极少见, 权重最低.
_BACKGROUND_MODELS = ['sedan', 'hatchback', 'taxi', 'compact', 'wagon',
                      'minivan', 'offroad', 'pickup', 'coupe', 'suv', 'sport']
_BACKGROUND_WEIGHTS = [18, 16, 13, 12, 11, 7, 7, 7, 7, 1, 1]  # random.choices 会自动归一化


def select_vehicle_model_name(veh_type: str) -> str:
    """根据车辆类型返回模型相对路径 (相对 vehicles/<poly>/); 背景车辆随机选择."""
    if veh_type in _MODEL_MAPPING:
        return _MODEL_MAPPING[veh_type]
    selected = random.choices(_BACKGROUND_MODELS, weights=_BACKGROUND_WEIGHTS, k=1)[0]
    return f"background/{selected}.glb"


def vehicle_models_dir() -> str:
    """返回车辆模型所在目录的绝对路径 (只维护一套车模)."""
    return _path_convert("../_assets_3d/vehicles")
