'''
@Author: WANG Maonan
@Date: 2023-10-29 22:46:51
@Description: 多智能体的环境测试
@LastEditTime: 2023-10-31 19:14:46
'''
from loguru import logger

from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger

from env_utils.make_tsc_env import make_multi_envs

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))


if __name__ == '__main__':
    sumo_cfg = path_convert("../../sumo_envs/multi_junctions_tsc/env/three_junctions.sumocfg")
    log_path = path_convert('./log/')
    tsc_env = make_multi_envs(
        sumo_cfg=sumo_cfg,
        num_seconds=1600,
        tls_ids=['J1', 'J2', 'J3'],
        use_gui=True
    )

    # Simulation with environment
    print(f'Group Map: {tsc_env.group_map}')
    print(f'Reward Key: {tsc_env.reward_key}')
    rollouts = tsc_env.rollout(1_000, break_when_any_done=False)
    for r in rollouts:
        logger.info(f'RL: {r}')