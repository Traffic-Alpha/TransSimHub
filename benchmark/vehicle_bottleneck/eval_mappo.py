'''
@Author: WANG Maonan
@Date: 2023-10-29 22:47:54
@Description: 测试训练好的 MAPPO 模型
@LastEditTime: 2023-12-19 21:18:35
'''
import torch

from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger

from train_utils.make_modules import policy_module
from env_utils.make_veh_env import make_multi_envs

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))


if __name__ == '__main__':
    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    sumo_cfg = path_convert("../sumo_envs/veh_bottleneck/veh.sumocfg")
    log_path = path_convert('./log/eval')
    n_agents = 3
    
    # 1. Create Env
    tsc_env = make_multi_envs(
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
        log_file=log_path,
        device=device
    )

    # 2. Load Model Dict
    policy_gen = policy_module(tsc_env, n_agents, device)
    policy_gen.load_model(path_convert('mappo_models/actor.pkl'))
    policy = policy_gen.make_policy_module()

    # 3. Simulation with environment using the policy
    rollouts = tsc_env.rollout(
        policy=policy,
        auto_reset=True,
        auto_cast_to_device=True,
        break_when_any_done=True,
        max_steps=1_000
    )