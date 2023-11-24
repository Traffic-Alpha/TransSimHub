'''
@Author: WANG Maonan
@Date: 2023-11-24 15:48:26
@Description: 初始化 Person Object
@LastEditTime: 2023-11-24 17:52:07
'''
from loguru import logger
from typing import Dict, Any

from .person import PersonInfo
from ..tshub_env.base_builder import BaseBuilder

class PersonBuilder(BaseBuilder):
    """
    Provides methods to retrieve information and control all persons in the scene.
    """

    def __init__(self, sumo) -> None:
        self.sumo = sumo  # sumo connection]
        self.people: Dict[str, PersonInfo] = {}

    def create_objects(self, person_id: str) -> None:
        """初始化行人
        """
        person_info = PersonInfo.create_person(
            id=person_id,
            angle=self.sumo.person.getAngle(person_id),
            position=self.sumo.person.getPosition(person_id),
            lane_position=self.sumo.person.getLanePosition(person_id),
            speed=self.sumo.person.getSpeed(person_id),
            road_id=self.sumo.person.getRoadID(person_id),
            next_edge=self.sumo.person.getNextEdge(person_id),
            waiting_time=0,
            sumo=self.sumo
        )
        self.people[person_id] = person_info

    def __delete_person(self, person_id: str) -> None:
        """删除指定 id 的行人

        Args:
            person_id (str): person_id id
        """
        if person_id in self.people:
            logger.info(f"SIM: Delete Person with ID {person_id}.")
            del self.people[person_id] # 离开环境后自动 unsubscribe
        else:
            logger.warning(f"SIM: Person with ID {person_id} does not exist.")

    def __update_existing_person(self, person_id: str, person_info:Dict[int, Any]) -> None:
        """更新在路网中行人的信息

        Args:
            person_id (str): 行人的 id
            person_info (Dict[int, Any]): 行人的信息
        """
        self.people[person_id].update_features(person_info)

    def update_objects_state(self) -> None:
        """更新场景中所有行人信息, 包含三个部分:
        1. 对于离开环境的行人，将其从 self.people 中删除；
        2. 对于之前就在环境中的行人，更新这些行人的信息；
        3. 对于新进入环境的行人，将其添加在 self.people；
        """
        subscription_results = self.sumo.person.getAllSubscriptionResults()
        person_ids = self.sumo.person.getIDList() # 目前环境里面所有行人的 id

        # 删除离开环境的行人
        for person_id in list(self.people.keys()):
            if person_id not in person_ids:
                self.__delete_person(person_id)

        # 更新已存在的行人信息
        for person_id in person_ids:
            if person_id in self.people:
                person_info = subscription_results[person_id]
                self.__update_existing_person(person_id, person_info)
            else:
                self.create_objects(person_id)

    def get_objects_infos(self):
        """
        Get information for all epople in the scene.
        Returns a dictionary where the keys are people IDs and the values are the people data.
        """
        self.update_objects_state() # 更新场景内的行人信息
        people_features = {}
        for person_id, person_info in self.people.items():
            people_features[person_id] = person_info.get_features()
        return people_features

    def control_objects(self) -> None:
        pass