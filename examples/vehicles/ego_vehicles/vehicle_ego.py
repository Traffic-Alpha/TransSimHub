'''
@Author: WANG Maonan
@Date: 2023-09-01 14:45:54
@Description: 使用 Lane 来控制车辆, 只控制是 ego 类型的车
@LastEditTime: 2024-08-11 19:36:55
'''
import traci
import sumolib
import numpy as np

from tshub.utils.get_abs_path import get_abs_path
from tshub.vehicle.vehicle_builder import VehicleBuilder
from tshub.utils.init_log import set_logger

def filter_ego_id(vehicle_data):
    ego_ids = []
    for _veh_id, _veh_info in vehicle_data.items():
        if _veh_info['vehicle_type'] == 'ego':
            ego_ids.append(_veh_id)
    return ego_ids

sumoBinary = sumolib.checkBinary('sumo-gui')

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumocfg_file = path_convert("../../sumo_env/three_junctions/env/3junctions.sumocfg")
traci.start([sumoBinary, "-c", sumocfg_file], label='0')
conn = traci.getConnection('0')

scene_vehicles = VehicleBuilder(sumo=conn, action_type='lane')
while conn.simulation.getMinExpectedNumber() > 0:
    # 获得车辆的信息
    data = scene_vehicles.get_objects_infos()

    # 控制部分车辆, 分别是 lane_change, speed
    ego_vehicles = filter_ego_id(data)
    actions = {
        _veh_id:{'lane_change': np.random.randint(4)} 
        for _veh_id in ego_vehicles
    }
    scene_vehicles.control_objects(actions)

    conn.simulationStep()

conn.close()