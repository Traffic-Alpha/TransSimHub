'''
@Author: WANG Maonan
@Date: 2023-12-21 14:38:40
@Description: 检查 Ego Env 是否正常工作
@LastEditTime: 2023-12-21 18:14:15
'''
import numpy as np
from loguru import logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from stable_baselines3.common.env_checker import check_env

from utils.make_veh_env import make_env

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))


if __name__ == '__main__':
    sumo_cfg = path_convert("../../sumo_envs/veh_bottleneck/veh.sumocfg")
    log_path = path_convert('./log/check')
    ego_env_generate = make_env(
        sumo_cfg=sumo_cfg,
        num_seconds= 650,
        use_gui=True,
        warmup_steps=80, 
        ego_ids=[
            'E0__0__ego.1', 
            'E0__1__ego.2', 
            'E0__2__ego.3',
        ], # ego vehicle 的 id
        out_edge_ids=['E3'], # ego 进入这里就不控制了
        bottle_necks=['E2'], # bottleneck 的 edge id
        bottle_neck_positions=(700, 70), # bottle neck 的坐标, 用于计算距离
        calc_features_lane_ids=[
            'E0_0', 'E0_1', 'E0_2', 'E0_3',
            'E1_0', 'E1_1', 'E1_2', 'E1_3',
            'E2_0', 'E2_1', 'E2_2', 'E2_3',
        ], # 计算对应的 lane 的信息
        env_index=0,
        log_file=log_path
    )
    ego_env = ego_env_generate()
    
    # Check Env
    print(ego_env.observation_space)
    print(ego_env.action_space)
    check_env(ego_env)

    # Simulation with environment
    dones = False
    ego_env.reset()
    while not dones:
        action = np.random.randint([2,2,2])
        states, rewards, truncated, dones, infos = ego_env.step(action=action)
        logger.info(f"SIM: {infos['step_time']} \n+State:{states}; \n+Reward:{rewards}.")
    ego_env.close()