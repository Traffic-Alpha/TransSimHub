'''
@Author: WANG Maonan
@Date: 2023-10-27 20:16:40
@Description: 基础车辆环境
@LastEditTime: 2023-10-27 20:30:04
'''
import gymnasium as gym

from typing import Dict
from tshub.tshub_env.tshub_env import TshubEnvironment

class VehEnvironment(gym.Env):
    def __init__(self, 
                 sumo_cfg:str, num_seconds:int, 
                 vehicle_action_type:str, use_gui:bool=False
        ) -> None:
        super().__init__()

        self.tsc_env = TshubEnvironment(
            sumo_cfg=sumo_cfg,
            is_vehicle_builder_initialized=True, # 只需要获得车辆的信息
            is_aircraft_builder_initialized=False, 
            is_traffic_light_builder_initialized=False,
            vehicle_action_type=vehicle_action_type,
            num_seconds=num_seconds,
            use_gui=use_gui,
            is_libsumo=(not use_gui), # 如果不开界面, 就是用 libsumo
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