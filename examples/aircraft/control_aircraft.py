'''
@Author: WANG Maonan
@Date: 2023-08-23 20:21:34
@Description: 测试控制 AirCraft
@LastEditTime: 2023-08-24 14:56:00
'''
import numpy as np
from loguru import logger
from tshub.aircraft.aircraft_builder import AircraftBuilder

aircraft_inits = {
    'a1': {"position":(10,10,50), "speed":10, "heading":(1,1,0), "communication_range":100},
    'a2': {"position":(10,10,50), "speed":10, "heading":(1,1,0), "communication_range":100}
}

scene_aircraft = AircraftBuilder(aircraft_inits)

for _ in range(10):
    aircraft_state = scene_aircraft.get_aircraft_info()
    logger.info(f'Before Action: {aircraft_state}.')

    actions = {
        "a1": (3, np.random.uniform(low=-5, high=5, size=(3))),
        "a2": (3, np.random.uniform(low=-5, high=5, size=(3))),
    }
    scene_aircraft.control_aircrafts(actions)
    logger.info(f'Action: {actions}.')

    aircraft_state = scene_aircraft.get_aircraft_info()
    logger.info(f'After Action: {aircraft_state}.')