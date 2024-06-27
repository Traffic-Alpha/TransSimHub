'''
@Author: WANG Maonan
@Date: 2024-06-27 19:05:17
@Description: 每次调整单个相位的持续时间
@LastEditTime: 2024-06-27 19:42:29
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
scene_traffic_lights = TrafficLightBuilder(
    sumo=conn, 
    tls_ids=['htddj_gsndj'], 
    action_type='set_phase_diration',
    delta_time=None # 这里推荐设置为 None
)
while conn.simulation.getMinExpectedNumber() > 0:
    # 获得路口信息
    tls_infos = scene_traffic_lights.get_objects_infos() # 返回路口信息
    logger.info(f'SIM: \n{dict_to_str(tls_infos)}')

    # 控制路口信息
    if tls_infos['htddj_gsndj']['can_perform_action']:
        # 每个相位的持续时间选择是从 10,15,20 里面选择
        new_phase_duration = np.random.choice([10, 15, 20])
        scene_traffic_lights.control_objects({'htddj_gsndj':new_phase_duration})
    else: # 此时下发的动作会无效
        scene_traffic_lights.control_objects({'htddj_gsndj':None})

    conn.simulationStep() # 仿真到某一步

conn.close()