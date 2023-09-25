'''
@Author: WANG Maonan
@Date: 2023-08-30 17:02:20
@Description: 从 tshub 中获得 "Veh"（车辆）、"Air"（航空）和 "Traf"（信号灯）的状态
@LastEditTime: 2023-09-25 14:01:40
'''
import math
import numpy as np
from loguru import logger
from typing import List
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.tshub_env.tshub_env import TshubEnvironment
from tshub.utils.format_dict import dict_to_str

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

sumo_cfg = path_convert("../sumo_env/single_junction/env/single_junction.sumocfg")
aircraft_inits = {
    'a1': {
        "aircraft_type": "drone",
        "action_type": "horizontal_movement", 
        "position":(1500,1110,100), "speed":10, "heading":(1,1,0), "communication_range":200, 
        "if_sumo_visualization":True, "img_file":None,
        "custom_update_cover_radius":custom_update_cover_radius # 使用自定义的计算
    },
    'a2': {
        "aircraft_type": "drone",
        "action_type": "horizontal_movement", 
        "position":(1900,800,100), "speed":10, "heading":(1,1,0), "communication_range":200, 
        "if_sumo_visualization":True, "img_file":None,
        "custom_update_cover_radius":None
    }
}

tshub_env = TshubEnvironment(
    sumo_cfg=sumo_cfg,
    is_aircraft_builder_initialized=True, 
    is_vehicle_builder_initialized=True, 
    is_traffic_light_builder_initialized=True,
    tls_ids=['htddj_gsndj'], aircraft_inits=aircraft_inits,
    vehicle_action_type='lane', tls_action_type='next_or_not',
    use_gui=True,
)

obs = tshub_env.reset()
done = False

while not done:
    actions = {
        'vehicle': dict(),
        'tls': {'htddj_gsndj':0},
        'aircraft': {
            "a1": (1, np.random.randint(8)),
            "a2": (1, np.random.randint(8)),
        }
    }
    obs, reward, info, done = tshub_env.step(actions=actions)
    logger.info(f"SIM: {info['step_time']} \n{dict_to_str(obs)}")
tshub_env._close_simulation()