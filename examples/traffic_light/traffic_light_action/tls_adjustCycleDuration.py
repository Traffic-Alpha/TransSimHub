'''
@Author: WANG Maonan
@Date: 2024-05-01 15:34:53
@Description: 每个周期内对所有的相位持续时间进行调整
@LastEditTime: 2024-05-01 15:59:36
'''
import sumolib
import numpy as np
from loguru import logger

from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.utils.format_dict import dict_to_str

from tshub.traffic_light.traffic_light_builder import TrafficLightBuilder

import traci
sumoBinary = sumolib.checkBinary('sumo-gui')

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumocfg_file = path_convert("../../sumo_env/single_junction/env/single_junction.sumocfg")
traci.start([sumoBinary, "-c", sumocfg_file], label='0')
conn = traci.getConnection('0')

action_index = 0 # 动作的 id
scene_traffic_lights = TrafficLightBuilder(sumo=conn, tls_ids=['htddj_gsndj'], action_type='adjust_cycle_duration')
while conn.simulation.getMinExpectedNumber() > 0:
    # 获得路口信息
    tls_infos = scene_traffic_lights.get_objects_infos() # 返回路口信息
    logger.info(f'SIM: \n{dict_to_str(tls_infos)}')

    # 控制路口信息
    if tls_infos['htddj_gsndj']['can_perform_action']:
        # 每个相位时间随机增加或者减少
        scene_traffic_lights.control_objects({'htddj_gsndj':[np.random.choice([-5,0,5]) for _ in range(4)]})
    else: # 此时下发的动作会无效
        scene_traffic_lights.control_objects({'htddj_gsndj':None})

    conn.simulationStep() # 仿真到某一步

conn.close()