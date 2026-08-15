'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: 从 tshub 观测构建渲染器无关的 SceneFrame / 路口相机 rig.

这里集中了原先散落在 SceneSync 里、与具体渲染引擎无关的逻辑:
- 从 tshub_obs 抽取车辆 / 飞行器位姿 (build_frame);
- 飞行器 heading -> 角度的语义转换;
- 路口相机 rig 的几何计算 (build_tls_rigs);
- 传感器配置校验 (validate_sensor_config).
不含任何 panda3d / blender import.
@LastEditTime: 2026-06-01 00:00:00
'''
import math
from loguru import logger
from typing import Any, Dict, List

# core_math 是 panda3d-free 的纯数学工具, 可安全用于渲染器无关层
from tshub.tshub_env3d.scene.utils.core_math import calculate_center_point, vec_to_radians, vec_2d
from .scene_elements import ObjectPose, SceneFrame
from .sensor_rig import CAMERA_RIGS

# 允许的传感器类型: object 类型 -> 该类型可挂载的传感器.
# 从 CAMERA_RIGS 派生 (单一真相源: 每个 rig 自带 carrier), 无需再手工维护一份列表.
VALID_SENSORS = {}
for _sensor_type, _rig in CAMERA_RIGS.items():
    VALID_SENSORS.setdefault(_rig.carrier, []).append(_sensor_type)


def validate_sensor_config(sensor_config: Dict[str, Any]) -> bool:
    """校验传感器配置是否合法 (object 类型与传感器类型均需在 VALID_SENSORS 内)."""
    for category, object_sensors in sensor_config.items():
        # 1. object 类型只支持 vehicle / tls / aircraft
        if category not in VALID_SENSORS:
            logger.error(f"SIM: Invalid category: {category}. Valid categories are {list(VALID_SENSORS.keys())}.")
            return False
        # 2. 具体传感器类型需在该类别允许的范围内
        for object_id, sensors_info in object_sensors.items():
            invalid_sensors = set(sensors_info.get('sensor_types', [])) - set(VALID_SENSORS[category])
            if invalid_sensors:
                logger.error(f"SIM: Invalid sensors in {category}: {invalid_sensors}. Valid sensors are {VALID_SENSORS[category]}.")
                return False
    return True


def build_frame(tshub_obs: Dict[str, Any]) -> SceneFrame:
    """从 tshub 观测构建一帧渲染器无关的 SceneFrame.

    车辆 heading 保持 tshub 观测中的原始值; 飞行器 heading 转换为角度 (0~360).
    """
    frame = SceneFrame()

    for veh_id, veh_info in tshub_obs.get('vehicle', {}).items():
        frame.vehicles[veh_id] = ObjectPose(
            object_id=veh_id,
            category='vehicle',
            position=veh_info['position'],
            heading=veh_info['heading'],
            object_type=veh_info['vehicle_type'],
            length=veh_info['length'],
        )

    for aircraft_id, aircraft_info in tshub_obs.get('aircraft', {}).items():
        heading_rad = vec_to_radians(vec_2d(aircraft_info['heading']))
        # aircraft heading comes from a velocity vector in tshub/SMARTS
        # convention (+Y=0, counter-clockwise). ObjectPose.heading is consumed
        # by Panda elements through Heading.from_sumo(), so store SUMO-style
        # degrees here (+Y=0, clockwise).
        heading_deg = math.degrees((2 * math.pi - heading_rad) % (2 * math.pi))
        frame.aircraft[aircraft_id] = ObjectPose(
            object_id=aircraft_id,
            category='aircraft',
            position=aircraft_info['position'],
            heading=heading_deg,
            object_type=aircraft_info.get('aircraft_type'),
        )

    return frame


def build_tls_rigs(tshub_init_obs: Dict[str, Any],
                   sensor_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """计算路口相机 rig (渲染器无关的几何): 在每个进入路口的 road 方向布置一个相机.

    返回: {tls_element_id: {'position', 'heading', 'sensor_types', 'tls_camera_height'}},
    其中 tls_element_id 形如 '{tls_id}_{index}'.
    """
    tls_rigs: Dict[str, Dict[str, Any]] = {}
    if ('tls' not in tshub_init_obs) or ('tls' not in sensor_config):
        return tls_rigs

    for tls_id, tls_info in tshub_init_obs['tls'].items():
        if tls_id not in sensor_config['tls']: # 只处理配置了传感器的路口
            continue
        sensor_types = sensor_config['tls'][tls_id].get('sensor_types', [])
        tls_camera_height = sensor_config['tls'][tls_id].get('tls_camera_height', 10)
        junction_bev_height = sensor_config['tls'][tls_id].get('junction_bev_height', 60)

        # 区分两类路口相机: 「每条 in-road 一个」(junction_front/back) 与「一个路口一个」的俯视 (junction_bev)
        road_sensors = [s for s in sensor_types if not s.startswith('junction_bev')]
        bev_sensors = [s for s in sensor_types if s.startswith('junction_bev')]

        # 按 heading 排序保证 index 稳定
        sorted_road_ids = sorted(tls_info['in_roads_heading'], key=tls_info['in_roads_heading'].get)
        road_centers = []
        for index, road_id in enumerate(sorted_road_ids):
            center = calculate_center_point(tls_info['in_road_stop_line'][road_id])
            road_centers.append(center)

        for index, road_id in enumerate(sorted_road_ids):
            center = road_centers[index]
            if road_sensors: # 每条 in-road 一个地面相机
                tls_rigs[f'{tls_id}_{index}'] = {
                    'position': center,
                    'heading': tls_info['in_roads_heading'][road_id],
                    'sensor_types': road_sensors,
                    'tls_camera_height': tls_camera_height,
                }

        # 一个路口一个俯视相机, 架在所有停车线中点的质心 (整个交叉口中心) 正上方
        if bev_sensors and road_centers:
            tls_rigs[f'{tls_id}_bev'] = {
                'position': calculate_center_point(road_centers),
                'heading': 0.0,
                'sensor_types': bev_sensors,
                'tls_camera_height': junction_bev_height,
            }
    return tls_rigs
