'''
@Author: WANG Maonan
@Date: 2023-08-25 13:28:22
@Description: 获得 Traffic Light Signal State
@LastEditTime: 2023-08-28 13:24:24
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

sumocfg_file = path_convert("../sumo_env/single_junction/env/single_junction.sumocfg")
traci.start([sumoBinary, "-c", sumocfg_file], label='0')
conn = traci.getConnection('0')

# 两种动作设计, 分别是 choose_next_phase 和 next_or_not
scene_traffic_lights = TrafficLightBuilder(sumo=conn, tls_ids=['htddj_gsndj'], action_type='next_or_not')
while conn.simulation.getMinExpectedNumber() > 0:
    tls_infos = scene_traffic_lights.get_traffic_lights_infos()
    logger.info(f'SIM: \n{dict_to_str(tls_infos)}')
    
    conn.simulationStep() # 仿真到某一步

conn.close()