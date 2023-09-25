'''
@Author: WANG Maonan
@Date: 2023-08-24 12:03:53
@Description: The example of custom update cover radius
+ 两个 aircraft 同时上升
+ 自定义 cover radius 变大，默认的变小
@LastEditTime: 2023-09-25 14:13:55
'''
import traci
import sumolib
import math
import numpy as np
from loguru import logger
from typing import List

from tshub.utils.get_abs_path import get_abs_path
from tshub.aircraft.aircraft_builder import AircraftBuilder
from tshub.utils.init_log import set_logger
from tshub.utils.format_dict import dict_to_str

sumoBinary = sumolib.checkBinary('sumo-gui')

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumocfg_file = path_convert("../sumo_env/single_junction/env/single_junction.sumocfg")
traci.start([sumoBinary, "-c", sumocfg_file], label='0')
conn = traci.getConnection('0')

def custom_update_cover_radius(position:List[float], communication_range:float) -> float:
    """自定义的更新地面覆盖半径的方法, 在这里实现您的自定义逻辑

    Args:
        position (List[float]): 飞行器的坐标, (x,y,z)
        communication_range (float): 飞行器的通行范围
    """
    height = position[2]
    cover_radius = height / np.tan(math.radians(75/2))
    return cover_radius


aircraft_inits = {
    'a1': {
            "aircraft_type": "drone",
            "action_type": "vertical_movement", 
            "position":(1500,1110,100), "speed":10, "heading":(1,1,0), "communication_range":200, 
            "if_sumo_visualization":True, "img_file":None, "color":(0,255,0),
            "custom_update_cover_radius":custom_update_cover_radius # 使用自定义的计算
        },
    'a2': {
            "aircraft_type": "drone",
            "action_type": "vertical_movement", 
            "position":(1900,800,100), "speed":10, "heading":(1,1,0), "communication_range":200, 
            "if_sumo_visualization":True, "img_file":None,
            "custom_update_cover_radius":None # 使用默认的
    }
}


scene_aircraft = AircraftBuilder(sumo=conn, aircraft_inits=aircraft_inits)
while conn.simulation.getMinExpectedNumber() > 0:
    conn.simulationStep() # 仿真到某一步
    actions = {
        "a1": (5, 1),
        "a2": (5, 1),
    } # 这里的 action 往上飞行
    scene_aircraft.control_objects(actions)
    aircraft_state = scene_aircraft.get_objects_infos()
    logger.info(f'SIM: {dict_to_str(aircraft_state)}')

conn.close()