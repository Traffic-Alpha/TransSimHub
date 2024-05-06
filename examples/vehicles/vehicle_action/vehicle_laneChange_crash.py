'''
@Author: WANG Maonan
@Date: 2024-05-05 14:50:29
@Description: 控制车辆进行碰撞, 由于换道引发的碰撞
@LastEditTime: 2024-05-05 15:09:09
'''
import traci
import sumolib
import numpy as np
from tshub.utils.get_abs_path import get_abs_path
from tshub.vehicle.vehicle_builder import VehicleBuilder
from tshub.utils.init_log import set_logger

sumoBinary = sumolib.checkBinary('sumo-gui')

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumocfg_file = path_convert("../../sumo_env/ego_crash/ego_crash_lane_change/scenario.sumocfg")
traci.start([sumoBinary, "-c", sumocfg_file, "--collision.action", "remove"], label='0') # 需要加入 collision.action
conn = traci.getConnection('0')

scene_vehicles = VehicleBuilder(sumo=conn, action_type='lane_continuous_speed')

while conn.simulation.getMinExpectedNumber() > 0:
    # 获得车辆的信息
    data = scene_vehicles.get_objects_infos()

    actions = {}
    if "1" in data:
        actions["1"] = (np.random.choice([-1,1]), 15)
    print(actions)
    scene_vehicles.control_objects(actions)

    conn.simulationStep()

conn.close()