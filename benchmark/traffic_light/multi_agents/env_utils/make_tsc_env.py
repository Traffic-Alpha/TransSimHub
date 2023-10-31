'''
@Author: WANG Maonan
@Date: 2023-10-30 19:34:54
@Description: Create Multi-Junctions Environment
@LastEditTime: 2023-10-31 23:30:03
'''
from typing import List
from env_utils.tsc_env import TSCEnvironment
from env_utils.tsc_wrapper import TSCEnvWrapper
from env_utils.pz_env import TSCEnvironmentPZ

from torchrl.envs import (
    ParallelEnv, 
    EnvCreator, 
    TransformedEnv,
    RewardSum,
    VecNorm
)
from torchrl.envs.libs.vmas import VmasEnv

from torchrl.envs.libs.pettingzoo import PettingZooWrapper

def make_multi_envs(
        tls_ids:List[str], sumo_cfg:str, 
        num_seconds:int, use_gui:bool,
        log_file:str, env_index:int,
        device:str='cpu'
    ):
    tsc_env = TSCEnvironment(
        sumo_cfg=sumo_cfg,
        num_seconds=num_seconds,
        tls_ids=tls_ids,
        tls_action_type='choose_next_phase',
        use_gui=use_gui
    )
    tsc_env = TSCEnvWrapper(tsc_env, filepath=log_file, env_id=env_index)
    tsc_env = TSCEnvironmentPZ(tsc_env)
    tsc_env = PettingZooWrapper(
        tsc_env, 
        group_map={'agents':tls_ids},
        categorical_actions=False,
        device=device
    )
    tsc_env = TransformedEnv(tsc_env)
    tsc_env.append_transform(RewardSum(in_keys=[tsc_env.reward_key]))
    tsc_env.append_transform(VecNorm(in_keys=[tsc_env.reward_key]))

    return tsc_env

def make_parallel_env(
        num_envs:int,
        tls_ids:List[str], sumo_cfg:str, 
        num_seconds:int, use_gui:bool,
        log_file:str, test:bool=False,
        device:str='cpu'
    ):
    if test:
        env = ParallelEnv(
            num_workers=num_envs, 
            create_env_fn=[
                (lambda i=i: make_multi_envs(tls_ids, sumo_cfg, num_seconds, use_gui, log_file=log_file+f'/test_{i}.log', env_index=f'{i}', device=device))
                for i in range(num_envs)
            ],
        )
    else:
        env = ParallelEnv(
            num_workers=num_envs, 
            create_env_fn=[
                (lambda i=i: make_multi_envs(tls_ids, sumo_cfg, num_seconds, use_gui, log_file=log_file+f'/{i}.log', env_index=f'{i}', device=device))
                for i in range(num_envs)
            ],
        )
    
    # env = TransformedEnv(env)
    # env.append_transform(RewardSum(in_keys=[env.reward_key]))
    # env.append_transform(VecNorm(in_keys=[env.reward_key]))

    return env