'''
@Author: WANG Maonan
@Date: 2024-04-13 15:01:42
@Description: 控制车辆进行碰撞
=> ego_crash_car_following, 追尾测试
=> ego_crash_intersection, 无保护左转撞车测试
@LastEditTime: 2024-04-13 17:51:26
'''
import traci
import sumolib

from tshub.utils.get_abs_path import get_abs_path
from tshub.vehicle.vehicle_builder import VehicleBuilder
from tshub.utils.init_log import set_logger

CRASH_TYPE = "ego_crash_intersection" # ego_crash_car_following, ego_crash_intersection

sumoBinary = sumolib.checkBinary('sumo-gui')

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumocfg_file = path_convert(f"../../sumo_env/ego_crash/{CRASH_TYPE}/env.sumocfg")
traci.start([sumoBinary, "-c", sumocfg_file, "--collision.action", "warn"], label='0')
conn = traci.getConnection('0')

scene_vehicles = VehicleBuilder(sumo=conn, action_type='lane_continuous_speed')

while conn.simulation.getMinExpectedNumber() > 0:
    # 获得车辆的信息
    data = scene_vehicles.get_objects_infos()

    actions = {}
    if "ego_1" in data:
        actions["ego_1"] = (0, 15)
    if "ego_2" in data:
        actions["ego_2"] = (0, 15)
    if "ego_3" in data:
        actions["ego_3"] = (0, 15)
    if "ego_4" in data:
        actions["ego_4"] = (0, 15)
    scene_vehicles.control_objects(actions)

    conn.simulationStep()

conn.close()