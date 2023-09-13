'''
@Author: WANG Maonan
@Date: 2023-09-08 19:45:37
@Description: 基于规则的方法, 每次选择排队最大的相位
@LastEditTime: 2023-09-08 20:44:54
'''
from loguru import logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from utils.make_tsc_env import make_env

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))


if __name__ == '__main__':
    sumo_cfg = path_convert("../../sumo_envs/J1/env/J1.sumocfg")
    log_path = path_convert('./log/')
    tsc_env_generate = make_env(
        tls_id='J4',
        num_seconds=2600,
        sumo_cfg=sumo_cfg, 
        use_gui=True,
        log_file=log_path,
        env_index=0,
    )
    tsc_env = tsc_env_generate()

    # Simulation with environment
    dones = False
    phase_occ = {0:0, 1:0, 2:0, 3:0}
    total_reward = 0
    tsc_env.reset()
    while not dones:
        action = max(phase_occ, key=phase_occ.get)
        states, rewards, dones, truncated, infos = tsc_env.step(action=action)
        total_reward += rewards
        phase_occ = infos['phase_occ']
        logger.info(f"SIM: {infos['step_time']} \n+State:{phase_occ};\n+Action:{action}; \n+Reward:{rewards}.")
    tsc_env.close()
    logger.info(f'累积奖励, {total_reward}.')