'''
@Author: WANG Maonan
@Date: 2023-08-23 20:13:10
@Description: This module provides the AircraftBuilder class for creating and controlling aircraft.
@LastEditTime: 2023-08-29 20:57:39
'''
from dataclasses import asdict
from typing import Dict, Tuple
from loguru import logger

from .aircraft import AircraftInfo

class AircraftBuilder:
    def __init__(self, aircraft_inits: Dict[str, Dict[str, any]]={}) -> None:
        """
        初始化 AircraftBuilder 类的实例。

        Args:
            aircraft_inits (Dict[str, Dict[str, any]], optional): 航空器的初始参数字典。默认为 None。
                下面是一个例子，包含 aircraft 的 id, 和初始位置, 初始速度, 初始 heading 角度, 和通讯距离：
                aircraft_inits = {
                    'a1': {
                        "position":(10,10,10), "speed":10, "heading":(1,1,0), "communication_range":100, 
                        "if_sumo_visualization":True, "sumo":conn, "img_file":None
                    },
                    'a2': {
                        "position":(10,10,100), "speed":10, "heading":(1,1,0), "communication_range":100, 
                        "if_sumo_visualization":True, "sumo":conn, "img_file":None
                    }
                }
        """
        self.aircraft_dict = {}
        for _aircraft_id, _aircraft_parameter in aircraft_inits.items():
            self.create_aircraft(id=_aircraft_id, **_aircraft_parameter)

    def create_aircraft(
            self, id:str, 
            action_type:str, 
            position: Tuple[float, float, float], 
            speed: float, 
            heading: Tuple[float, float, float], 
            communication_range: float,
            if_sumo_visualization: bool = False,
            img_file: str = None,
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
            id, action_type, 
            position, speed, heading, communication_range,
            if_sumo_visualization, img_file, sumo
        )
        self.aircraft_dict[id] = aircraft

    def get_aircraft_info(self) -> Dict[str, dict]:
        """
        获取所有 aircraft 的信息。

        Returns:
            Dict[str, dict]: 包含所有 aircraft 信息的字典。
        """
        all_aircraft_data = {
            aircraft_id: asdict(aircraft)
            for aircraft_id, aircraft in self.aircraft_dict.items()
        }
        return all_aircraft_data
    
    def control_aircrafts(self, actions: Dict[str, Tuple[float, Tuple[float, float, float]]]) -> None:
        """
        控制 aircraft 的行为。

        Args:
            actions (Dict[str, Tuple[float, Tuple[float, float, float]]]): 包含 aircraft ID和对应行为的字典。
                下面是一个可行的输入，分别给出每个 aircraft 的 (speed, heading)
                actions = {
                    "a1": (1, (1,1,0)),
                    "a2": (10, (1,1,0)),
                }

        Returns:
            None
        """
        for _aircraft_id, _action in actions.items():
            speed, heading = _action
            self._control_single_aircraft(_aircraft_id, speed, heading)

    def _control_single_aircraft(self, aircraft_id: str, speed: float, heading: Tuple[float, float, float]) -> None:
        """
        控制单个 aircraft 的行为。

        Args:
            aircraft_id (str): aircraft ID。
            speed (float): aircraft 的速度。
            heading (Tuple[float, float, float]): aircraft 的航向。

        Returns:
            None
        """
        aircraft = self.aircraft_dict[aircraft_id]
        aircraft.speed = speed
        aircraft.heading = heading
        # 根据给定的速度和航向计算新的位置
        new_position = (
            aircraft.position[0] + speed * heading[0],
            aircraft.position[1] + speed * heading[1],
            aircraft.position[2] + speed * heading[2]
        )
        # 确保高度不小于0
        if new_position[2] >= 0:
            aircraft.position = new_position
            aircraft.update_ground_cover_radius() # 更新 ground cover radius
        else:
            logger.warning(f'SIM: Aircraft 的高度不能小于 0, 现在高度为 {new_position[2]}.')
            logger.warning('SIM: Aircraft 的位置不变.')
        # 如果开启可视化, 更新 aircraft 在地图上的位置
        aircraft.update_sumo_visualization()