'''
@Author: WANG Maonan
@Date: 2024-07-13 20:53:01
@Description: 场景的同步, 根据 SUMO 的信息更新 panda3d
LastEditTime: 2025-07-28 21:13:10
'''
import math
from loguru import logger
from typing import Dict, List

from ..traffic_elements.vehicle import Vehicle3DElement
from ..traffic_elements.traffic_signals import TLS3DElement
from ..traffic_elements.aircraft import Aircraft3DElement
from ...vis3d_utils.core_math import calculate_center_point, vec_to_radians, vec_2d

VALID_SENSORS = {
    'aircraft': ['aircraft_all', 'aircraft_vehicle'],
    'tls': [
        'junction_front_all', 'junction_front_vehicle', 
        'junction_back_all', 'junction_back_vehicle'
    ],
    'vehicle': [
        'front_left_all', 'front_right_all', 'front_all', 
        'back_left_all', 'back_right_all', 'back_all',
        'front_left_vehicle', 'front_right_vehicle', 'front_vehicle', 
        'back_left_vehicle', 'back_right_vehicle', 'back_vehicle',
        'bev_all', 'bev_vehicle'
    ]
}


class SceneSync(object):
    def __init__(
            self, root_np, showbase_instance, 
            sensor_config:Dict[str, List[str]],
            preset:str='480P', resolution:float=1.0,
            vehicle_model:str='low'
        ) -> None:
        """同步场景内的 object

        Args:
            root_np: 场景的 Node
            showbase_instance: Pnada3D ShowBase
            sensor_config (Dict[str, List[str]]): 需要渲染的物体和对应的摄像头
            preset (str, optional): 预设分辨率名称（如 '720x480', '360x240' 等）. Defaults to '480p'.
            resolution (float, optional): 缩放因子（默认 1.0 表示原尺寸, 0.5 表示半尺寸）. Defaults to 1.0.
        """
        self.root_np = root_np
        self.showbase_instance = showbase_instance
        self.vehicle_model = vehicle_model # 加载不同精度的车辆 3D 模型
        self.sensor_config = sensor_config # 不同 object 加载的传感器类型

        # 获得传感器输出的图像的分辨率和大小
        presets = {
            '320P': (320, 240),   # 320x240（类 NTSC 标清）
            '480P': (720, 480),   # 720x480（标准 480P）
            '720P': (1280, 720),  # 1280x720（HD 标清）
            '1080P': (1920, 1080) # 1920x1080（Full HD）
        }
        if preset not in presets:
            raise ValueError(f"Invalid preset: {preset}. Valid presets are: {list(presets.keys())}")
        self.fig_width, self.fig_height = presets.get(preset) # 获得图像的长和宽
        self.resolution = resolution

        if not SceneSync.validate_sensor_config(sensor_config):
            logger.info("SIM: Sensor configuration validation failed. Please check the errors above.")
            raise ValueError(f"传感器文件配置错误, {sensor_config}")
            
        # 记录场景中的 element
        self._vehicle_elements = {} # 加入渲染的车辆
        self._tls_elements = {} # 加入信号灯 (每一个 in road 会有一个), 这里信号灯没有实体, 只有 sensor
        self._aircraft_elements = {} # 目前 aircraft 没有实体, 只有摄像头

    @staticmethod
    def validate_sensor_config(sensor_config: Dict[str, List[str]]) -> bool:
        """Validate the sensor configuration against the predefined valid sensors.
        """
        for category, object_sensors in sensor_config.items():
            # 1. 检测安装传感器的 object 类型是否符合标准, 只支持三种, 分别是 vehicle, tls 和 aircraft
            if category not in VALID_SENSORS: # 只能给三种类型的 objects 安装传感器
                logger.error(f"SIM: Invalid category: {category}. Valid categories are {list(VALID_SENSORS.keys())}.")
                return False
            
            # 2. 检测具体的传感器类型是否符合要求, 例如 tls 支持 junction_front_all 
            for object_id, sensors_info in object_sensors.items():            
                # 检测传感器的类型
                invalid_sensors = set(sensors_info.get('sensor_types', [])) - set(VALID_SENSORS[category])
                if invalid_sensors:
                    logger.error(f"SIM: Invalid sensors in {category}: {invalid_sensors}. Valid sensors are {VALID_SENSORS[category]}.")
                    return False
        return True

    def reset(self, tshub_init_obs) -> None:
        # 初始化 & 关闭所有车辆和飞行器的 sensors
        self.remove_missing_elements(set(), self._vehicle_elements, 'vehicle')
        self.remove_missing_elements(set(), self._aircraft_elements, 'aircraft')
        
        # 初始化信号灯 (如果没有初始化 & 路口有信号灯的信息 & 设置了信号灯的传感器)
        if (not self._tls_elements) and ("tls" in tshub_init_obs) and ("tls" in self.sensor_config): # 只需要加载一次即可
            for tls_id, tls_info in tshub_init_obs['tls'].items():
                if tls_id in self.sensor_config['tls']: # 只初始化指定的信号灯路口
                    self._initialize_tls_elements(tls_id, tls_info)

    def _initialize_tls_elements(self, tls_id, tls_info) -> None:
        """初始化某一个信号灯传感器
        """
        sensor_types = self.sensor_config['tls'][tls_id].get('sensor_types', []) # 获得特定路口(tls_id)传感器类型
        tls_camera_height = self.sensor_config['tls'][tls_id].get('tls_camera_height', 10) # 传感器的高度
        # 获得路口的方向, 在每一个方向安装摄像头
        sorted_road_ids = sorted(tls_info['in_roads_heading'], key=tls_info['in_roads_heading'].get)

        for index, road_id in enumerate(sorted_road_ids):
            tls_element_id = f'{tls_id}_{index}'
            position = calculate_center_point(tls_info['in_road_stop_line'][road_id])
            heading = tls_info['in_roads_heading'][road_id]
            element = TLS3DElement(
                fig_width = self.fig_width,
                fig_height = self.fig_height,
                fig_resolution = self.resolution,
                element_id = tls_element_id, 
                element_position = position, 
                element_heading = heading, 
                root_np = self.root_np, 
                showbase_instance = self.showbase_instance,
                tls_camera_height=tls_camera_height
            ) # 初始化路口信号灯的 element
            element.attach_sensors_to_element(sensor_types)
            self._tls_elements[tls_element_id] = element      


    def _sync(self, tshub_obs):
        # 更新车辆和飞行器
        veh_ids, aircraft_ids = self.update_elements(tshub_obs)
        
        # 管理离开的 vehicle 和 aircraft
        self.remove_missing_elements(veh_ids, self._vehicle_elements, 'vehicle')
        self.remove_missing_elements(aircraft_ids, self._aircraft_elements, 'aircraft')
        
        # 更新 camera
        logger.info(f'SIM: Update All Sensors Positions.')
        self.showbase_instance.taskMgr.step()
        
        # 所有传感器渲染
        self.showbase_instance.graphicsEngine.renderFrame()

        # 获得 camera 的数据
        _sensors = {
            **self.collect_sensors(self._tls_elements), 
            **self.collect_sensors(self._vehicle_elements), 
            **self.collect_sensors(self._aircraft_elements)
        }
        return _sensors

    def update_elements(self, tshub_obs):
        """跟据 SUMO 的观测更新 vehicle 和 aircraft 的信息, 会分别调用:
        1. self._manage_vehicle_element: 更新车辆信息
        2. self._manage_aircraft_element 更新飞行器信息
        """
        # 每一步需要处理的 vehicles 和 aircrafts 的 ids
        # 有两类 objects, 分别是:
        # - 需要挂载传感器在 object 上面 (需要同时满足出现在场景且需要挂载传感器)
        # - 不需要挂载传感器, 只需要使用 panda3d 在场景中渲染出来
        veh_ids, aircraft_ids = set(), set()

        # 1. 更新车辆的信息 (如果出现在 SUMO 中就需要在 tshub3d 中进行渲染)
        for veh_id, veh_info in tshub_obs.get('vehicle', {}).items():
            veh_ids.add(veh_id)
            self._manage_vehicle_element(veh_id, veh_info)

        # 2. 更新飞行器的信息 (如果出现在 SUMO 中就需要在 tshub3d 中进行渲染)
        for aircraft_id, aircraft_info in tshub_obs.get('aircraft', {}).items():
            aircraft_ids.add(aircraft_id)
            self._manage_aircraft_element(aircraft_id, aircraft_info)         

        return veh_ids, aircraft_ids

    def _manage_vehicle_element(self, veh_id, veh_info) -> None:
        # 获得车辆传感器的配置信息
        element = self._vehicle_elements.get(veh_id)
        if not element: # 如果车辆不存在
            element = Vehicle3DElement(
                fig_width = self.fig_width,
                fig_height = self.fig_height,
                fig_resolution = self.resolution,
                vehicle_model=self.vehicle_model,
                veh_id=veh_id, 
                veh_type=veh_info['vehicle_type'], 
                veh_pos=veh_info['position'], 
                veh_heading=veh_info['heading'], 
                veh_length=veh_info['length'], 
                root_np=self.root_np, 
                showbase_instance=self.showbase_instance
            )
            element.create_node()
            element.begin_rendering_node()
            # 只有特定的车辆才需要挂载传感器
            if veh_id in self.sensor_config.get('vehicle', {}):
                sensor_types = self.sensor_config['vehicle'][veh_id].get('sensor_types', []) # 车辆需要安装的传感器
                element.attach_sensors_to_element(sensor_types)
            self._vehicle_elements[veh_id] = element
        else:
            element.update_node(
                veh_position=veh_info['position'], 
                veh_heading=veh_info['heading'], 
                veh_type=veh_info['vehicle_type']
            )

    def _manage_aircraft_element(self, aircraft_id, aircraft_info) -> None:
        heading = math.degrees(vec_to_radians(vec_2d(aircraft_info['heading']))) % 360
        element = self._aircraft_elements.get(aircraft_id)
        if not element:
            element = Aircraft3DElement(
                fig_width = self.fig_width,
                fig_height = self.fig_height,
                fig_resolution = self.resolution,
                aircraft_id=aircraft_id, 
                aircraft_pos=aircraft_info['position'], 
                aircraft_heading=heading, 
                root_np=self.root_np, 
                showbase_instance=self.showbase_instance
            )
            if aircraft_id in self.sensor_config.get('aircraft', {}):
                sensor_types = self.sensor_config['aircraft'][aircraft_id].get('sensor_types', []) # 飞行器需要安装的传感器
                element.attach_sensors_to_element(sensor_types)
            self._aircraft_elements[aircraft_id] = element
        else:
            element.update_sensor(aircraft_info['position'], heading)

    def remove_missing_elements(self, current_ids, elements, element_type):
        missing_ids = set(elements) - current_ids # 计算减少的 id
        for id in missing_ids:
            elements[id].remove_node() # tarffic element 中调用 remove node
            del elements[id]
            logger.info(f'SIM: 3D, Del {element_type} {id} since it leaves the scenario.')

    def collect_sensors(self, elements):
        # 获得传感器数据
        sensor_outputs = {} # 获得传感器的输出
        for id, element in elements.items():
            _sensor_output = element.get_sensor()
            if _sensor_output:
                sensor_outputs[id] = _sensor_output
        return sensor_outputs