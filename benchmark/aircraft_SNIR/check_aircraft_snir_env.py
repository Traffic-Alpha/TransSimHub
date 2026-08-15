'''
@Author: WANG Maonan
@Date: 2024-05-29 16:25:18
@Description: 检查 aircraft SNIR 环境
你需要做的事情（注意下面目标点全部固定，reset 的时候不要随机，先看一下能不能收敛）:
1. 单 aircraft 单个目标点可以收敛
2. 单 aircraft 多个目标点（2或是3）可以收敛
3. 多 aircrafts 多个目标点可以收敛（例如 2 个 aircrafts 和 2 个目标点）
---
1. 思考一下 state 的设计，或者说如何和通信可以有联系
@LastEditTime: 2024-05-29 18:45:55
'''
import math
import numpy as np
from loguru import logger
from typing import List
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.format_dict import dict_to_str

from env_utils.vis_snir import render_map
from env_utils.aircraft_snir_env import ACSNIREnvironment
from env_utils.snir_wrapper import SNIRWrapper

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
    sumo_cfg = path_convert("./berlin_UAM/berlin_UAM.sumocfg")
    net_file = path_convert("./berlin_UAM/berlin_UAM.net.xml")
    snir_files = {
        '100': path_convert("./berlin_UAM/berlin_UAM_SNIR_100.txt"),
        # xxx, 这里可以添加不同高度的文件
    }

    aircraft_inits = {
        'drone_1': {
            "aircraft_type": "drone",
            "action_type": "horizontal_movement", 
            "position":(1400, 960, 50), "speed":10, "heading":(1,1,0), "communication_range":50,
            "if_sumo_visualization": True,
            "custom_update_cover_radius":custom_update_cover_radius # 使用自定义覆盖范围的计算
        },
        'drone_2': {
            "aircraft_type": "drone",
            "action_type": "horizontal_movement", 
            "position":(1814, 1314, 50), "speed":10, "heading":(1,1,0), "communication_range":50,
            "if_sumo_visualization": True,
            "custom_update_cover_radius":custom_update_cover_radius # 使用自定义覆盖范围的计算
        },
        'airship_1': {
            "aircraft_type": "airship",
            "action_type": "horizontal_movement", 
            "position":(1588, 1165, 100), "speed":10, "heading":(1,1,0), "communication_range":500,
            "if_sumo_visualization": True, "color": (0,255,0),
        }
    }

    ac_env = ACSNIREnvironment(
        sumo_cfg=sumo_cfg,
        num_seconds=300,
        net_file=net_file,
        radio_map_files=snir_files,
        aircraft_inits=aircraft_inits,
        use_gui=True
    )
    ac_env_wrapper = SNIRWrapper(env=ac_env)

    done = False
    ac_env_wrapper.reset()

    while not done:
        action = {
            "drone_1": (3, 0), # np.random.randint(8)
            "drone_2": (3, 0),
            "airship_1": (1, 0),
        }
        states, rewards, truncated, done, infos = ac_env_wrapper.step(action=action)
        logger.info(f'SIM: State: \n{dict_to_str(states)} \nReward:\n {rewards}')
    
    # 进行可视化
    render_map(
        x_min=ac_env_wrapper.x_min, 
        y_min=ac_env_wrapper.y_min, 
        resolution=ac_env_wrapper.resolution, 
        grid_z=ac_env_wrapper.grid_z,
        trajectories=ac_env_wrapper.ac_history_pos,
        goal_points=ac_env_wrapper.goal_points,
        img_path=path_convert("./snir.jpg")
    )
    ac_env.close()