'''
@Author: WANG Maonan
@Date: 2023-08-23 20:21:34
@Description: 测试控制 AirCraft
@LastEditTime: 2023-08-30 15:44:09
'''
import numpy as np
from loguru import logger
from tshub.aircraft.aircraft_builder import AircraftBuilder
from tshub.utils.format_dict import dict_to_str

aircraft_inits = {
    'a1': {
        "action_type": "horizontal_movement", 
        "position":(10,10,50), "speed":10, "heading":(1,1,0), "communication_range":100
    },
    'a2': {
        "action_type": "horizontal_movement", 
        "position":(10,10,50), "speed":10, "heading":(1,1,0), "communication_range":100
    }
}

scene_aircraft = AircraftBuilder(aircraft_inits)

for _ in range(10):
    aircraft_state = scene_aircraft.get_objects_infos()
    logger.info(f'Before Action:\n{dict_to_str(aircraft_state)}.')

    actions = {
        "a1": (1, np.random.randint(8)),
        "a2": (1, np.random.randint(8)),
    }
    scene_aircraft.control_objects(actions)
    logger.info(f'Action: {actions}.')

    aircraft_state = scene_aircraft.get_objects_infos()
    logger.info(f'After Action:\n{dict_to_str(aircraft_state)}.')