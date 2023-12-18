'''
@Author: WANG Maonan
@Date: 2023-12-18 18:02:07
@Description: 
@LastEditTime: 2023-12-18 20:48:38
'''
'''
@Author: WANG Maonan
@Date: 2023-10-31 18:59:34
@Description: 检查 TSC PZ Env 环境, 尝试多次 reset
@LastEditTime: 2023-11-01 12:45:04
'''
import numpy as np
from loguru import logger

from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.utils.format_dict import dict_to_str

from typing import List, Dict, Tuple
from env_utils.veh_env import VehEnvironment
from env_utils.veh_wrapper import VehEnvWrapper
from env_utils.pz_veh_env import VehEnvironmentPZ

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

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
        use_gui=use_gui
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

    return veh_env


if __name__ == '__main__':
    sumo_cfg = path_convert("../sumo_envs/veh_bottleneck/veh.sumocfg")
    log_path = path_convert('./log/tsc_pz_env')

    env = make_multi_envs(
        sumo_cfg=sumo_cfg,
        warmup_steps=100,
        num_seconds=1200,
        ego_ids=[
            'E0__0__ego.1', 
            'E0__1__ego.2', 
            'E0__2__ego.3',
        ], # ego vehicle 的 id
        edge_ids=['E0','E1','E2'],
        edge_lane_num={
            'E0':4,
            'E1':4,
            'E2':4
        }, # 每一个 edge 对应的车道数
        bottle_necks=['E2'], # bottleneck 的 edge id
        bottle_neck_positions=(700, 70), # bottle neck 的坐标, 用于计算距离
        calc_features_lane_ids=[
            'E0_0', 'E0_1', 'E0_2', 'E0_3',
            'E1_0', 'E1_1', 'E1_2', 'E1_3',
            'E2_0', 'E2_1', 'E2_2', 'E2_3',
        ], # 计算对应的 lane 的信息        
        use_gui=True,
        log_file=log_path
    )

    for _ in range(3):
        state, info = env.reset()
        logger.info(f'RL-Init State: {dict_to_str(state)}')
        logger.info(f'RL-Init Info: {dict_to_str(info)}')
        dones = False
        while not dones:
            action = {ego_id: 5 for ego_id in env.agents}
            observations, rewards, terminations, truncations, infos = env.step(action)
            dones = all(terminations.values())
    env.close()