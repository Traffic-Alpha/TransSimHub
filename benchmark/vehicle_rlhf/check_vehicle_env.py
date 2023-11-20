'''
@Author: WANG Maonan
@Date: 2023-10-27 20:16:14
@Description: 检查车辆环境
@LastEditTime: 2023-11-20 16:16:02
'''
import numpy as np
from loguru import logger
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.format_dict import dict_to_str
from tshub.utils.check_folder import check_folder

from utils.veh_env import VehEnvironment
from utils.veh_wrapper import VehEnvWrapper

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))


if __name__ == '__main__':
    sumo_cfg = path_convert("../sumo_envs/veh_rlhf/veh_rlhf.sumocfg")
    net_file = path_convert("../sumo_envs/veh_rlhf/veh_rlhf.net.xml")
    image_save_folder = path_convert('./scenario_images') # 存储场景图像的地方
    check_folder(image_save_folder)
    
    ac_env = VehEnvironment(
        sumo_cfg=sumo_cfg,
        net_file=net_file,
        num_seconds=500, # 秒
        vehicle_action_type='lane_continuous_speed',
        use_gui=True
    )
    ac_env_wrapper = VehEnvWrapper(env=ac_env)

    done = False
    ac_env_wrapper.reset()
    while not done:
        action = {
            "E0__0__ego.0": (np.random.choice([0, 1, 2]), -1),
            "E0__1__ego.0": (np.random.choice([0, 1, 2]), -1),
            "E0__1__ego.1": (np.random.choice([0, 1, 2]), -1),
            "E0__2__ego.0": (np.random.choice([0, 1, 2]), -1),
            "E0__2__ego.1": (np.random.choice([0, 1, 2]), -1),
            "E0__3__ego.0": (np.random.choice([0, 1, 2]), -1),
            "E0__4__ego.0": (np.random.choice([0, 1, 2]), -1),
            "E0__5__ego.0": (np.random.choice([0, 1, 2]), -1),
        } # (lane, speed)
        states, rewards, truncated, done, infos = ac_env_wrapper.step(action=action)
        logger.info(f'SIM: State: \n{dict_to_str(states)} \nReward:\n {rewards}')

        # Save Follow Vehicle Image
        fig = ac_env_wrapper.render(
            focus_id='E0__0__ego.0', 
            focus_type='vehicle', 
            focus_distance=80,
            mode='sumo_gui',
            save_folder=image_save_folder
        )
    ac_env.close()