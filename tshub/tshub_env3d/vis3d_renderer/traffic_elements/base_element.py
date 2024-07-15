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
@LastEditTime: 2024-07-15 12:09:15
'''
import numpy as np
from typing import Tuple
from abc import ABC, abstractmethod

from ...vis3d_utils.coordinates import Pose, Heading

class BaseElement(ABC):
    def __init__(
            self,
            element_id:str,
            element_position:Tuple[float, float],
            element_heading:float,
            element_length:float = None,
            root_np = None,
            showbase_instance = None
        ) -> None:
        super().__init__()
        self.element_id = element_id
        self.element_position = element_position
        self.element_heading = element_heading
        self.element_length = element_length

        self.root_np = root_np
        self.showbase_instance = showbase_instance

        # element 的属性
        self.length, self.width, self.height = None, None, None # 模型的长宽高
        self.sensors = {} # 记录 element 上面绑定的 sensors
        self._cameras = {} # 记录这个 element 上面拥有的 camera
    
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

    @abstractmethod
    def remove_node(self):
        raise NotImplementedError

    @abstractmethod
    def begin_rendering_node(self):
        raise NotImplementedError

    # ----------- #
    # 添加 Sensor
    # ----------- #
    def attach_sensor_to_element(self):
        raise NotImplementedError
    
    @staticmethod
    def _gen_sensor_name(base_name: str, vehicle_id: str):
        return BaseElement._gen_base_sensor_name(base_name, vehicle_id)
    
    @staticmethod
    def _gen_base_sensor_name(base_name: str, actor_id: str):
        return f"{base_name}_{actor_id}"