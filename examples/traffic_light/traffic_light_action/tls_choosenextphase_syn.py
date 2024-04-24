'''
@Author: WANG Maonan
@Date: 2023-08-25 13:28:22
@Description: 控制 Traffic Light Signal (Synchronize), 使用 Choose Next Phase 的动作设计
@LastEditTime: 2024-04-24 20:47:28
'''
import sumolib
from loguru import logger

from tshub.traffic_light.traffic_light_builder import TrafficLightBuilder
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.utils.format_dict import dict_to_str

import traci
sumoBinary = sumolib.checkBinary('sumo-gui')

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumocfg_file = path_convert("../../sumo_env/single_junction/env/single_junction.sumocfg")
traci.start([sumoBinary, "-c", sumocfg_file], label='0')
conn = traci.getConnection('0')

action_index = 0 # 动作的 id
scene_traffic_lights = TrafficLightBuilder(sumo=conn, tls_ids=['htddj_gsndj'], action_type='choose_next_phase_syn')
while conn.simulation.getMinExpectedNumber() > 0:
    # 获得路口信息
    tls_infos = scene_traffic_lights.get_objects_infos() # 返回路口信息
    logger.info(f'SIM: \n{dict_to_str(tls_infos)}')

    # 控制路口信息
    if tls_infos['htddj_gsndj']['can_perform_action']:
        scene_traffic_lights.control_objects({'htddj_gsndj':action_index})
        action_index = (action_index+1)%4
        logger.debug(f'SIM: Action Index: {action_index}')
    else: # 此时下发的动作会无效
        scene_traffic_lights.control_objects({'htddj_gsndj':None})

    conn.simulationStep() # 仿真到某一步

conn.close()