'''
@Author: WANG Maonan
@Date: 2023-11-24 18:05:38
@Description: 环境返回行人的信息
@LastEditTime: 2023-11-24 18:27:07
'''
import numpy as np
from loguru import logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.tshub_env.tshub_env import TshubEnvironment
from tshub.utils.format_dict import dict_to_str

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumo_cfg = path_convert("../sumo_env/pedestrian_cross/env/pedestrian_cross.sumocfg")
net_file = path_convert("../sumo_env/pedestrian_cross/env/pedestrian_cross.net.xml")

tshub_env = TshubEnvironment(
    sumo_cfg=sumo_cfg,
    is_map_builder_initialized=True,
    is_aircraft_builder_initialized=False, 
    is_vehicle_builder_initialized=True, 
    is_traffic_light_builder_initialized=True,
    is_person_builder_initialized=True,
    # map builder
    net_file=net_file,
    # traffic light builder
    tls_ids=['J4'], 
    tls_action_type='next_or_not',
    # vehicle builder
    vehicle_action_type='lane',
    use_gui=True, num_seconds=700
)

obs = tshub_env.reset()
done = False

while not done:
    actions = {
        'vehicle': dict(),
    }
    obs, reward, info, done = tshub_env.step(actions=actions)
    logger.info(f"SIM: {info['step_time']} \n{dict_to_str(obs)}")
tshub_env._close_simulation()