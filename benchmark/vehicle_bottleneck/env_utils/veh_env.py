'''
@Author: Liu Lu & WANG Maonan
@Date: 2023-10-27 20:16:40
@Description: 基础车辆环境
@LastEditTime: 2023-12-16 22:22:16
'''
import gymnasium as gym

from typing import Dict
from tshub.tshub_env.tshub_env import TshubEnvironment

class VehEnvironment(gym.Env):
    def __init__(self, 
                 sumo_cfg:str, num_seconds:int, 
                 vehicle_action_type:str, use_gui:bool=False,
                 trip_info: str = None  # 添加 trip_info 参数

        ) -> None:
        super().__init__()
        self.num_seconds = num_seconds  # 将 num_seconds 保存为一个属性

        self.tsc_env = TshubEnvironment(
            sumo_cfg=sumo_cfg,
            is_vehicle_builder_initialized=True,  # 只需要获得车辆的信息
            is_aircraft_builder_initialized=False, 
            is_traffic_light_builder_initialized=False,
            is_map_builder_initialized=False,
            is_person_builder_initialized=False,
            vehicle_action_type=vehicle_action_type,
            num_seconds=num_seconds,
            use_gui=use_gui,
            is_libsumo=(not use_gui),  # 如果不开界面, 就是用 libsumo
            trip_info=trip_info
        )

    def reset(self):
        state_infos = self.tsc_env.reset()
        return state_infos
        
    def step(self, action:Dict[str, Dict[str, int]]):
        action = {'vehicle': action}
        states, rewards, infos, dones = self.tsc_env.step(action)
        truncated = dones

        return states, rewards, truncated, dones, infos
    
    def close(self) -> None:
        self.tsc_env._close_simulation()