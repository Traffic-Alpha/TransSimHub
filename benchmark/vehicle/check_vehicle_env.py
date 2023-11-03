'''
@Author: WANG Maonan
@Date: 2023-10-27 20:16:14
@Description: 检查车辆环境
@LastEditTime: 2023-11-03 18:09:12
'''
import math
import numpy as np
from loguru import logger
from typing import List
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.format_dict import dict_to_str

from utils.veh_env import VehEnvironment
from utils.veh_wrapper import VehEnvWrapper

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))


if __name__ == '__main__':
    sumo_cfg = path_convert("../sumo_envs/veh_speed/veh.sumocfg")

    ac_env = VehEnvironment(
        sumo_cfg=sumo_cfg,
        num_seconds=350, # 秒
        vehicle_action_type='lane_continuous_speed',
        use_gui=True
    )
    ac_env_wrapper = VehEnvWrapper(env=ac_env)

    done = False
    ac_env_wrapper.reset()
    while not done:
        action = {
            'ego_0': (0, 1),
            'ego_1': (0, 3),
            'ego_2': (0, 12),
        }
        states, rewards, truncated, done, infos = ac_env_wrapper.step(action=action)
        logger.info(f'SIM: State: \n{dict_to_str(states)} \nReward:\n {rewards}')
    ac_env.close()