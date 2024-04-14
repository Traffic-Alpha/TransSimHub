'''
@Author: WANG Maonan
@Date: 2024-04-13 17:52:18
@Description: 车辆碰撞测试
1. 根据车辆位置计算相互之间的距离
2. 当检测到有撞车, 则停止仿真 (例如辆车之间的距离较小)
@LastEditTime: 2024-04-14 15:20:55
'''
import math
import itertools
import numpy as np

from loguru import logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.tshub_env.tshub_env import TshubEnvironment
from tshub.utils.format_dict import dict_to_str

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

CRASH_TYPE = "ego_crash_intersection" # ego_crash_car_following, ego_crash_intersection
sumo_cfg = path_convert(f"../sumo_env/ego_crash/{CRASH_TYPE}/env.sumocfg")

def check_collisions_based_pos(vehicles, gap_threshold: float):
    """输出距离过小的车辆的 ID, 直接根据 pos 来进行计算是否碰撞 (比较简单)

    Args:
        vehicles: 包含车辆部分的位置信息
        gap_threshold (float): 最小的距离限制
    """
    collisions = []
    _distance = {} # 记录每辆车之间的距离
    for (id1, v1), (id2, v2) in itertools.combinations(vehicles.items(), 2):
        dist = math.sqrt(
            (v1['position'][0] - v2['position'][0]) ** 2 \
                + (v1['position'][1] - v2['position'][1]) ** 2
        )
        _distance[f'{id1}-{id2}'] = dist
        if dist < gap_threshold:
            collisions.append((id1, id2))
    return collisions


tshub_env = TshubEnvironment(
    sumo_cfg=sumo_cfg,
    is_map_builder_initialized=False,
    is_aircraft_builder_initialized=False, 
    is_vehicle_builder_initialized=True, 
    is_traffic_light_builder_initialized=False,
    vehicle_action_type='lane_continuous_speed',
    use_gui=True, num_seconds=100,
    collision_action="warn"
)

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
    collisions_vehs = check_collisions_based_pos(obs["vehicle"], gap_threshold=5)
    logger.info(f"SIM: {info['step_time']} {collisions_vehs}, {dict_to_str(actions)}")
tshub_env._close_simulation()