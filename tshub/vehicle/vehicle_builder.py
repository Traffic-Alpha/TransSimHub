'''
@Author: WANG Maonan
@Date: 2023-08-23 15:25:52
@Description: This module provides a VehicleBuilder class that serves as a vehicle management system for a scene. 
It offers methods to retrieve information about all vehicles in the scene and control their actions.

Functionalities:
- Retrieving vehicle data: The `get_all_vehicles_data` method retrieves information for all vehicles in the scene and returns a dictionary where the keys are vehicle IDs and the values are the corresponding vehicle data.
- Controlling vehicles: The `control_all_vehicles` method allows controlling all vehicles in the scene based on the provided actions. Actions are specified as a dictionary where the keys are vehicle IDs, and the values are tuples representing the desired speed and lane index for each vehicle.
- Subscribing to new vehicles: The `subscribe_new_vehicles` method subscribes to newly arrived vehicles in the scene and adds them to the collection of managed vehicles.

Usage:
1. Create an instance of the VehicleBuilder class, providing a connection to the SUMO (Simulation of Urban MObility) simulation.
2. Use the `get_all_vehicles_data` method to retrieve information about all vehicles in the scene.
3. Use the `control_all_vehicles` method to control the actions of the vehicles in the scene.
4. Use the `subscribe_new_vehicles` method to subscribe to newly arrived vehicles.

Note: This module relies on the `VehicleInfo` class defined in the `vehicle.py` module to represent vehicle information.

@LastEditTime: 2023-08-23 18:15:31
'''
import traci
from loguru import logger
from dataclasses import asdict

from .vehicle import VehicleInfo

class VehicleBuilder:
    """
    Provides methods to retrieve information and control all vehicles in the scene.
    """

    def __init__(self, sumo):
        self.sumo = sumo  # sumo connection
        self.subscribed_vehicles_id = set()

    def get_all_vehicles_data(self):
        """
        Get information for all vehicles in the scene.
        Returns a dictionary where the keys are vehicle IDs and the values are the vehicle data.
        """
        subscription_results = self.sumo.vehicle.getAllSubscriptionResults()
        all_vehicles_data = {
            vehicle_id: asdict(VehicleInfo.from_subscription_result(vehicle_id, vehicle_data))
            for vehicle_id, vehicle_data in subscription_results.items()
        }
        return all_vehicles_data

    def control_all_vehicles(self, actions, hightlight:bool=True):
        """
        Control all vehicles in the scene based on the provided actions.
        Args:
            actions: A dictionary where the keys are vehicle IDs and the values are the corresponding actions.
                     Each action is represented as a tuple (speed, lane_index).
        """
        for vehicle_id, action in actions.items():
            speed, lane_index = action
            self._log_vehicle_info(vehicle_id, speed, lane_index)
            self.sumo.vehicle.slowDown(vehicle_id, speed, duration=1)
            # self.sumo.vehicle.changeLane(vehicle_id, lane_index, duration=1)
            if hightlight:
                self.sumo.vehicle.highlight(vehicle_id, color=(255, 0, 0, 255), size=-1, alphaMax=-1)

    def subscribe_new_vehicles(self):
        """
        Subscribe to newly arrived vehicles in the scene and add them to the collection.
        """
        running_vehicle_ids = set(self.sumo.vehicle.getIDList())
        new_vehicle_ids = running_vehicle_ids - self.subscribed_vehicles_id
        for new_vehicle_id in new_vehicle_ids:
            self.sumo.vehicle.subscribe(
                new_vehicle_id,
                [
                    traci.constants.VAR_POSITION, traci.constants.VAR_SPEED,
                    traci.constants.VAR_ROAD_ID, traci.constants.VAR_LANE_ID,
                    traci.constants.VAR_EDGES, traci.constants.VAR_WAITING_TIME,
                    traci.constants.VAR_NEXT_TLS
                ]
            )
        self.subscribed_vehicles_id = running_vehicle_ids

    def _log_vehicle_info(self, vehicle_id, speed, lane_index):
        logger.debug(f'SIM: {vehicle_id:<15} | {speed:<6} | {lane_index:<6}')