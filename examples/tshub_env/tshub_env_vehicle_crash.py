'''
@Author: WANG Maonan
@Date: 2024-04-13 17:52:18
@Description: 车辆碰撞测试
1. 根据车辆位置计算相互之间的距离
2. 当检测到有撞车, 则停止仿真 (例如辆车之间的距离较小)
@LastEditTime: 2024-04-13 18:33:25
'''
import math
import itertools

from loguru import logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.tshub_env.tshub_env import TshubEnvironment
from tshub.utils.format_dict import dict_to_str

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumo_cfg = path_convert("../sumo_env/ego_crash/ego_crash_intersection/env.sumocfg")

def check_collisions(vehicles, gap_threshold: float):
    """输出距离过小的车辆的 ID

    Args:
        vehicles: 包含车辆部分的位置信息
        gap_threshold (float): 最小的距离限制
    """
    collisions = []
    _distance = {}
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
    use_gui=True, num_seconds=30
)

obs = tshub_env.reset()
done = False

while not done:
    if 'ego_1' in obs['vehicle']:
        actions = {
            'vehicle': {
                "ego_1": (0, 10), "ego_2": (0, 10), 
                "ego_3": (0, 10), "ego_4": (0, 10)
            },
        } # 只控制车辆, 且车辆是同时出现的
    else:
        actions = {}
    obs, reward, info, done = tshub_env.step(actions=actions)
    collisions_vehs = check_collisions(obs["vehicle"], gap_threshold=5)
    logger.info(f"SIM: {info['step_time']} {collisions_vehs}")
tshub_env._close_simulation()