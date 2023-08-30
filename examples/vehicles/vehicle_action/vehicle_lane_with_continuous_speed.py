'''
@Author: WANG Maonan
@Date: 2023-08-30 16:19:47
@Description: 控制车辆, 同时控制换道和速度
@LastEditTime: 2023-08-30 16:21:37
'''
import traci
import random
import numpy as np
import sumolib

from tshub.utils.get_abs_path import get_abs_path
from tshub.vehicle.vehicle_builder import VehicleBuilder
from tshub.utils.init_log import set_logger

def select_keys(dictionary):
    keys = list(dictionary.keys())
    selected_keys = random.sample(keys, k=int(len(keys) * 0.1))
    return selected_keys

sumoBinary = sumolib.checkBinary('sumo-gui')

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumocfg_file = path_convert("../../sumo_env/single_junction/env/single_junction.sumocfg")
traci.start([sumoBinary, "-c", sumocfg_file], label='0')
conn = traci.getConnection('0')

scene_vehicles = VehicleBuilder(sumo=conn, action_type='lane_continuous_speed')
while conn.simulation.getMinExpectedNumber() > 0:
    # 获得车辆的信息
    data = scene_vehicles.get_objects_infos()

    # 控制部分车辆, 分别是 lane_change, speed
    selected_vehicles = select_keys(data)
    actions = {_veh_id:(np.random.randint(3), 12) for _veh_id in selected_vehicles}
    scene_vehicles.control_objects(actions)

    conn.simulationStep()

conn.close()