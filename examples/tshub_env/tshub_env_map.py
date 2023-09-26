'''
@Author: WANG Maonan
@Date: 2023-09-25 21:11:30
@Description: 测试 TSHub 环境返回环境信息
@LastEditTime: 2023-09-25 21:29:11
'''
import numpy as np
from loguru import logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.tshub_env.tshub_env import TshubEnvironment
from tshub.utils.format_dict import dict_to_str

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumo_cfg = path_convert("../sumo_env/osm_berlin/env/berlin.sumocfg")
osm_file = path_convert("../sumo_env/osm_berlin/berlin.osm")
poly_file = path_convert("../sumo_env/osm_berlin/env/berlin.poly.xml")

aircraft_inits = {
    'a1': {
        "aircraft_type": "drone",
        "action_type": "horizontal_movement", 
        "position":(124,305,100), "speed":10, "heading":(1,1,0), "communication_range":200, 
        "if_sumo_visualization":True, "img_file":None,
    },
    'a2': {
        "aircraft_type": "drone",
        "action_type": "horizontal_movement", 
        "position":(270,123,100), "speed":10, "heading":(1,1,0), "communication_range":200, 
        "if_sumo_visualization":True, "img_file":None,
    }
}

tshub_env = TshubEnvironment(
    sumo_cfg=sumo_cfg,
    is_map_builder_initialized=True,
    is_aircraft_builder_initialized=True, 
    is_vehicle_builder_initialized=True, 
    is_traffic_light_builder_initialized=True,
    # map builder
    osm_file=osm_file,
    poly_file=poly_file,
    # traffic light builder
    tls_ids=['25663405', '25663436', '25663407', '25663429', '25663423', '25663426'], 
    tls_action_type='next_or_not',
    # aircraft builder
    aircraft_inits=aircraft_inits,
    # vehicle builder
    vehicle_action_type='lane',
    use_gui=True, num_seconds=700
)

obs = tshub_env.reset()
done = False

while not done:
    actions = {
        'vehicle': dict(),
        'tls': {
            '25663405':0, '25663436':0, '25663407':0, 
            '25663429':0, '25663423':0, '25663426':0
        },
        'aircraft': {
            "a1": (1, np.random.randint(8)),
            "a2": (1, np.random.randint(8)),
        }
    }
    obs, reward, info, done = tshub_env.step(actions=actions)
    logger.info(f"SIM: {info['step_time']} \n{dict_to_str(obs)}")
tshub_env._close_simulation()