'''
@Author: WANG Maonan
@Date: 2024-05-29 16:24:36
@Description: 控制飞行器, state 包含坐标的 snir 数值
@LastEditTime: 2024-05-29 16:56:30
'''
import gymnasium as gym

from typing import Dict, Any
from tshub.tshub_env.tshub_env import TshubEnvironment

class ACSNIREnvironment(gym.Env):
    def __init__(self, 
                 sumo_cfg:str, num_seconds:int, 
                 aircraft_inits:Dict[str, Any], net_file:str, radio_map_files:Dict[str, str], 
                 use_gui:bool=False
        ) -> None:
        super().__init__()

        self.tsc_env = TshubEnvironment(
            sumo_cfg=sumo_cfg,
            is_aircraft_builder_initialized=True, 
            is_vehicle_builder_initialized=False,
            is_map_builder_initialized=True,
            is_traffic_light_builder_initialized=False,
            net_file=net_file,
            radio_map_files=radio_map_files,
            aircraft_inits=aircraft_inits, 
            num_seconds=num_seconds,
            use_gui=use_gui,
            is_libsumo=(not use_gui), # 如果不开界面, 就是用 libsumo
        )

    def reset(self):
        state_infos = self.tsc_env.reset()
        return state_infos
        
    def step(self, action:Dict[str, Dict[str, int]]):
        action = {'aircraft': action} # 这里只控制 aircraft 即可
        states, rewards, infos, dones = self.tsc_env.step(action)
        truncated = dones # 这里的 done 你需要自己计算

        return states, rewards, truncated, dones, infos
    
    def close(self) -> None:
        self.tsc_env._close_simulation()