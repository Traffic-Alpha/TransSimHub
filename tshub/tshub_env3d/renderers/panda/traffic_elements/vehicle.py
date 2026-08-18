'''
@Author: WANG Maonan
@Date: 2024-07-08 22:21:18
@Description: 3D 场景内的车辆
LastEditTime: 2025-09-01 15:36:04
'''
from loguru import logger
from typing import Tuple

from .base_element import BaseElement

# 导入传感器
from tshub.tshub_env3d.renderers.panda.masks import CamMask
from tshub.tshub_env3d.core import select_vehicle_model_name # 车辆模型选择 (各后端共用)
from tshub.utils.get_abs_path import get_abs_path

class Vehicle3DElement(BaseElement):
    current_file_path = get_abs_path(__file__)
    _carrier = 'vehicle'

    def __init__(
            self, 
            fig_width: float, fig_height: float, 
            fig_resolution:float,
            veh_id: str,
            veh_type: str,
            veh_pos: Tuple[float, float],
            veh_heading: float,
            veh_length: float,
            root_np, # showbase 的根节点
            showbase_instance, # panda3d showbase, 单例模式
        ) -> None:
        super().__init__(
            fig_width, fig_height, fig_resolution,
            veh_id, veh_pos, veh_heading, veh_length, root_np, showbase_instance
        )
        self.veh_type = veh_type # 车辆的类型, 对 ego 车辆特殊处理
        self.veh_node_path = None # 记录这辆车的 node path
        self.veh_model_name = None # 记录车辆加载的模型名称
    
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
        self.veh_node_path.hide(CamMask.AllOn) # 首先不让所有相机看到
        self.veh_node_path.show(CamMask.VehMask) # 接着只让部分相机可以看到
        
        return True

    def reset_node(self):
        self.remove_node() # 删除节点
        self.create_node() # 新增节点
        self.begin_rendering_node() # 渲染节点
        self.sensors = {}    
                
    def _select_vehicle_model(self) -> str:
        """根据车辆类型选择对应的 3D 模型路径.

        车辆类型 -> 模型相对路径的映射由渲染器无关的 scene.select_vehicle_model_name
        提供 (各后端共用). 只维护一套车模, 位于 _assets_3d/vehicles/ 下.
        """
        self.veh_model_name = select_vehicle_model_name(self.veh_type)
        return Vehicle3DElement.current_file_path(
            f"../../../_assets_3d/vehicles/{self.veh_model_name}"
        )

    def update_node(
            self, 
            veh_position:Tuple[float],
            veh_heading: float,
            veh_type:str,
        ) -> None:
        """Move the specified vehicle node (更新车辆的位置)
        """
        if not self.veh_node_path: # 如果是 None, 则会出现提示
            logger.warning(f"SIM: Renderer ignoring invalid vehicle id: {self.element_id}")
            return

        # vehicle type 改变, 则需要重新加载模型
        if veh_type != self.veh_type:
            self.veh_type = veh_type # 重新设置 vehicle type
            self.reset_node()
        
        # 更新模型的位置和传感器信息
        self.update_element_position_heading(veh_position, veh_heading) # 更新 vehicle element 的位置
        pose = self.get_element_pose_from_bumper() # 坐标转换
        pos, heading = pose.as_panda3d()
        self.veh_node_path.setPosHpr(*pos, heading, 0, 0)
        self.update_sensor() # 顺便更新传感器的位置

    def remove_node(self) -> None:
        """Remove a vehicle node
        """
        if not self.veh_node_path:
            logger.warning(f"SIM: Renderer ignoring invalid vehicle id: {self.element_id}")
            return
        logger.info(f"SIM: Remove Renderer vehicle id: {self.element_id}")
        self.veh_node_path.removeNode()
        # 删除车辆上面的传感器
        for _, _sensor in self.sensors.items():
            _sensor.teardown() # 删除挂载在车上的传感器
        self.sensors = None
        
    def begin_rendering_node(self) -> None:
        """Add the vehicle node to the scene graph
        """
        if not self.veh_node_path:
            logger.warning(f"SIM: Renderer ignoring invalid vehicle id: {self.element_id}")
            return
        
        # 连接到 TSHub Render 的根节点
        self.veh_node_path.reparentTo(self.root_np.find("**/vehicles"))
    
    # #################
    # 添加和更新 Sensors
    # #################

    def _sensor_init_pose(self):
        """车辆传感器初始位姿 = 前保险杠 (与 SUMO 车头坐标对齐)."""
        return self.get_element_pose_from_bumper()

    def update_sensor(self) -> None:
        """更新 sensor 的数据
        """
        for _sensor_id, _sensor in self.sensors.items():
            # 更新 camera 的位置, 车辆的 sensor 跟着车辆跑就行
            _sensor.step(self.get_element_pose_from_bumper())
    
    def get_sensor(self):
        sensor_data = {}
        for _sensor_id, _sensor in self.sensors.items():
            ego_rgb = _sensor() # 调用 call 获得传感器数据
            sensor_data[_sensor_id] = ego_rgb
        return sensor_data
