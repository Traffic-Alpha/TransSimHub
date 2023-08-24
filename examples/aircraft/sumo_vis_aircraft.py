'''
@Author: WANG Maonan
@Date: 2023-08-24 12:03:53
@Description: 在 SUMO 中对 Aircraft 进行可视化
@LastEditTime: 2023-08-24 15:21:04
'''
import numpy as np
import traci
import sumolib

from tshub.utils.get_abs_path import get_abs_path
from tshub.aircraft.aircraft_builder import AircraftBuilder
from tshub.utils.init_log import set_logger


sumoBinary = sumolib.checkBinary('sumo-gui')

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumocfg_file = path_convert("../sumo_env/single_junction/env/single_junction.sumocfg")
traci.start([sumoBinary, "-c", sumocfg_file], label='0')
conn = traci.getConnection('0')

aircraft_inits = {
    'a1': {
        "position":(1500,1110,100), "speed":10, "heading":(1,1,0), "communication_range":200, 
        "if_sumo_visualization":True, "sumo":conn, "img_file":None},
    'a2': {
        "position":(1900,800,100), "speed":10, "heading":(1,1,0), "communication_range":200, 
        "if_sumo_visualization":True, "sumo":conn, "img_file":None
    }
}

scene_aircraft = AircraftBuilder(aircraft_inits)
while conn.simulation.getMinExpectedNumber() > 0:
    conn.simulationStep() # 仿真到某一步
    actions = {
        "a1": (0, np.random.uniform(low=-5, high=5, size=(3))), # 固定
        "a2": (3, np.random.uniform(low=-5, high=5, size=(3))), # 移动
    }
    scene_aircraft.control_aircrafts(actions)

conn.close()
