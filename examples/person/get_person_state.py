'''
@Author: WANG Maonan
@Date: 2023-11-24 16:06:00
@Description: 查看行人的 state
@LastEditTime: 2023-11-24 17:35:53
'''
import sumolib
from loguru import logger

from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.utils.format_dict import dict_to_str
from tshub.person.person_builder import PersonBuilder

import traci
sumoBinary = sumolib.checkBinary('sumo-gui')

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumocfg_file = path_convert("../sumo_env/pedestrian_cross/env/pedestrian_cross.sumocfg")
traci.start([sumoBinary, "-c", sumocfg_file], label='0')
conn = traci.getConnection('0')

scene_people = PersonBuilder(sumo=conn)
while conn.simulation.getMinExpectedNumber() > 0:
    data = scene_people.get_objects_infos() # 获得行人的信息
    logger.info(f'SIM: {dict_to_str(data)}')

    conn.simulationStep()

conn.close()