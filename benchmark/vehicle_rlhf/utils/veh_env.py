'''
@Author: WANG Maonan
@Date: 2023-10-27 20:16:40
@Description: 基础车辆环境
@LastEditTime: 2023-11-20 16:14:05
'''
import gymnasium as gym

from typing import Dict
from tshub.tshub_env.tshub_env import TshubEnvironment

class VehEnvironment(gym.Env):
    def __init__(self, 
                 sumo_cfg:str, net_file:str,
                 num_seconds:int, 
                 vehicle_action_type:str, use_gui:bool=False
        ) -> None:
        super().__init__()

        self.tsc_env = TshubEnvironment(
            sumo_cfg=sumo_cfg,
            net_file=net_file,
            is_map_builder_initialized=True, # 获得地图信息
            is_vehicle_builder_initialized=True, # 要获得车辆的信息
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
    
    def render(self, mode:str='rgb',
               focus_id:str=None, focus_type:str=None, focus_distance:float=None, 
               save_folder:str=None
            ):
        return self.tsc_env.render(mode, focus_id, focus_type, focus_distance, save_folder)
    
    def close(self) -> None:
        self.tsc_env._close_simulation()