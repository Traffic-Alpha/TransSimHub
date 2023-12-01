'''
@Author: WANG Maonan
@Date: 2023-12-01 14:39:47
@Description: 开启仿真同时保存 tripinfo, 只对车辆进行仿真, 同时保存 tripinfo
@LastEditTime: 2023-12-01 20:13:18
'''
import numpy as np
from loguru import logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.tshub_env.tshub_env import TshubEnvironment
from tshub.utils.format_dict import dict_to_str

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumo_cfg = path_convert("../../sumo_env/single_junction/env/single_junction.sumocfg")

tshub_env = TshubEnvironment(
    sumo_cfg=sumo_cfg,
    is_map_builder_initialized=False,
    is_aircraft_builder_initialized=False, 
    is_vehicle_builder_initialized=True, 
    is_traffic_light_builder_initialized=False,
    tls_ids=['htddj_gsndj'],
    vehicle_action_type='lane', 
    tls_action_type='next_or_not',
    use_gui=True, 
    num_seconds=2000,
    trip_info=path_convert('./single_junction.tripinfo.xml')
)

obs = tshub_env.reset()
done = False

while not done:
    actions = {
        'vehicle': dict(),
        'tls': {'htddj_gsndj':0},
        'aircraft': {
            "a1": (1, np.random.randint(8)),
            "a2": (1, np.random.randint(8)),
        }
    }
    obs, reward, info, done = tshub_env.step(actions=actions)
    logger.info(f"SIM: {info['step_time']} \n{dict_to_str(obs)}")
tshub_env._close_simulation()