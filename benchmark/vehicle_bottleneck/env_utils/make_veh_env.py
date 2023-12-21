'''
@Author: WANG Maonan
@Date: 2023-12-18 17:26:56
@Description: Make Parallel Env
@LastEditTime: 2023-12-20 20:01:04
'''
from typing import List, Dict, Tuple
from env_utils.veh_env import VehEnvironment
from env_utils.veh_wrapper import VehEnvWrapper
from env_utils.pz_veh_env import VehEnvironmentPZ

from torchrl.envs import (
    ParallelEnv, 
    TransformedEnv,
    RewardSum,
    VecNorm
)
from torchrl.envs.libs.pettingzoo import PettingZooWrapper

def make_multi_envs(
        sumo_cfg:str,
        ego_ids:List[str], edge_ids:List[str],
        edge_lane_num:Dict[str, int],
        calc_features_lane_ids:List[str],
        bottle_necks:List[str],
        bottle_neck_positions:Tuple[float],
        warmup_steps:int,
        num_seconds:int, use_gui:bool,
        log_file:str, device:str='cpu'
    ):
    veh_env = VehEnvironment(
        sumo_cfg=sumo_cfg,
        num_seconds=num_seconds,
        vehicle_action_type='lane_continuous_speed',
        use_gui=use_gui,
    )
    veh_env = VehEnvWrapper(
        env=veh_env, 
        warmup_steps=warmup_steps,
        ego_ids=ego_ids,
        edge_ids=edge_ids,
        edge_lane_num=edge_lane_num,
        bottle_necks=bottle_necks,
        bottle_neck_positions=bottle_neck_positions,
        calc_features_lane_ids=calc_features_lane_ids,
        filepath=log_file
    )
    veh_env = VehEnvironmentPZ(veh_env)
    veh_env = PettingZooWrapper(
        veh_env, 
        group_map={'agents':ego_ids},
        categorical_actions=False,
        device=device
    )
    veh_env = TransformedEnv(veh_env)
    veh_env.append_transform(RewardSum(in_keys=[veh_env.reward_key]))
    veh_env.append_transform(VecNorm(in_keys=[veh_env.reward_key]))

    return veh_env

def make_parallel_env(
        num_envs:int,
        sumo_cfg:str,
        ego_ids:List[str], edge_ids:List[str],
        edge_lane_num:Dict[str, int],
        calc_features_lane_ids:List[str],
        bottle_necks:List[str],
        bottle_neck_positions:Tuple[float],
        warmup_steps:int,
        num_seconds:int, use_gui:bool,
        log_file:str, device:str='cpu',
        prefix:str=None,
    ):
    if prefix is None:
        env = ParallelEnv(
            num_workers=num_envs, 
            create_env_fn=[
                (lambda i=i: make_multi_envs(
                    sumo_cfg, ego_ids, edge_ids, edge_lane_num,
                    calc_features_lane_ids, bottle_necks, bottle_neck_positions, 
                    warmup_steps, num_seconds, use_gui, log_file=log_file+f'/{i}', device=device
                ))
                for i in range(num_envs)
            ],
        )
    else:
        env = ParallelEnv(
            num_workers=num_envs, 
            create_env_fn=[
                (lambda i=i: make_multi_envs(
                    sumo_cfg, ego_ids, edge_ids, edge_lane_num,
                    calc_features_lane_ids, bottle_necks, bottle_neck_positions, 
                    warmup_steps, num_seconds, use_gui, log_file=log_file+f'/{prefix}_{i}', 
                    device=device
                ))
                for i in range(num_envs)
            ],
        )

    return env