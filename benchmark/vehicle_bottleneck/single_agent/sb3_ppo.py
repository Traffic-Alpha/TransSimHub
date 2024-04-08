'''
@Author: WANG Maonan
@Date: 2023-09-08 15:48:26
@Description: 基于 Stabe Baseline3 来控制 ego vehicle
@LastEditTime: 2024-04-08 16:57:11
'''
import os
import torch
from loguru import logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger

from utils.make_veh_env import make_env
from utils.sb3_utils import VecNormalizeCallback, linear_schedule
from utils.custom_models import CustomModel

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, VecNormalize
from stable_baselines3.common.callbacks import CallbackList, CheckpointCallback

path_convert = get_abs_path(__file__)
logger.remove()
set_logger(path_convert('./'), file_log_level="INFO")

if __name__ == '__main__':
    log_path = path_convert('./log/')
    model_path = path_convert('./models/')
    tensorboard_path = path_convert('./tensorboard/')
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    if not os.path.exists(model_path):
        os.makedirs(model_path)
    if not os.path.exists(tensorboard_path):
        os.makedirs(tensorboard_path)
    
    # #########
    # Init Env
    # #########
    sumo_cfg = path_convert("../../sumo_envs/veh_bottleneck/veh.sumocfg")
    params = {
        'sumo_cfg':sumo_cfg,
        'num_seconds': 650,
        'use_gui':False,
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
        'log_file':log_path
    }
    env = SubprocVecEnv([make_env(env_index=f'{i}', **params) for i in range(6)])
    env = VecNormalize(env, norm_obs=False, norm_reward=True)

    # #########
    # Callback
    # #########
    checkpoint_callback = CheckpointCallback(
        save_freq=10000, # 多少个 step, 需要根据与环境的交互来决定
        save_path=model_path,
    )
    vec_normalize_callback = VecNormalizeCallback(
        save_freq=10000,
        save_path=model_path,
    ) # 保存环境参数
    callback_list = CallbackList([checkpoint_callback, vec_normalize_callback])

    # #########
    # Training
    # #########
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    policy_kwargs = dict(
        features_extractor_class=CustomModel,
        features_extractor_kwargs=dict(features_dim=16),
    )
    model = PPO(
                "MlpPolicy", 
                env, 
                batch_size=64,
                n_steps=200, n_epochs=5, # 每次间隔 n_epoch 去评估一次
                learning_rate=linear_schedule(1e-4),
                verbose=True, 
                policy_kwargs=policy_kwargs, 
                tensorboard_log=tensorboard_path, 
                device=device
            )
    model.learn(total_timesteps=1e6, tb_log_name='Ego', callback=callback_list)
    
    # #################
    # 保存 model 和 env
    # #################
    env.save(f'{model_path}/last_vec_normalize.pkl')
    model.save(f'{model_path}/last_rl_model.zip')
    print('训练结束, 达到最大步数.')

    env.close()