'''
@Author: WANG Maonan
@Date: 2023-08-23 20:21:16
@Description: 测试获得 AirCraft 的信息
@LastEditTime: 2023-08-30 15:40:59
'''
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
aircraft_state = scene_aircraft.get_objects_infos()
logger.info(dict_to_str(aircraft_state))