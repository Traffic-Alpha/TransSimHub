'''
@Author: WANG Maonan
@Date: 2024-07-08 22:21:18
@Description: 3D 场景内的车辆
@LastEditTime: 2024-07-08 23:14:18
'''
import numpy as np
from pathlib import Path
from loguru import logger
from typing import Tuple, Union, Optional, Dict, Any

from .base_element import BaseElement
from ...vis3d_utils.colors import Colors, SceneColors
from ...vis3d_utils.coordinates import Pose, Heading
from ...vis3d_utils.masks import RenderMasks

class Vehicle3DElement(BaseElement):
    def __init__(
            self, 
            tshub_render,
            veh_id: str,
            veh_type: str,
            veh_pos: Tuple[float, float],
            veh_heading: float,
            veh_length: float,
            glb_model: Union[str, Path],
            color: Union[Colors, SceneColors]=Colors.BlueTransparent,
            interest_color: Optional[Union[Colors, SceneColors]]=SceneColors.Agent
        ) -> None:
        super().__init__(tshub_render)
        self.veh_id = veh_id # 车辆的 id
        self.veh_type = veh_type # 车辆的类型, 对 ego 车辆特殊处理
        self.veh_pos_sumo = veh_pos # 车辆的位置 (SUMO 中的坐标)
        self.veh_heading = veh_heading
        self.veh_length = veh_length
        self.glb_model = glb_model # 车辆的模型
        self.color = color # 车辆的颜色
        self.interest_color = interest_color # color for ego vehicles
    
    # ###################
    # Vehicle Node 的更新
    # ###################
    def create_node(self) -> bool:
        """Create a vehicle node.
        """        
        node_path = self.tshub_render._showbase_instance.loader.loadModel(self.glb_model)
        node_path.setName("vehicle-%s" % self.veh_id)
        if (
            'ego' in self.veh_type
            and self.interest_color is not None
        ): # 如果是 ego 车, 则使用不一样的颜色
            node_path.setColor(self.interest_color.value)
        else:
            node_path.setColor(self.color.value)

        pose = Pose.from_front_bumper(
            front_bumper_position=np.array(self.veh_pos_sumo),
            heading=Heading.from_sumo(self.veh_heading),
            length=self.veh_length,
        ) # 车辆坐标转换
        pos, heading = pose.as_panda3d() # 转换为位置和角度
        node_path.setPosHpr(*pos, heading, 0, 0)
        node_path.hide(RenderMasks.DRIVABLE_AREA_HIDE)
        
        self.tshub_render._vehicle_nodes[self.veh_id] = node_path # 修改可变对象
        return True
    
    def update_node(
            self, 
            veh_position:Tuple[float],
            veh_heading: float,
        ) -> None:
        """Move the specified vehicle node. (更新车辆的位置)
        """
        vehicle_path = self.tshub_render._vehicle_nodes.get(self.veh_id, None)
        if not vehicle_path:
            logger.warning(f"SIM: Renderer ignoring invalid vehicle id: {self.veh_id}")
            return

        pose = Pose.from_front_bumper(
            front_bumper_position=np.array(veh_position),
            heading=Heading.from_sumo(veh_heading),
            length=self.veh_length,
        ) # 坐标转换
        pos, heading = pose.as_panda3d()
        vehicle_path.setPosHpr(*pos, heading, 0, 0)

    def remove_node(self) -> None:
        """Remove a vehicle node
        """
        vehicle_path = self.tshub_render._vehicle_nodes.get(self.veh_id, None)
        if not vehicle_path:
            logger.warning(f"SIM: Renderer ignoring invalid vehicle id: {self.veh_id}")
            return
        vehicle_path.removeNode()
        del self.tshub_render._vehicle_nodes[self.veh_id]
        
    def begin_rendering_node(self) -> None:
        """Add the vehicle node to the scene graph
        """
        vehicle_path = self.tshub_render._vehicle_nodes.get(self.veh_id, None)
        if not vehicle_path:
            logger.warning(f"SIM: Renderer ignoring invalid vehicle id: {self.veh_id}")
            return
        vehicle_path.reparentTo(self.tshub_render._vehicles_np) # 连接到 TSHub Render 的根节点