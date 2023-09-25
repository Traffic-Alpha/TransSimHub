'''
@Author: WANG Maonan
@Date: 2023-09-14 13:47:34
@Description: Check aircraft and vehicle ENV
+ Two types of aircraft, custom image
@LastEditTime: 2023-09-25 14:20:32
'''
import math
import numpy as np
from loguru import logger
from typing import List
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.format_dict import dict_to_str
from utils.ac_env import ACEnvironment
from utils.ac_wrapper import ACEnvWrapper

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

def custom_update_cover_radius(position:List[float], communication_range:float) -> float:
    """自定义的更新地面覆盖半径的方法, 在这里实现您的自定义逻辑

    Args:
        position (List[float]): 飞行器的坐标, (x,y,z)
        communication_range (float): 飞行器的通行范围
    """
    height = position[2]
    cover_radius = height / np.tan(math.radians(75/2))
    return cover_radius

if __name__ == '__main__':
    sumo_cfg = path_convert("../sumo_envs/OSM/env/osm.sumocfg")
    aircraft_inits = {
        'drone_1': {
            "aircraft_type": "drone",
            "action_type": "horizontal_movement", 
            "position":(1400, 960, 50), "speed":10, "heading":(1,1,0), "communication_range":50,
            "if_sumo_visualization": True, "img_file": path_convert('./asset/drone.png'),
            "custom_update_cover_radius":custom_update_cover_radius # 使用自定义覆盖范围的计算
        },
        'drone_2': {
            "aircraft_type": "drone",
            "action_type": "horizontal_movement", 
            "position":(1814, 1314, 50), "speed":10, "heading":(1,1,0), "communication_range":50,
            "if_sumo_visualization": True, "img_file": path_convert('./asset/drone.png'),
            "custom_update_cover_radius":custom_update_cover_radius # 使用自定义覆盖范围的计算
        },
        'airship_1': {
            "aircraft_type": "airship",
            "action_type": "horizontal_movement", 
            "position":(1588, 1165, 100), "speed":10, "heading":(1,1,0), "communication_range":500,
            "if_sumo_visualization": True, "color": (0,255,0),
            "img_file": path_convert('./asset/airship.png')
        }
    }

    ac_env = ACEnvironment(
        sumo_cfg=sumo_cfg,
        num_seconds=1200,
        aircraft_inits=aircraft_inits,
        use_gui=True
    )
    ac_env_wrapper = ACEnvWrapper(env=ac_env)

    done = False
    ac_env_wrapper.reset()
    while not done:
        action = {
            "drone_1": (3, np.random.randint(8)),
            "drone_2": (3, np.random.randint(8)),
            "airship_1": (1, np.random.randint(8)),
        }
        states, rewards, truncated, done, infos = ac_env_wrapper.step(action=action)
        logger.info(f'SIM: State: \n{dict_to_str(states)} \nReward:\n {rewards}')
    ac_env.close()