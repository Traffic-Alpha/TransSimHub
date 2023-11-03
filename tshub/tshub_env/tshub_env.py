'''
@Author: WANG Maonan
@Date: 2023-08-23 15:34:52
@Description: 整合 "Veh"（车辆）、"Air"（航空）和 "Traf"（信号灯）的环境
@LastEditTime: 2023-11-03 17:46:51
'''
import os
import sys
from typing import Dict, List, Any, Literal

from .base_sumo_env import BaseSumoEnvironment
from ..map.map_builder import MapBuilder
from ..aircraft.aircraft_builder import AircraftBuilder
from ..traffic_light.traffic_light_builder import TrafficLightBuilder
from ..vehicle.vehicle_builder import VehicleBuilder

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare the environment variable 'SUMO_HOME'")


class TshubEnvironment(BaseSumoEnvironment):
    """
    SUMO Environment for Traffic Signal Control

    :param net_file: (str) SUMO .net.xml file
    :param route_file: (str) SUMO .rou.xml file
    :param out_csv_name: (str) name of the .csv output with simulation results. If None no output is generated
    :param use_gui: (bool) Wheter to run SUMO simulation with GUI visualisation
    :param begin_time: (int) The time step (in seconds) the simulation starts
    :param num_seconds: (int) Number of simulated seconds on SUMO. The time in seconds the simulation must end.
    :param max_depart_delay: (int) Vehicles are discarded if they could not be inserted after max_depart_delay seconds
    :param delta_time: (int) Simulation seconds between actions
    :param min_green: (int) Minimum green time in a phase
    :param max_green: (int) Max green time in a phase
    :single_agent: (bool) If true, it behaves like a regular gym.Env. Else, it behaves like a MultiagentEnv (https://github.com/ray-project/ray/blob/master/python/ray/rllib/env/multi_agent_env.py)
    :sumo_seed: (int/string) Random seed for sumo. If 'random' it uses a randomly chosen seed.
    :fixed_ts: (bool) If true, it will follow the phase configuration in the route_file and ignore the actions. 不调整信号灯
    """
    CONNECTION_LABEL = 1  # For traci multi-client support

    def __init__(self, 
                 sumo_cfg: str, 
                 is_map_builder_initialized:bool = False,
                 is_vehicle_builder_initialized:bool = True, 
                 is_aircraft_builder_initialized:bool = True, 
                 is_traffic_light_builder_initialized:bool = True,
                 poly_file:str = None, osm_file:str = None,
                 tls_ids:List[str] = None, aircraft_inits:Dict[str, Any] = None,
                 vehicle_action_type:str = 'lane', hightlight:bool = False,
                 tls_action_type:str = 'next_or_not',
                 net_file: str = None, route_file: str = None, 
                 trip_info: str = None, statistic_output: str = None, summary: str = None, queue_output: str = None, 
                 tls_state_add: List = None, use_gui: bool = False, is_libsumo: bool = False, 
                 begin_time=0, num_seconds=20000, max_depart_delay=100000, time_to_teleport=-1, 
                 sumo_seed: str = 'random', 
                 remote_port: int = None, num_clients: int = 1) -> None:
        
        super().__init__(sumo_cfg, net_file, route_file, 
                         trip_info, statistic_output, summary, queue_output, 
                         tls_state_add, use_gui, is_libsumo, 
                         begin_time, num_seconds, max_depart_delay, time_to_teleport, 
                         sumo_seed, remote_port, num_clients
                        )
        
        self.label = str(TshubEnvironment.CONNECTION_LABEL)
        TshubEnvironment.CONNECTION_LABEL += 1 # 多次初始化 label 是不同的

        self.is_map_builder_initialized = is_map_builder_initialized
        self.is_vehicle_builder_initialized = is_vehicle_builder_initialized
        self.is_aircraft_builder_initialized = is_aircraft_builder_initialized
        self.is_traffic_light_builder_initialized = is_traffic_light_builder_initialized

        # Map Builder Input
        self.poly_file = poly_file
        self.osm_file = osm_file
        # Traffic Light Builder Input
        self.tls_ids = tls_ids
        self.tls_action_type = tls_action_type
        # Aircraft Builder Input
        self.aircraft_inits = aircraft_inits
        # Vehicle Builder Input
        self.vehicle_action_type = vehicle_action_type
        self.hightlight = hightlight

    def __init_builder(self) -> None:
        map_builder = (
            MapBuilder(poly_file=self.poly_file, osm_file=self.osm_file)
            if self.is_map_builder_initialized
            else None
        )
        if map_builder is not None:
            self.map_infos = map_builder.get_objects_infos() # Statistic Map Info

        vehicle_builder = (
            VehicleBuilder(sumo=self.sumo, action_type=self.vehicle_action_type, hightlight=self.hightlight)
            if self.is_vehicle_builder_initialized
            else None
        )
        aircraft_builder = (
            AircraftBuilder(sumo=self.sumo, aircraft_inits=self.aircraft_inits)
            if self.is_aircraft_builder_initialized
            else None
        )
        tls_builder = (
            TrafficLightBuilder(sumo=self.sumo, tls_ids=self.tls_ids, action_type=self.tls_action_type)
            if self.is_traffic_light_builder_initialized
            else None
        )

        self.scene_objects = {
            'vehicle': vehicle_builder,
            'aircraft': aircraft_builder,
            'tls': tls_builder
        }

    def reset(self) -> Dict[str, Any]:
        """重置环境, 返回初始的 obs
        """
        self._close_simulation() # 关闭仿真
        self._start_simulation() # 开启仿真
        self.__init_builder() # 初始化场景内的 builder
        obs = self.__computer_observation()
        return obs
    
    def step(self, actions):
        # apply action
        for _object_type, _object_action in actions.items():
            if self.scene_objects[_object_type] is not None:
                self.scene_objects[_object_type].control_objects(_object_action)
        
        self.sumo.simulationStep()

        # update env
        obs = self.__computer_observation()
        reward = self.__computer_reward()
        info = self.__compute_info()
        done = self._computer_done()
        return obs, reward, info, done

    def __computer_observation(self) -> Dict[str, Any]:
        """自定义 obs 的计算
        """
        env_state = {
            _object_type: _object_builder.get_objects_infos()
            for _object_type, _object_builder in self.scene_objects.items()
            if _object_builder is not None
        }
        if self.is_map_builder_initialized:
            env_state['map'] = self.map_infos
        return env_state

    def __computer_reward(self) -> Literal[0]:
        """自定义 reward 的计算
        """
        return 0

    def __compute_info(self):
        """每一步, 返回信息
        """
        return {
            'step_time': self.sim_step, # 返回当前仿真的时间
        }