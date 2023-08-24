'''
@Author: WANG Maonan
@Date: 2023-08-23 20:21:16
@Description: 测试获得 AirCraft 的信息
@LastEditTime: 2023-08-23 20:59:35
'''
from loguru import logger
from tshub.aircraft.aircraft_builder import AircraftBuilder

aircraft_inits = {
    'a1': {"position":(10,10,10), "speed":10, "heading":(1,1,0), "communication_range":100},
    'a2': {"position":(10,10,100), "speed":10, "heading":(1,1,0), "communication_range":100}
}

scene_aircraft = AircraftBuilder(aircraft_inits)
aircraft_state = scene_aircraft.get_aircraft_info()
logger.info(aircraft_state)