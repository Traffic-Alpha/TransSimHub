'''
@Author: WANG Maonan
@Date: 2023-08-25 11:22:43
@Description: 定义每一个 traffic light 的信息
@LastEditTime: 2023-08-25 20:03:06
'''
from __future__ import annotations

import traci
from loguru import logger
from dataclasses import dataclass
from typing import List, Dict


from .traffic_light_action_type import tls_action_type
from .tls_type.choose_next_phase import choose_next_phase
from .tls_type.next_or_not import next_or_not

@dataclass
class TrafficLightInfo:
    id: str
    action_type: str
    last_step_mean_speed: List[float]
    jam_length_vehicle: List[float]
    jam_length_meters: List[float]
    last_step_occupancy: List[float]
    this_phase: List[bool]
    last_phase: List[bool]
    next_phase: List[bool]
    sumo: traci.connection.Connection # 与 sumo 的 connection
    movement_directions: Dict[str, str] = None, # 每一个 movement 的方向
    movement_lane_numbers: List[int] = None, # 每一个 movement 包含的车道数
    movement_info: List[str] = None # 存储 movement (不包含右转)
    phase2movements: Dict[int, List[str]] = None # 记录每个 phase 控制的 connection
    # 存储现在是在哪一个 phase

    def __post_init__(self) -> None:
        _action = tls_action_type(self.action_type)
        if _action == tls_action_type.ChooseNextPhase:
            self.tls_action = choose_next_phase(ts_id=self.id, sumo=self.sumo)
        elif _action == tls_action_type.NextorNot:
            self.tls_action = next_or_not(ts_id=self.id, sumo=self.sumo)
        else:
            logger.error(f'信号灯动作只支持 choose_next_phase 和 next_or_not, 现在是 {self.action_type}.')
            raise ValueError(f'信号灯动作只支持 choose_next_phase 和 next_or_not, 现在是 {self.action_type}.')
        self.tls_action.build_phases()
        self.phase2movements = self.tls_action.controled_phase_movements()
        self.movement_info, self.movement_directions, self.movement_lane_numbers = self.tls_action.get_movements_infos()

    @classmethod
    def create_traffic_light(
            cls, id, action_type,
            last_step_mean_speed, jam_length_vehicle, jam_length_meters, last_step_occupancy,
            this_phase, last_phase, next_phase,
            sumo) -> TrafficLightInfo:
        """
        创建交通信号灯
        """
        return cls(id, action_type,
                   last_step_mean_speed, jam_length_vehicle, jam_length_meters, last_step_occupancy,
                   this_phase, last_phase, next_phase, sumo)

    def update_features(self, tls_data):
        """
        更新交通信号灯的属性
        """
        print(1)
        pass

    def process_feature(self, raw_feature):
        """
        对原始特征进行处理，用于更新特征
        """
        # 在此处编写处理原始特征的代码
        pass

    def get_feature(self):
        """
        返回交通信号灯的特征
        """
        # 在此处编写返回交通信号灯特征的代码
        pass

    def control_traffic_light(self):
        """
        控制交通信号灯
        """
        # 在此处编写控制交通信号灯的代码
        pass