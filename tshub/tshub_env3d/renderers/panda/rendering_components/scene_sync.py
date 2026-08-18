'''
@Author: WANG Maonan
@Date: 2024-07-13 20:53:01
@Description: 场景同步 (Panda3D). 消费渲染器无关的 SceneFrame / SceneStatic,
负责 Panda3D 这一侧的工作: 管理 3D 元素 (车辆/飞行器/信号灯) 的增删改、渲染、读回传感器数据.

「场景里有什么」的提取与转换已上移到 tshub.tshub_env3d.vis3d_scene (build_frame / build_tls_rigs);
本文件只保留 Panda3D 特有的实现.
LastEditTime: 2026-06-01 00:00:00
'''
from loguru import logger
from typing import Dict, List

from ..traffic_elements.vehicle import Vehicle3DElement
from ..traffic_elements.traffic_signals import TLS3DElement
from ..traffic_elements.aircraft import Aircraft3DElement
from tshub.tshub_env3d.core import SceneFrame, SceneStatic, ObjectPose, validate_sensor_config


class SceneSync(object):
    def __init__(
            self, root_np, showbase_instance,
            sensor_config:Dict[str, List[str]],
            preset:str='480P', resolution:float=1.0,
        ) -> None:
        """同步场景内的 object (Panda3D 侧)

        Args:
            root_np: 场景的 Node
            showbase_instance: Pnada3D ShowBase
            sensor_config (Dict[str, List[str]]): 需要渲染的物体和对应的摄像头
            preset (str, optional): 预设分辨率名称（如 '720x480', '360x240' 等）. Defaults to '480p'.
            resolution (float, optional): 缩放因子（默认 1.0 表示原尺寸, 0.5 表示半尺寸）. Defaults to 1.0.
        """
        self.root_np = root_np
        self.showbase_instance = showbase_instance
        self.sensor_config = sensor_config # 不同 object 加载的传感器类型

        # 获得传感器输出的图像的分辨率和大小
        presets = {
            '320P': (320, 240),   # 320x240（类 NTSC 标清）
            '480P': (720, 480),   # 720x480（标准 480P）
            '720P': (1280, 720),  # 1280x720（HD 标清）
            '720P_SQUARE': (720, 720), # 720x720（BEV / map-style square output）
            '1080P': (1920, 1080) # 1920x1080（Full HD）
        }
        if preset not in presets:
            raise ValueError(f"Invalid preset: {preset}. Valid presets are: {list(presets.keys())}")
        self.fig_width, self.fig_height = presets.get(preset) # 获得图像的长和宽
        self.resolution = resolution

        if not validate_sensor_config(sensor_config):
            logger.info("SIM: Sensor configuration validation failed. Please check the errors above.")
            raise ValueError(f"传感器文件配置错误, {sensor_config}")

        # 记录场景中的 element
        self._vehicle_elements = {} # 加入渲染的车辆
        self._tls_elements = {} # 加入信号灯 (每一个 in road 会有一个), 这里信号灯没有实体, 只有 sensor
        self._aircraft_elements = {} # 加入渲染的飞行器

    def reset(self, static: SceneStatic) -> None:
        # 初始化 & 关闭所有车辆和飞行器的 sensors
        self.remove_missing_elements(set(), self._vehicle_elements, 'vehicle')
        self.remove_missing_elements(set(), self._aircraft_elements, 'aircraft')

        # 初始化信号灯相机 (只需要加载一次), rig 几何已由 build_tls_rigs 计算好
        if not self._tls_elements:
            for tls_element_id, rig in static.tls_rigs.items():
                self._initialize_tls_element(tls_element_id, rig)

    def _initialize_tls_element(self, tls_element_id, rig) -> None:
        """根据 rig (position/heading/height/sensor_types) 初始化某一个路口相机."""
        element = TLS3DElement(
            fig_width = self.fig_width,
            fig_height = self.fig_height,
            fig_resolution = self.resolution,
            element_id = tls_element_id,
            element_position = rig['position'],
            element_heading = rig['heading'],
            root_np = self.root_np,
            showbase_instance = self.showbase_instance,
            tls_camera_height = rig['tls_camera_height'],
        )
        element.attach_sensors_to_element(rig['sensor_types'])
        self._tls_elements[tls_element_id] = element

    def _sync(self, frame: SceneFrame):
        # 更新车辆和飞行器
        veh_ids, aircraft_ids = self.update_elements(frame)

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

    def update_elements(self, frame: SceneFrame):
        """根据 SceneFrame 更新 vehicle 和 aircraft 的信息, 会分别调用:
        1. self._manage_vehicle_element: 更新车辆信息
        2. self._manage_aircraft_element 更新飞行器信息
        """
        veh_ids, aircraft_ids = set(), set()

        # 1. 更新车辆的信息
        for veh_id, veh_pose in frame.vehicles.items():
            veh_ids.add(veh_id)
            self._manage_vehicle_element(veh_id, veh_pose)

        # 2. 更新飞行器的信息
        for aircraft_id, aircraft_pose in frame.aircraft.items():
            aircraft_ids.add(aircraft_id)
            self._manage_aircraft_element(aircraft_id, aircraft_pose)

        return veh_ids, aircraft_ids

    def _manage_vehicle_element(self, veh_id, veh_pose: ObjectPose) -> None:
        element = self._vehicle_elements.get(veh_id)
        if not element: # 如果车辆不存在
            element = Vehicle3DElement(
                fig_width = self.fig_width,
                fig_height = self.fig_height,
                fig_resolution = self.resolution,
                veh_id=veh_id,
                veh_type=veh_pose.object_type,
                veh_pos=veh_pose.position,
                veh_heading=veh_pose.heading,
                veh_length=veh_pose.length,
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
                veh_position=veh_pose.position,
                veh_heading=veh_pose.heading,
                veh_type=veh_pose.object_type
            )

    def _manage_aircraft_element(self, aircraft_id, aircraft_pose: ObjectPose) -> None:
        heading = aircraft_pose.heading # 已是角度 (degrees)
        element = self._aircraft_elements.get(aircraft_id)
        if not element:
            element = Aircraft3DElement(
                fig_width = self.fig_width,
                fig_height = self.fig_height,
                fig_resolution = self.resolution,
                aircraft_id=aircraft_id,
                aircraft_type=aircraft_pose.object_type or 'drone',
                aircraft_pos=aircraft_pose.position,
                aircraft_heading=heading,
                root_np=self.root_np,
                showbase_instance=self.showbase_instance
            )
            element.create_node()
            element.begin_rendering_node()
            if aircraft_id in self.sensor_config.get('aircraft', {}):
                sensor_types = self.sensor_config['aircraft'][aircraft_id].get('sensor_types', []) # 飞行器需要安装的传感器
                element.attach_sensors_to_element(sensor_types)
            self._aircraft_elements[aircraft_id] = element
        else:
            element.update_node(
                aircraft_position=aircraft_pose.position,
                aircraft_heading=heading,
                aircraft_type=aircraft_pose.object_type or 'drone',
            )

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
