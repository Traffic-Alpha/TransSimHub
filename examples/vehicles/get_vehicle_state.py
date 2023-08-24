'''
@Author: WANG Maonan
@Date: 2023-08-23 15:50:00
@Description: 获得场景中所有车辆的信息
# 这里需要可以在每隔 Ns 获得当前车辆的所有信息
@LastEditTime: 2023-08-23 18:16:00
'''
import sumolib
from loguru import logger

from tshub.utils.get_abs_path import get_abs_path
from tshub.vehicle.vehicle_builder import VehicleBuilder
from tshub.utils.init_log import set_logger

import traci
sumoBinary = sumolib.checkBinary('sumo-gui')

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumocfg_file = path_convert("../sumo_env/single_junction/env/single_junction.sumocfg")
traci.start([sumoBinary, "-c", sumocfg_file], label='0')
conn = traci.getConnection('0')

scene_vehicles = VehicleBuilder(sumo=conn)
while conn.simulation.getMinExpectedNumber() > 0:
    scene_vehicles.subscribe_new_vehicles()
    data = scene_vehicles.get_all_vehicles_data()
    
    conn.simulationStep() # 仿真到某一步

conn.close()