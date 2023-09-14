'''
@Author: WANG Maonan
@Date: 2023-08-30 15:53:08
@Description: Aircraft 垂直方向移动
@LastEditTime: 2023-09-14 16:26:06
'''
import traci
import sumolib
from loguru import logger
import numpy as np

from tshub.utils.get_abs_path import get_abs_path
from tshub.aircraft.aircraft_builder import AircraftBuilder
from tshub.utils.init_log import set_logger
from tshub.utils.format_dict import dict_to_str

sumoBinary = sumolib.checkBinary('sumo-gui')

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumocfg_file = path_convert("../../sumo_env/single_junction/env/single_junction.sumocfg")
traci.start([sumoBinary, "-c", sumocfg_file], label='0')
conn = traci.getConnection('0')

aircraft_inits = {
    'a1': {
        "aircraft_type": "drone",
        "action_type": "vertical_movement", 
        "position":(1500,1110,100), "speed":10, "heading":(1,1,0), "communication_range":200, 
        "if_sumo_visualization":True, "img_file":None},
    'a2': {
        "aircraft_type": "drone",
        "action_type": "vertical_movement", 
        "position":(1900,800,100), "speed":10, "heading":(1,1,0), "communication_range":200, 
        "if_sumo_visualization":True, "img_file":None
    }
}

scene_aircraft = AircraftBuilder(sumo=conn, aircraft_inits=aircraft_inits)
while conn.simulation.getMinExpectedNumber() > 0:
    conn.simulationStep() # 仿真到某一步
    actions = {
        "a1": (5, np.random.randint(3)),
        "a2": (5, np.random.randint(3)),
    } # 这里的 action 不会移动 aircraft
    scene_aircraft.control_objects(actions)
    aircraft_state = scene_aircraft.get_objects_infos()
    logger.info(f'SIM: {dict_to_str(aircraft_state)}')

conn.close()