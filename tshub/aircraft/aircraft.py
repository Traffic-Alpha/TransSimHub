'''
@Author: WANG Maonan
@Date: 2023-08-23 20:13:01
@Description: Aircraft Object
@LastEditTime: 2023-08-30 15:56:51
'''
import traci
import math
from dataclasses import dataclass, fields
from typing import Tuple, Dict, Any
from loguru import logger

from .aircraft_action_type import aircraft_action_type
from .aircraft_type.stationary import StationaryAction
from .aircraft_type.horizontal_movement import HorizontalMovementAction
from .aircraft_type.vertical_movement import VerticalMovementAction
from .aircraft_type.combined_movement import CombinedMovementAction
from ..utils.get_abs_path import get_abs_path

@dataclass
class AircraftInfo:
    id: str
    action_type: str # aircraft 的动作类型
    position: tuple[float, float, float]
    speed: tuple[float, float, float]
    heading: tuple[float, float, float]
    communication_range: float
    ground_cover_radius: float
    if_sumo_visualization: bool = False
    img_file: str = None
    sumo: traci.connection.Connection = None

    def __post_init__(self) -> None:
        """
        初始化后根据高度更新地面覆盖半径。
        """
        # 初始化 aircraft 的动作类型
        _action = aircraft_action_type(self.action_type)
        if _action == aircraft_action_type.Stationary:
            self.aircraft_action = StationaryAction(id=self.id)
        elif _action == aircraft_action_type.HorizontalMovement:
            self.aircraft_action = HorizontalMovementAction(id=self.id)
        elif _action == aircraft_action_type.VerticalMovement:
            self.aircraft_action = VerticalMovementAction(id=self.id)
        elif _action == aircraft_action_type.CombinedMovement:
            self.aircraft_action = CombinedMovementAction(id=self.id)
        
        # 初始化 aircraft
        self.current_file_path = get_abs_path(__file__)
        self.update_ground_cover_radius() # 更新地面覆盖半径
        self.check_sumo_visualization() # 检查是否需要可视化

    def update_ground_cover_radius(self) -> None:
        """
        根据当前位置的高度更新地面覆盖半径。
            1. 获取 position[2](height) 和 communication_range 的值。
            2. 计算地面覆盖半径：radius = sqrt(communication_range**2 - height**2)
        """
        height = self.position[2]
        if height > self.communication_range:
            self.ground_cover_radius = 0.0
            logger.warning(f'SIM: Aircraft 的高度 {height} 超过了通讯范围 {self.communication_range}.')
        else:
            self.ground_cover_radius = math.sqrt(self.communication_range**2 - height**2)

    def check_sumo_visualization(self) -> None:
        """
        检查是否需要进行 SUMO 可视化设置。
        """
        if self.if_sumo_visualization:
            if self.sumo is None:
                raise ValueError('需要设置 SUMO 连接')
            else:
                x, y = self.position[0], self.position[1]
                if self.img_file is None:
                    self.img_file = self.current_file_path('./aircraft.png')
                self.sumo.poi.add(
                    self.id, x, y, (135, 206, 250, 255), imgFile=self.img_file, width=10, height=10, layer=50
                )
                circle_points = self.get_circle_points()
                self.sumo.polygon.add(self.id, circle_points, (255, 0, 0, 100), layer=50)
                
    def get_circle_points(self, n: int=30) -> list:
        """
        获取圆上的点的坐标。返回当前以 aircraft 为中心，边缘的点坐标

        参数：
        n (int)：采样数，表示圆上的点的数量。

        返回值：
        list：包含圆上每个点的坐标的列表。
        """
        x, y = self.position[0], self.position[1]
        r = self.ground_cover_radius

        points = []
        angle_increment = 2 * math.pi / n

        for i in range(n + 1):
            angle = i * angle_increment
            point_x = x + r * math.cos(angle)
            point_y = y + r * math.sin(angle)
            points.append((point_x, point_y))

        return points
    
    def update_sumo_visualization(self) -> None:
        """更新 SUMO 可视化的结果, 位置
        """
        if self.if_sumo_visualization:
            # Update POI position
            x,y = self.position[0], self.position[1]
            self.sumo.poi.setPosition(self.id, x, y)
            # Update circle position
            circle_points = self.get_circle_points() # 得到圆的坐标
            self.sumo.polygon.setShape(self.id, circle_points)

    @classmethod
    def create(cls, 
            id:str, 
            action_type:str,
            position: Tuple[float, float, float], 
            speed: float, 
            heading: Tuple[float, float, float], 
            communication_range: float,
            if_sumo_visualization: bool = False,
            img_file: str = None,
            sumo = None,
        ):
        """
        创建 AircraftInfo 实例。同时计算出地面的覆盖半径。
        
               * <----- aircraft
               |\
               | \
               |  \ communication_range
               |   \
        height |    \
               |     \
               |      \
               |       \
               |        \
               - - - - - -
               ground_cover_radius

        Args:
            id (str): aircraft ID。
            position (Tuple[float, float, float]): aircraft 的位置坐标。
            speed (float): aircraft 的速度。
            heading (Tuple[float, float, float]): aircraft 的航向。
            communication_range (float): aircraft 的通信范围。

        Returns:
            AircraftInfo: 创建的 AircraftInfo 实例。
        """
        logger.info(f'SIM: Init Aircraft: {id}.')
        aircraft = cls(
            id, action_type, position, speed, heading, communication_range, 0.0, 
            if_sumo_visualization, img_file, sumo
        )
        aircraft.update_ground_cover_radius()
        return aircraft
    
    def update_features(self, position:Tuple[float, float, float], speed:float, heading:Tuple[float, float, float]) -> None:
        self.position = position
        self.speed = speed
        self.heading = heading

    def get_features(self) -> Dict[str, Any]:
        output_dict = {}
        for field in fields(self):
            field_name = field.name
            field_value = getattr(self, field_name)
            if field_name != 'sumo':
                output_dict[field_name] = field_value
        return output_dict

    def control_aircraft(self, action) -> None:
        speed, heading_index = action
        new_position, heading = self.aircraft_action.execute(
            position=self.position,
            speed=speed, heading_index=heading_index
        )
        self.update_features(new_position, speed, heading)
        self.update_ground_cover_radius() # 更新地面可视化范围
        self.update_sumo_visualization() # 更新可视化结果