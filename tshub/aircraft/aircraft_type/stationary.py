'''
@Author: WANG Maonan
@Date: 2023-08-29 18:10:45
@Description: 飞翔器保持不动
@LastEditTime: 2023-08-30 15:31:05
'''
from .base_aircraft_action import AircraftAction

class StationaryAction(AircraftAction):
    def __init__(self, id) -> None:
        super().__init__(id)
    
    def execute(self, *args, **kwargs) -> None:
        position = kwargs['position']
        heading = (0,0,0) # heading 为 0, 保持不变
        return position, heading