'''
@Author: WANG Maonan
@Date: 2023-08-23 16:55:45
@Description: 修改车辆的状态
@LastEditTime: 2023-08-24 15:24:21
'''
import numpy as np
import sumolib

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

    actions = {_veh_id:(12, 2) for _veh_id in data}
    scene_vehicles.control_all_vehicles(actions)

    conn.simulationStep() # 仿真到某一步

conn.close()