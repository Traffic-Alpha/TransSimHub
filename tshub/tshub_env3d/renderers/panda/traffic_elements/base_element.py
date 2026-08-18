'''
@Author: WANG Maonan
@Date: 2024-07-08 21:51:45
@Description: Base 3D Elements, 主要包含以下的方法:
-> 在 render 的 root node path 上添加 node
--> create node
--> update node
--> remove node
--> begin render node
-> 在 node 上添加传感器
这里 Element 可以是 vehicles, aircrsaft, 或是 traffic signal light
LastEditTime: 2025-03-21 10:52:49
'''
import numpy as np
from typing import Tuple, List
from abc import ABC, abstractmethod

from tshub.tshub_env3d.core.utils.coordinates import Pose, Heading
from tshub.tshub_env3d.core import get_camera_rig
from tshub.tshub_env3d.renderers.panda.masks import FULL_CAM_MASK
from tshub.tshub_env3d.renderers.panda.sensors.rgb_sensor import RGBSensor

class BaseElement(ABC):
    def __init__(
            self,
            fig_width: float, fig_height: float, 
            fig_resolution:float,
            element_id:str,
            element_position:Tuple[float, float],
            element_heading:float = None,
            element_length:float = None,
            root_np = None,
            showbase_instance = None
        ) -> None:
        super().__init__()
        # 传感器输出相关
        self.fig_width = fig_width
        self.fig_height = fig_height
        self.fig_resolution = fig_resolution

        self.element_id = element_id
        self.element_position = element_position
        self.element_heading = element_heading
        self.element_length = element_length

        self.root_np = root_np
        self.showbase_instance = showbase_instance

        # element 的属性
        self.length, self.width, self.height = 0,0,0 # 模型的长宽高
        self.sensors = {} # 记录 element 上面绑定的 sensors

    def get_element_pose_from_center(self) -> Pose:
        """将当前 element (这里是 tls) 的位置转换为 TSHub3D 中的坐标
        """
        return Pose.from_center(
            base_position=np.array(self.element_position),
            heading=Heading.from_sumo(self.element_heading),
        )
    
    def get_element_pose_from_bumper(self) -> Pose:
        """将当前 element (这里是 vehicle) 的位置转换为 TSHub3D 中的坐标
        """
        return Pose.from_front_bumper(
            front_bumper_position=np.array(self.element_position),
            heading=Heading.from_sumo(self.element_heading),
            length=self.element_length
        )

    def get_node_dimensions(self, node_path) -> None:
        # 获取节点的边界
        node_bound = node_path.getBounds()

        # 获取边界的最小和最大点
        min_point = node_bound.getMin()
        max_point = node_bound.getMax()

        # 计算长、宽和高
        self.length = max_point.getX() - min_point.getX()
        self.width = max_point.getY() - min_point.getY()
        self.height = max_point.getZ() - min_point.getZ()

    def update_element_position_heading(
            self, 
            new_position:Tuple[float, float], 
            new_heading:float
        ) -> None:
        """更新 element 的位置信息等

        Args:
            new_position (Tuple[float, float]): element 新的位置
            new_heading (float): element 新的角度
        """
        self.element_position = new_position
        self.element_heading = new_heading
    
    # ------------------- #
    # 创建, 更新和删除 Node
    # ------------------- #
    @abstractmethod
    def create_node(self):
        raise NotImplementedError

    @abstractmethod
    def update_node(self):
        raise NotImplementedError

    def remove_node(self) -> None:
        # 删除传感器 (一个 node 可以挂载多个传感器)
        for _, _sensor in self.sensors.items():
            _sensor.teardown() # 删除传感器
        self.sensors = None

    @abstractmethod
    def begin_rendering_node(self):
        raise NotImplementedError

    # ----------- #
    # 添加 Sensor
    # ----------- #
    # element 的载体类型 (子类覆盖): 'vehicle' | 'tls' | 'aircraft', 用于校验 sensor_type
    _carrier: str = None

    def attach_sensor_to_element(self, sensor_type: str) -> None:
        """按 sensor_type 从注册表 (scene.sensor_rig) 取 CameraRig, 派生 mask, 挂载一个 RGBSensor.

        取代原先各 element 里硬编码的 sensor_configs (camera_mask + camera_type):
        现在 mask 由 rig.visibility 派生, 相机由 rig 直接驱动, 单一真相源为 CAMERA_RIGS.
        """
        rig = get_camera_rig(sensor_type)
        if self._carrier is not None and rig.carrier != self._carrier:
            raise ValueError(
                f"sensor_type '{sensor_type}' (carrier={rig.carrier}) 不能挂在 {self._carrier} 上"
            )
        self.sensors[sensor_type] = RGBSensor(
            camera_name=self._gen_sensor_name(sensor_type, self.element_id),
            camera_mask=FULL_CAM_MASK,
            showbase_instance=self.showbase_instance,
            root_np=self.root_np,
            init_element_pose=self._sensor_init_pose(),
            element_dimensions=(self.length, self.width, self.height),
            fig_width=self.fig_width,
            fig_height=self.fig_height,
            fig_resolution=self.fig_resolution,
            rig=rig,
            **self._sensor_extra_kwargs(),
        )

    def _sensor_init_pose(self) -> Pose:
        """传感器初始位姿 (默认按 element 中心; 车辆覆盖为前保险杠)."""
        return self.get_element_pose_from_center()

    def _sensor_extra_kwargs(self) -> dict:
        """传给 RGBSensor 的额外 kwargs (如 tls 的相机高度). 默认无."""
        return {}

    def attach_sensors_to_element(self, sensor_types: List[str]) -> None:
        for sensor_type in sensor_types:
            self.attach_sensor_to_element(sensor_type)

    @staticmethod
    def _gen_sensor_name(base_name: str, vehicle_id: str):
        return BaseElement._gen_base_sensor_name(base_name, vehicle_id)
    
    @staticmethod
    def _gen_base_sensor_name(base_name: str, actor_id: str):
        return f"{base_name}_{actor_id}"