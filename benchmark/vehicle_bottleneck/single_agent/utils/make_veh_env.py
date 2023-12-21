'''
@Author: WANG Maonan
@Date: 2023-12-21 14:42:14
@Description: veh_env + veh_wrapper
@LastEditTime: 2023-12-21 16:37:35
'''
import gymnasium as gym

from typing import List, Dict, Tuple
from utils.veh_env import VehEnvironment
from utils.veh_wrapper import VehEnvWrapper
from stable_baselines3.common.monitor import Monitor

def make_env(
        sumo_cfg:str,
        num_seconds:int, warmup_steps:int, 
        ego_ids:List[str], out_edge_ids:List[str], bottle_necks:List[str],
        bottle_neck_positions:Tuple[int],
        calc_features_lane_ids:List[str], use_gui:bool,
        log_file:str, env_index:int,
        trip_info:str=None
        ):
    def _init() -> gym.Env: 
        veh_env = VehEnvironment(
            sumo_cfg=sumo_cfg, 
            num_seconds=num_seconds,
            vehicle_action_type='lane_continuous_speed',
            use_gui=use_gui,
            trip_info=trip_info,
        )
        tsc_wrapper = VehEnvWrapper(
            env=veh_env, 
            warmup_steps=warmup_steps, 
            ego_ids=ego_ids,
            out_edge_ids=out_edge_ids,
            bottle_necks=bottle_necks,
            bottle_neck_positions=bottle_neck_positions,
            calc_features_lane_ids=calc_features_lane_ids
        )
        return Monitor(tsc_wrapper, filename=f'{log_file}/{env_index}')
    
    return _init