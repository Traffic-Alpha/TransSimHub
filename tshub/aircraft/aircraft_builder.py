'''
@Author: WANG Maonan
@Date: 2023-08-23 20:13:10
@Description: This module provides the AircraftBuilder class for creating and controlling aircraft.
@LastEditTime: 2023-09-25 14:17:33
'''
import traci
from typing import Dict, Tuple

from .aircraft import AircraftInfo
from ..tshub_env.base_builder import BaseBuilder

class AircraftBuilder(BaseBuilder):
    def __init__(self, 
                 sumo: traci.connection.Connection, 
                 aircraft_inits: Dict[str, Dict[str, any]]={}) -> None:
        """
        初始化 AircraftBuilder 类的实例。

        Args:
            sumo (traci.connection.Connection): sumo 的连接 
            aircraft_inits (Dict[str, Dict[str, any]], optional): 航空器的初始参数字典。默认为 None。
                下面是一个例子，包含 aircraft 的 id, 和初始位置, 初始速度, 初始 heading 角度, 和通讯距离：
                aircraft_inits = {
                    'a1': {
                        "action_type": "horizontal_movement", 
                        "position":(10,10,10), "speed":10, "heading":(1,1,0), "communication_range":100, 
                        "if_sumo_visualization":True, "img_file":None, "color":(0,255,0),
                        "custom_update_cover_radius":custom_update_cover_radius # 使用自定义的计算
                    },
                    'a2': {
                        "action_type": "horizontal_movement", 
                        "position":(10,10,100), "speed":10, "heading":(1,1,0), "communication_range":100, 
                        "if_sumo_visualization":True, "img_file":None, "color":(0,255,0),
                        "custom_update_cover_radius":None
                    }
                }
        """
        self.aircraft_dict = {} # 存储每一个 aircraft 的类
        for _aircraft_id, _aircraft_parameter in aircraft_inits.items():
            self.create_objects(id=_aircraft_id, sumo=sumo, **_aircraft_parameter)

    def create_objects(
            self, id:str, aircraft_type:str,
            action_type:str, 
            position: Tuple[float, float, float], 
            speed: float, 
            heading: Tuple[float, float, float], 
            communication_range: float,
            if_sumo_visualization: bool = False,
            color: Tuple[int,int,int] = tuple([255, 0, 0]),
            img_file: str = None,
            custom_update_cover_radius = None,
            sumo = None,
        ) -> None:
        """
        创建 aircraft 并将其添加到 aircraft_dict 中。

        Args:
            id (str): aircraft ID。
            position (Tuple[float, float, float]): aircraft 的位置坐标。
            speed (float): aircraft 的速度。
            heading (Tuple[float, float, float]): aircraft 的航向。
            communication_range (float): aircraft 的通信范围。

        Returns:
            None
        """
        aircraft = AircraftInfo.create(
            id, aircraft_type, action_type, 
            position, speed, heading, communication_range,
            if_sumo_visualization, color, 
            img_file, custom_update_cover_radius,
            sumo,
        )
        self.aircraft_dict[id] = aircraft

    def get_objects_infos(self) -> Dict[str, dict]:
        """
        获取所有 aircraft 的信息。

        Returns:
            Dict[str, dict]: 包含所有 aircraft 信息的字典。
        """
        all_aircraft_data = {
            aircraft_id: aircraft.get_features()
            for aircraft_id, aircraft in self.aircraft_dict.items()
        }
        return all_aircraft_data
    
    def control_objects(self, actions: Dict[str, Tuple[float, Tuple[float, float, float]]]) -> None:
        """
        控制 aircraft 的行为。

        Args:
            actions (Dict[str, Tuple[float, Tuple[float, float, float]]]): 包含 aircraft ID和对应行为的字典。
                下面是一个可行的输入，分别给出每个 aircraft 的 (speed, heading_index)
                actions = {
                    "a1": (1, 1),
                    "a2": (10, 2),
                }

        Returns:
            None
        """
        for _aircraft_id, _action in actions.items():
            self.aircraft_dict[_aircraft_id].control_aircraft(_action)
    
    def update_objects_state(self):
        raise NotImplementedError