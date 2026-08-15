'''
@Author: WANG Maonan
@Date: 2026-07-11
@Description: 渲染器无关的飞行器 3D 模型选择 (aircraft_type -> glb 相对路径).
'''
from tshub.utils.get_abs_path import get_abs_path

_path_convert = get_abs_path(__file__)

_MODEL_MAPPING = {
    'drone': 'evetol/evetol_design_2022.glb',
    'evetol': 'evetol/evetol_design_2022.glb',
    'evtol': 'evetol/evetol_design_2022.glb',
}


def select_aircraft_model_name(aircraft_type: str) -> str:
    """根据 aircraft 类型返回模型相对路径."""
    return _MODEL_MAPPING.get(aircraft_type, _MODEL_MAPPING['drone'])


def aircraft_models_dir() -> str:
    """返回飞行器模型所在目录的绝对路径.

    当前复用 vehicles 资产目录, 因为 eVTOL 模型临时放在该目录下。
    """
    return _path_convert("../_assets_3d/vehicles")
