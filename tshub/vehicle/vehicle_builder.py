'''
@Author: WANG Maonan
@Date: 2023-08-23 15:25:52
@Description: 初始化一个场景内所有的车辆
@LastEditTime: 2023-08-29 17:30:36
'''
from loguru import logger
from typing import Dict, Any

from .vehicle import VehicleInfo

class VehicleBuilder:
    """
    Provides methods to retrieve information and control all vehicles in the scene.
    """

    def __init__(self, sumo, action_type):
        self.sumo = sumo  # sumo connection]
        self.action_type = action_type # lane, lane_continuous_speed
        self.vehicles: Dict[str, VehicleInfo] = {}

    def __create_vehicle(self, vehicle_id: str) -> None:
        """初始化车辆
        """
        vehicle_info = VehicleInfo.create_vehicle(
            id=vehicle_id,
            action_type=self.action_type,
            position=(0,0),
            speed=0,
            road_id='road_id',
            lane_id='lane_id',
            lane_index=0,
            edges=[],
            waiting_time=0,
            next_tls=[],
            sumo=self.sumo
        )
        self.vehicles[vehicle_id] = vehicle_info

    def __delete_vehicle(self, vehicle_id: str) -> None:
        """删除指定 id 的车辆

        Args:
            vehicle_id (str): vehicle id
        """
        if vehicle_id in self.vehicles:
            logger.info(f"SIM: Delete Vehicle with ID {vehicle_id}.")
            del self.vehicles[vehicle_id] # 离开环境后自动 unsubscribe
        else:
            logger.warning(f"SIM: Vehicle with ID {vehicle_id} does not exist.")

    def __update_existing_vehicle(self, vehicle_id: str, vehicle_info:Dict[int, Any]) -> None:
        """更新在路网中车辆的信息

        Args:
            vehicle_id (str): 车辆的 id
            vehicle_info (Dict[int, Any]): 车辆的信息
        """
        self.vehicles[vehicle_id].update_features(vehicle_info)

    def update_scene_vehicles(self) -> None:
        """更新场景中所有车辆信息, 包含三个部分:
        1. 对于之前就在环境中的车辆，更新这些车辆的信息；
        2. 对于离开环境的车辆，将其从 self.vehicles 中删除；
        3. 对于新进入环境的车辆，将其添加在 self.vehicles；
        """
        subscription_results = self.sumo.vehicle.getAllSubscriptionResults()
        vehicle_ids = self.sumo.vehicle.getIDList()

        # 更新已存在的车辆信息
        for vehicle_id in vehicle_ids:
            if vehicle_id in self.vehicles:
                vehicle_info = subscription_results[vehicle_id]
                self.__update_existing_vehicle(vehicle_id, vehicle_info)
            else:
                self.__create_vehicle(vehicle_id)

        # 删除离开环境的车辆
        for vehicle_id in list(self.vehicles.keys()):
            if vehicle_id not in vehicle_ids:
                self.__delete_vehicle(vehicle_id)


    def get_all_vehicles_data(self):
        """
        Get information for all vehicles in the scene.
        Returns a dictionary where the keys are vehicle IDs and the values are the vehicle data.
        """
        self.update_scene_vehicles() # 更新场景内的车辆信息
        vehicle_features = {}
        for vehicle_id, vehicle_info in self.vehicles.items():
            vehicle_features[vehicle_id] = vehicle_info.get_features()
        return vehicle_features


    def control_vehicles(self, actions, hightlight:bool=True):
        """
        Control all vehicles in the scene based on the provided actions.
        Args:
            actions: A dictionary where the keys are vehicle IDs and the values are the corresponding actions.
                     Each action is represented as a tuple (speed, lane_index).
        """
        for vehicle_id, action in actions.items():
            lane_change, target_speed = action
            self._log_vehicle_info(vehicle_id, lane_change, target_speed)
            self.vehicles[vehicle_id].control_vehicle(lane_change, target_speed)
            if hightlight:
                self.sumo.vehicle.highlight(vehicle_id, color=(255, 0, 0, 255), size=-1, alphaMax=255, duration=1)

    def _log_vehicle_info(self, vehicle_id, lane_change, target_speed) -> None:
        if target_speed == None:
            target_speed = 'None'
        logger.debug(f'SIM: {vehicle_id:<20} | Lane Change: {lane_change:<7} | Target Speed: {target_speed:<7}')