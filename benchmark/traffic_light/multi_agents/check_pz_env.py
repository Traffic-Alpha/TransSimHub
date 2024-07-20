'''
@Author: WANG Maonan
@Date: 2023-10-31 18:59:34
@Description: 检查 TSC PZ Env 环境, 尝试多次 reset
@LastEditTime: 2024-04-24 21:01:52
'''
import numpy as np
from loguru import logger

from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.utils.format_dict import dict_to_str

from typing import List
from env_utils.tsc_env import TSCEnvironment
from env_utils.tsc_wrapper import TSCEnvWrapper
from env_utils.pz_env import TSCEnvironmentPZ

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

def make_multi_envs(
        tls_ids:List[str], sumo_cfg:str, 
        num_seconds:int, use_gui:bool,
        filepath:str
    ):
    tsc_env = TSCEnvironment(
        sumo_cfg=sumo_cfg,
        num_seconds=num_seconds,
        tls_ids=tls_ids,
        tls_action_type='choose_next_phase_syn',
        use_gui=use_gui
    )
    tsc_env = TSCEnvWrapper(tsc_env, filepath=filepath)
    tsc_env = TSCEnvironmentPZ(tsc_env)

    return tsc_env

if __name__ == '__main__':
    sumo_cfg = path_convert("../../sumo_envs/multi_junctions_tsc/env/three_junctions.sumocfg")
    log_path = path_convert('./log/tsc_pz_env')
    env = make_multi_envs(
        tls_ids=["J1", "J2", "J3"],
        sumo_cfg=sumo_cfg,
        num_seconds=1600,
        use_gui=True,
        filepath=log_path
    )

    for _ in range(3):
        state, info = env.reset()
        logger.info(f'RL-Init State: {dict_to_str(state)}')
        logger.info(f'RL-Init Info: {dict_to_str(info)}')
        dones = False
        while not dones:
            random_action = {_tls_id:np.random.randint(2) for _tls_id in ["J1", "J2", "J3"]}
            observations, rewards, terminations, truncations, infos = env.step(random_action)
            dones = all(terminations.values())
    env.close()
