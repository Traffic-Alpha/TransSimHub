'''
@Author: WANG Maonan
@Date: 2024-07-13 22:14:31
@Description: 仿真器中飞行器的可视化 (在飞行器上安装摄像头)
LastEditTime: 2025-03-21 10:56:41
'''
from typing import Tuple
from loguru import logger

from .base_element import BaseElement
from tshub.tshub_env3d.renderers.panda.masks import CamMask
from tshub.tshub_env3d.core import select_aircraft_model_name
from tshub.utils.get_abs_path import get_abs_path

# 导入传感器

class Aircraft3DElement(BaseElement):
    current_file_path = get_abs_path(__file__)

    def __init__(
            self, 
            fig_width: float, fig_height: float, 
            fig_resolution:float,
            aircraft_id: str,
            aircraft_type: str,
            aircraft_pos: Tuple[float, float, float],
            aircraft_heading: float,
            aircraft_length: float = None,
            root_np = None, # showbase 的根节点
            showbase_instance = None, # panda3d showbase, 单例模式 
        ) -> None:
        super().__init__(
            fig_width, fig_height, fig_resolution,
            aircraft_id, aircraft_pos, aircraft_heading, aircraft_length, root_np, showbase_instance
        )
        self.aircraft_type = aircraft_type
        self.aircraft_node_path = None
        self.aircraft_model_name = None
    
    # ###########################################
    # Aircraft Node 的更新
    # ###########################################
    _carrier = 'aircraft'

    def create_node(self) -> None:
        aircraft_model_path = self._select_aircraft_model()
        self.aircraft_node_path = self.showbase_instance.loader.loadModel(aircraft_model_path)
        self.get_node_dimensions(node_path=self.aircraft_node_path)
        self.aircraft_node_path.setName(f"aircraft-{self.element_id}")

        pose = self.get_element_pose_from_center()
        pos, heading = pose.as_panda3d()
        self.aircraft_node_path.setPosHpr(*pos, heading, 0, 0)
        self.aircraft_node_path.hide(CamMask.AllOn)
        self.aircraft_node_path.show(CamMask.AircraftMask)

    def _select_aircraft_model(self) -> str:
        self.aircraft_model_name = select_aircraft_model_name(self.aircraft_type)
        return Aircraft3DElement.current_file_path(
            f"../../../_assets_3d/vehicles/{self.aircraft_model_name}"
        )

    def update_node(
            self,
            aircraft_position: Tuple[float, float, float],
            aircraft_heading: float,
            aircraft_type: str,
        ) -> None:
        if not self.aircraft_node_path:
            logger.warning(f"SIM: Renderer ignoring invalid aircraft id: {self.element_id}")
            return

        if aircraft_type != self.aircraft_type:
            self.aircraft_type = aircraft_type
            self.reset_node()

        self.update_element_position_heading(aircraft_position, aircraft_heading)
        pose = self.get_element_pose_from_center()
        pos, heading = pose.as_panda3d()
        self.aircraft_node_path.setPosHpr(*pos, heading, 0, 0)
        self.update_sensor(aircraft_position, aircraft_heading)

    def reset_node(self):
        self.remove_node()
        self.create_node()
        self.begin_rendering_node()
        self.sensors = {}

    def remove_node(self) -> None:
        if self.aircraft_node_path:
            logger.info(f"SIM: Remove Renderer aircraft id: {self.element_id}")
            self.aircraft_node_path.removeNode()
        for _, _sensor in (self.sensors or {}).items():
            _sensor.teardown()
        self.sensors = None
        
    def begin_rendering_node(self) -> None:
        if not self.aircraft_node_path:
            logger.warning(f"SIM: Renderer ignoring invalid aircraft id: {self.element_id}")
            return
        self.aircraft_node_path.reparentTo(self.root_np.find("**/aircraft"))
    
    # #################
    # 添加和更新 Sensors
    # #################

    def update_sensor(
            self,
            new_position: Tuple[float, float, float],
            new_heading:float
        ) -> None:
        """更新 sensor 的位置, 这里需要跟随无人机的位置移动
        """
        self.update_element_position_heading(new_position, new_heading)
        for _sensor_id, _sensor in self.sensors.items():
            _sensor.step(self.get_element_pose_from_center())
    
    def get_sensor(self):
        sensor_data = {}
        for _sensor_id, _sensor in self.sensors.items():
            ego_rgb = _sensor()
            sensor_data[_sensor_id] = ego_rgb
        return sensor_data
