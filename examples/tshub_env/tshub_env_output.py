'''
@Author: WANG Maonan
@Date: 2024-05-07 14:58:35
@Description: 仿真输出的文件
@LastEditTime: 2024-06-25 17:29:39
'''
import math
import itertools
import numpy as np

from loguru import logger
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env.tshub_env import TshubEnvironment

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

CRASH_TYPE = "ego_crash_intersection" # ego_crash_car_following, ego_crash_intersection
sumo_cfg = path_convert(f"../sumo_env/ego_crash/{CRASH_TYPE}/env.sumocfg")
net_file = path_convert(f"../sumo_env/ego_crash/{CRASH_TYPE}/inter_tsc.net.xml")

tshub_env = TshubEnvironment(
    sumo_cfg=sumo_cfg,
    net_file=net_file,
    is_map_builder_initialized=False,
    is_aircraft_builder_initialized=False, 
    is_vehicle_builder_initialized=True, 
    is_traffic_light_builder_initialized=False,
    vehicle_action_type='lane_continuous_speed',
    trip_info=path_convert('./tripinfo.out.xml'),
    summary=path_convert('./summary.out.xml'),
    statistic_output=path_convert('./statistic.out.xml'),
    tls_state_add=[
        path_convert(f"../sumo_env/ego_crash/{CRASH_TYPE}/add/tls_programs.add.xml"),
        path_convert(f"../sumo_env/ego_crash/{CRASH_TYPE}/add/tls_state.add.xml"),
        path_convert(f"../sumo_env/ego_crash/{CRASH_TYPE}/add/tls_switch_states.add.xml"),
        path_convert(f"../sumo_env/ego_crash/{CRASH_TYPE}/add/tls_switches.add.xml")
    ],
    use_gui=True, num_seconds=100,
    collision_action="warn"
)

for _ in range(3): # 多次重置, output 文件可以保留
    obs = tshub_env.reset()
    done = False

    while not done:
        veh_actions = {}
        for i in range(1, 5):
            ego_key = f'ego_{i}' # id: ego_1, ego_2, ...
            if ego_key in obs['vehicle']:
                veh_actions[ego_key] = (0, 15)

        actions = {
            'vehicle': veh_actions
        } # 只控制车辆, 且车辆是同时出现的
        obs, reward, info, done = tshub_env.step(actions=actions)

tshub_env._close_simulation()