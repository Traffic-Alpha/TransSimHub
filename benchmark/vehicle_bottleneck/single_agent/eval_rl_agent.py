'''
@Author: WANG Maonan
@Date: 2023-09-08 18:57:35
@Description: 使用训练好的 RL Agent 进行测试
@LastEditTime: 2023-12-21 18:22:47
'''
import torch
from loguru import logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecNormalize, SubprocVecEnv

from utils.make_veh_env import make_env

path_convert = get_abs_path(__file__)
logger.remove()

if __name__ == '__main__':
    # #########
    # Init Env
    # #########
    sumo_cfg = path_convert("../../sumo_envs/veh_bottleneck/veh.sumocfg")
    params = {
        'sumo_cfg':sumo_cfg,
        'num_seconds': 650,
        'use_gui':True,
        'warmup_steps':80, 
        'ego_ids':[
            'E0__0__ego.1', 
            'E0__1__ego.2', 
            'E0__2__ego.3',
        ], # ego vehicle 的 id
        'out_edge_ids':['E3'], # ego 进入这里就不控制了
        'bottle_necks':['E2'], # bottleneck 的 edge id
        'bottle_neck_positions':(700, 70), # bottle neck 的坐标, 用于计算距离
        'calc_features_lane_ids':[
            'E0_0', 'E0_1', 'E0_2', 'E0_3',
            'E1_0', 'E1_1', 'E1_2', 'E1_3',
            'E2_0', 'E2_1', 'E2_2', 'E2_3',
        ], # 计算对应的 lane 的信息
        'log_file':path_convert('./log/'),
    }
    env = SubprocVecEnv([make_env(env_index=f'{i}', **params) for i in range(1)])
    env = VecNormalize.load(load_path=path_convert('./models/last_vec_normalize.pkl'), venv=env)
    env.training = False # 测试的时候不要更新
    env.norm_reward = False

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model_path = path_convert('./models/last_rl_model.zip')
    model = PPO.load(model_path, env=env, device=device)

    # 使用模型进行测试
    obs = env.reset()
    dones = False # 默认是 False
    total_reward = 0

    while not dones:
        action, _state = model.predict(obs, deterministic=True)
        obs, rewards, dones, infos = env.step(action)
        total_reward += rewards
        
    env.close()
    print(f'累积奖励为, {total_reward}.')