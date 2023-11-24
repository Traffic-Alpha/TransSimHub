'''
@Author: WANG Maonan
@Date: 2023-11-24 15:48:01
@Description: Person Dataclass
- https://sumo.dlr.de/docs/TraCI/Person_Value_Retrieval.html
- https://sumo.dlr.de/docs/TraCI/Change_Person_State.html
@LastEditTime: 2023-11-24 17:52:52
'''
import traci
from typing import Dict, Any
from loguru import logger
from dataclasses import dataclass, fields
from typing import List, Tuple


@dataclass
class PersonInfo:
    """
    Represents information about a person.
    """
    id: str  # The ID of the person
    angle: float # the angle of the named person within the last step [°]
    position: Tuple[float]  # The position of the person
    lane_position: float # The position of the person along the edge (in [m])
    speed: float  # The current speed of the person
    road_id: str  # The ID of the road the person is on
    waiting_time: float  # The waiting time of the person
    next_edge: str # Returns the next edge on the persons route while it is walking. If there is no further edge or the person is in another stage, returns the empty string.
    sumo: traci.connection.Connection

    def __post_init__(self) -> None:
        # 订阅行人
        self.sumo.person.subscribe(
                self.id,
                [
                    traci.constants.VAR_ANGLE, traci.constants.VAR_POSITION, 
                    traci.constants.VAR_SPEED, traci.constants.VAR_ROAD_ID, 
                    traci.constants.VAR_WAITING_TIME, traci.constants.VAR_NEXT_EDGE,
                    traci.constants.VAR_LANEPOSITION
                ]
            )

    @classmethod
    def create_person(cls, id: str, angle: float,
                       sumo:traci.connection.Connection,
                       position: Tuple[float], 
                       lane_position: float,
                       speed: float, road_id: str, 
                       waiting_time: float, 
                       next_edge: List[str]
                    ):
        logger.info(f'SIM: Init Person: {id}')
        return cls(id=id, angle=angle,
                   sumo=sumo, position=position, 
                   lane_position=lane_position,
                   speed=speed, road_id=road_id, 
                   waiting_time=waiting_time,
                   next_edge=next_edge
        )

    @staticmethod
    def get_feature_index(feature: str) -> int:
        """
        Get the index of a feature in the subscription result.
        Args:
            feature: The name of the feature.
        Returns:
            The index of the feature.
        """
        feature_mapping = {
            'angle': 67,
            'position': 66,
            'speed': 64,
            'road_id': 80,
            'waiting_time': 122,
            'next_edge': 193,
            'lane_position': 86
        }
        return feature_mapping.get(feature, -1)
    
    def update_features(self, person_info:Dict[int, Any]) -> None:
        """更新在路网中的行人的信息
        """
        self.angle=person_info.get(PersonInfo.get_feature_index('angle'), None)
        self.position=person_info.get(PersonInfo.get_feature_index('position'), None)
        self.speed=person_info.get(PersonInfo.get_feature_index('speed'), None)
        self.road_id=person_info.get(PersonInfo.get_feature_index('road_id'), None)
        self.waiting_time=person_info.get(PersonInfo.get_feature_index('waiting_time'), None)
        self.next_edge=person_info.get(PersonInfo.get_feature_index('next_edge'), None)
        self.lane_position=person_info.get(PersonInfo.get_feature_index('lane_position'), None)

    def get_features(self):
        output_dict = {}
        for field in fields(self):
            field_name = field.name
            field_value = getattr(self, field_name)
            if field_name != 'sumo':
                output_dict[field_name] = field_value
        return output_dict

    def control_person(self) -> None:
        pass