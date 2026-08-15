'''
@Author: WANG Maonan
@Date: 2024-08-10 21:39:37
@Description: 同时控制车辆和信号灯
@LastEditTime: 2024-08-11 20:18:02
'''
import gymnasium as gym

from typing import Dict, List
from tshub.tshub_env.tshub_env import TshubEnvironment

class MixFlowEnvironment(gym.Env):
    def __init__(self, 
                 sumo_cfg:str, num_seconds:int, 
                 tls_ids:List[str],
                 vehicle_action_type:str='speed', 
                 tls_action_type:str='choose_next_phase_syn',
                 use_gui:bool=False,
                 trip_info: str = None  # 添加 trip_info 参数

        ) -> None:
        super().__init__()
        self.num_seconds = num_seconds  # 将 num_seconds 保存为一个属性

        self.tsc_env = TshubEnvironment(
            sumo_cfg=sumo_cfg,
            is_vehicle_builder_initialized=True, # 控制车
            is_aircraft_builder_initialized=False, 
            is_traffic_light_builder_initialized=True, # 控制信号灯
            is_map_builder_initialized=False,
            is_person_builder_initialized=False,
            vehicle_action_type=vehicle_action_type,
            tls_ids=tls_ids,
            tls_action_type=tls_action_type,
            num_seconds=num_seconds,
            use_gui=use_gui,
            is_libsumo=(not use_gui), # 如果不开界面, 就是用 libsumo
            trip_info=trip_info,
            # collision_action="warn"
        )

    def reset(self):
        state_infos = self.tsc_env.reset()
        return state_infos
        
    def step(self, action:Dict[str, Dict[str, int]]):
        states, rewards, infos, dones = self.tsc_env.step(action)
        truncated = dones

        return states, rewards, truncated, dones, infos
    
    def close(self) -> None:
        self.tsc_env._close_simulation()