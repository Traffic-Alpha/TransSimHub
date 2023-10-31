'''
@Author: WANG Maonan
@Date: 2023-10-30 23:01:03
@Description: 检查同时开启多个仿真环境
@LastEditTime: 2023-10-31 20:08:33
'''
from loguru import logger

from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from env_utils.make_tsc_env import make_parallel_env

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

if __name__ == '__main__':
    sumo_cfg = path_convert("../../sumo_envs/multi_junctions_tsc/env/three_junctions.sumocfg")
    log_path = path_convert('./log/')
    tsc_env = make_parallel_env(
        num_envs=4,
        sumo_cfg=sumo_cfg,
        num_seconds=1600,
        tls_ids=['J1', 'J2', 'J3'],
        use_gui=False,
        log_file=log_path
    )

    rollouts = tsc_env.rollout(1_000, break_when_any_done=False)
    for r in rollouts:
        logger.info(f'RL: {r}')