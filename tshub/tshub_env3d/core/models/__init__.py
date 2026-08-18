'''
@Author: WANG Maonan
@Date: 2026-08-15
@Description: 3D 资产选择 (物体类型 -> glb 模型), 渲染器无关.

各后端 (Panda 在线 / Blender 离线) 共用同一套映射, 保证同一辆车在两条渲染路径上
是同一个模型. 模型文件位于 _assets_3d/.
@LastEditTime: 2026-08-15
'''
from .vehicle_models import select_vehicle_model_name, vehicle_models_dir
from .aircraft_models import select_aircraft_model_name, aircraft_models_dir

__all__ = [
    'select_vehicle_model_name', 'vehicle_models_dir',
    'select_aircraft_model_name', 'aircraft_models_dir',
]
