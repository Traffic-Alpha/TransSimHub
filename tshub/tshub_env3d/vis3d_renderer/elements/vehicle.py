'''
@Author: WANG Maonan
@Date: 2024-07-08 22:21:18
@Description: 3D 场景内的车辆
@LastEditTime: 2024-07-14 20:32:12
'''
import random
from pathlib import Path
from loguru import logger
from typing import Tuple, Union, Optional, Dict, Any

from .base_element import BaseElement
from ...vis3d_utils.coordinates import Pose, Heading

# 导入传感器
from ..sensors.rgb_sensor import RGBSensor
from ..sensors.vehicle_mask_sensor import VehicleSensor
from ..sensors.camera_sensor_type import CameraSensorID
from ...vis3d_utils.masks import CamMask
from ....utils.get_abs_path import get_abs_path

from panda3d.core import BitMask32, CollisionNode

class Vehicle3DElement(BaseElement):
    current_file_path = get_abs_path(__file__)

    def __init__(
            self, 
            veh_id: str,
            veh_type: str,
            veh_pos: Tuple[float, float],
            veh_heading: float,
            veh_length: float,
            root_np, # showbase 的根节点
            showbase_instance # panda3d showbase, 单例模式 
        ) -> None:
        super().__init__(veh_id, veh_pos, veh_heading, veh_length, root_np, showbase_instance)
        self.veh_type = veh_type # 车辆的类型, 对 ego 车辆特殊处理
        self.veh_node_path = None # 记录这辆车的 node path
    
    # ###################
    # Vehicle Node 的更新
    # ###################
    def create_node(self) -> bool:
        """Create a vehicle node.
        """
        veh_model_path = self._select_vehicle_model() # 随机选择车辆的模型
        self.veh_node_path = self.showbase_instance.loader.loadModel(veh_model_path)
        self.get_node_dimensions(node_path=self.veh_node_path)
        self.veh_node_path.setName(f"vehicle-{self.element_id}")

        pose = self.get_element_pose_from_bumper() # 车辆坐标转换
        pos, heading = pose.as_panda3d() # 转换为位置和角度
        self.veh_node_path.setPosHpr(*pos, heading, 0, 0)
        self.veh_node_path.hide(BitMask32.allOn()) # 首先不让所有相机看到
        self.veh_node_path.show(CamMask.VehMask) # 接着只让部分相机可以看到
        
        return True

    def _select_vehicle_model(self) -> str:
        """随机选择车辆的模型, ego vehicle 和 soical vehicle 的模型是不一样的
        """
        if 'ego' in self.veh_type:
            veh_list = ['AudiTT', 'FerrariF355']
            weights = [4/5, 1/5]
            selected_model = random.choices(veh_list, weights=weights, k=1)[0]
            return Vehicle3DElement.current_file_path(f"../../_assets_3d/vehicles/ego_vehicles/{selected_model}.bam")
        else:
            veh_list = [
                'BMWZ4', 'HyundaiKona', 'KiaXceed', 
                'LamborghiniUrus', 'MercedesCL', 'NIssanMurano', 
                'Peugeot208', 'volkswagenT-Roc'
            ]
            weights = [1/14, 1/14, 1/14, 1/2, 1/14, 1/14, 1/14, 1/14]
            selected_model = random.choices(veh_list, weights=weights, k=1)[0]
            return Vehicle3DElement.current_file_path(f"../../_assets_3d/vehicles/social_vehicles/{selected_model}.bam")


    def update_node(
            self, 
            veh_position:Tuple[float],
            veh_heading: float,
        ) -> None:
        """Move the specified vehicle node (更新车辆的位置)
        """
        if not self.veh_node_path: # 如果是 None, 则会出现提示
            logger.warning(f"SIM: Renderer ignoring invalid vehicle id: {self.element_id}")
            return

        self.update_element_position_heading(veh_position, veh_heading) # 更新 vehicle element 的位置
        pose = self.get_element_pose_from_bumper() # 坐标转换
        pos, heading = pose.as_panda3d()
        self.veh_node_path.setPosHpr(*pos, heading, 0, 0)

    def remove_node(self) -> None:
        """Remove a vehicle node
        """
        if not self.veh_node_path:
            logger.warning(f"SIM: Renderer ignoring invalid vehicle id: {self.element_id}")
            return
        self.veh_node_path.removeNode()
        
    def begin_rendering_node(self) -> None:
        """Add the vehicle node to the scene graph
        """
        if not self.veh_node_path:
            logger.warning(f"SIM: Renderer ignoring invalid vehicle id: {self.element_id}")
            return
        
        # 连接到 TSHub Render 的根节点
        self.veh_node_path.reparentTo(self.root_np.find("**/vehicles"))
    
    # ############
    # 添加 Sensors
    # ############
    # 这里需要重构一下, attach_sensor, 然后可以有不同种类的 sensor
    def attach_rgbsensor_to_element(self) -> None:
        # 获得当前 camera 的名称
        _camera_name = BaseElement._gen_sensor_name(
            base_name=CameraSensorID.TOP_DOWN_RGB.value, 
            vehicle_id=self.element_id
        )

        # 在 node path 上创建 camera (camera 需要和 sensor 进行绑定)
        # TODO, 这里需要把 build camera 直接放在 sensor init 的时候
        self.build_offscreen_camera(
            name=_camera_name,
            mask= (CamMask.VehMask),
            width=800,
            height=600,
            resolution=0.1, # resolution 越小, 视野越小
        ) # 这里调整 camera 的参数

        # 将 sensor 与 camera 进行绑定
        # veh_rgb_sensor = RGBSensor(
        #     camera=self._cameras[_camera_name],
        #     element_pose=self.get_element_pose_from_bumper(), # 获得车辆当前的位置
        #     element_dimensions=(self.length, self.width, self.height),
        # ) # 定义车辆的 RGB Sensor
        # self.sensors['rgb'] = veh_rgb_sensor # 在 element 上新增 sensors

        # 定义不同的 sensor
        veh_rgb_sensor = VehicleSensor(
            camera=self._cameras[_camera_name],
            element_pose=self.get_element_pose_from_bumper(), # 获得车辆当前的位置
            element_dimensions=(self.length, self.width, self.height),
        ) # 定义车辆的 RGB Sensor
        self.sensors['rgb'] = veh_rgb_sensor # 在 element 上新增 sensors
    
    def update_sensor(self) -> None:
        """更新 sensor 的数据
        """
        for _sensor_id, _sensor in self.sensors.items():
            _sensor.step(self.get_element_pose_from_bumper()) # 更新 camera 的位置
    
    def get_sensor(self):
        sensor_data = {}
        for _sensor_id, _sensor in self.sensors.items():
            ego_rgb = _sensor()
            sensor_data[_sensor_id] = ego_rgb
        return sensor_data