'''
@Author: WANG Maonan
@Date: 2023-10-29 22:47:54
@Description: 测试训练好的 MAPPO 模型
@LastEditTime: 2024-04-25 01:34:20
'''
import torch

from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger

from train_utils.make_modules import policy_module
from env_utils.make_tsc_env import make_multi_envs

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))


if __name__ == '__main__':
    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    sumo_cfg = path_convert("../../sumo_envs/multi_junctions_tsc/env/three_junctions.sumocfg")
    log_path = path_convert('./log/eval')
    n_agents = 3
    
    # 1. Create Env
    tsc_env = make_multi_envs(
        sumo_cfg=sumo_cfg,
        num_seconds=1300,
        tls_ids=['J1', 'J2', 'J3'],
        use_gui=True,
        log_file=log_path
    )

    # 2. Load Model Dict
    policy_gen = policy_module(tsc_env, n_agents, device)
    policy_gen.load_model(path_convert('mappo_models/actor_147.pkl'))
    policy = policy_gen.make_policy_module()

    # 3. Simulation with environment using the policy
    rollouts = tsc_env.rollout(
        policy=policy,
        auto_reset=True,
        auto_cast_to_device=True,
        break_when_any_done=True,
        max_steps=1_000
    )