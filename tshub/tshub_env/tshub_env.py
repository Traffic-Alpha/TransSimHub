'''
@Author: WANG Maonan
@Date: 2023-08-23 15:34:52
@Description: 整合 "Veh"（车辆）、"Air"（航空）和 "Traf"（信号灯）的环境
LastEditTime: 2026-04-21 11:17:40
'''
import os
import sys
from loguru import logger
from typing import Dict, List, Any, Literal

from .base_sumo_env import BaseSumoEnvironment
from ..map.map_builder import MapBuilder
from ..aircraft.aircraft_builder import AircraftBuilder
from ..traffic_light.traffic_light_builder import TrafficLightBuilder
from ..vehicle.vehicle_builder import VehicleBuilder
from ..person.person_builder import PersonBuilder
from ..lane.lane_builder import LaneBuilder
from ..edge.edge_builder import EdgeBuilder
from ..visualization.micro import LocalMapRenderer
from ..visualization.micro import compute_focus_window

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

    def __init__(self, 
                 sumo_cfg: str, 
                 is_map_builder_initialized:bool = False,
                 is_vehicle_builder_initialized:bool = True, 
                 is_aircraft_builder_initialized:bool = True, 
                 is_traffic_light_builder_initialized:bool = True,
                 is_person_builder_initialized:bool = True,
                 is_lane_builder_initialized:bool = False,
                 is_edge_builder_initialized:bool = False,
                 poly_file:str = None, osm_file:str = None, radio_map_files:Dict[str, str]=None,
                 tls_ids:List[str] = None, aircraft_inits:Dict[str, Any] = None,
                 vehicle_action_type:str = 'lane', hightlight:bool = False,
                 tls_action_type:str = 'next_or_not', delta_time:int=5,
                 net_file: str = None, route_file: str = None, 
                 trip_info: str = None, statistic_output: str = None, summary: str = None, queue_output: str = None, fcd_output: str = None, 
                 tls_state_add: List = None, use_gui: bool = False, is_libsumo: bool = False, 
                 begin_time=0, num_seconds=20000, max_depart_delay=100000, time_to_teleport=-1, 
                 sumo_seed: str = 'random', tripinfo_output_unfinished:bool=True, collision_action:str=None,
                 remote_port: int = None, num_clients: int = 1
        ) -> None:
        
        super().__init__(sumo_cfg, net_file, route_file,
                         trip_info, statistic_output, summary, queue_output, fcd_output,
                         tls_state_add, use_gui, is_libsumo,
                         begin_time, num_seconds, max_depart_delay, time_to_teleport,
                         sumo_seed, tripinfo_output_unfinished,
                         collision_action, remote_port, num_clients
                        )

        self.is_map_builder_initialized = is_map_builder_initialized
        self.is_vehicle_builder_initialized = is_vehicle_builder_initialized
        self.is_aircraft_builder_initialized = is_aircraft_builder_initialized
        self.is_traffic_light_builder_initialized = is_traffic_light_builder_initialized
        self.is_person_builder_initialized = is_person_builder_initialized
        self.is_lane_builder_initialized = is_lane_builder_initialized
        self.is_edge_builder_initialized = is_edge_builder_initialized

        # Map Builder Input
        self.poly_file = poly_file
        self.osm_file = osm_file
        self.radio_map_files = radio_map_files

        # Traffic Light Builder Input
        self.tls_ids = tls_ids
        self.tls_action_type = tls_action_type
        self.delta_time = delta_time
        if self.is_traffic_light_builder_initialized is True and not self.tls_ids:
            raise ValueError("Both `map_init` and `tls_ids` need to be set together.")
        if tls_ids is not None:
            if not isinstance(self.tls_ids, list):
                raise TypeError("The 'tls_ids' must be of type 'list'.")

        # Aircraft Builder Input
        self.aircraft_inits = aircraft_inits
        
        # Vehicle Builder Input
        self.vehicle_action_type = vehicle_action_type
        self.hightlight = hightlight

        # For SUMI-GUI render
        self.render_count = 0
        # mode='rgb' 的局部视角渲染器 (持有路网空间索引与复用的 figure), 首次 render 时创建
        self._map_renderer = None

    def __init_builder(self) -> None:
        map_builder = (
            MapBuilder(net_file=self._net, poly_file=self.poly_file, osm_file=self.osm_file, radio_map_files=self.radio_map_files)
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
            TrafficLightBuilder(sumo=self.sumo, tls_ids=self.tls_ids, action_type=self.tls_action_type, delta_time=self.delta_time)
            if self.is_traffic_light_builder_initialized
            else None
        )
        person_builder = (
            PersonBuilder(sumo=self.sumo)
            if self.is_person_builder_initialized
            else None
        )
        lane_builder = (
            LaneBuilder(sumo=self.sumo)
            if self.is_lane_builder_initialized
            else None
        )
        edge_builder = (
            EdgeBuilder(sumo=self.sumo)
            if self.is_edge_builder_initialized
            else None
        )

        # 注意 key 与 obs 的 key 一致. 车道/路段的交通状态用 'lane_state'/'edge_state',
        # 与地图的静态几何 obs['lane_shape'] 区分开
        self.scene_objects = {
            'vehicle': vehicle_builder,
            'aircraft': aircraft_builder,
            'tls': tls_builder,
            'person': person_builder,
            'lane_state': lane_builder,
            'edge_state': edge_builder,
        }

    def reset(self) -> Dict[str, Any]:
        """重置环境, 返回初始的 obs
        """
        self._close_simulation() # 关闭仿真
        if self._map_renderer is not None: # 路网可能变化, 渲染器连同 figure 一起重建
            self._map_renderer.close()
            self._map_renderer = None
        self._start_simulation() # 开启仿真
        self.__init_builder() # 初始化场景内的 builder
        obs = self.__computer_observation()

        self.obs = obs.copy() # copy obs for render

        return obs
    
    def step(self, actions):
        # apply action
        for _object_type, _object_action in actions.items():
            if self.scene_objects[_object_type] is not None:
                self.scene_objects[_object_type].control_objects(_object_action)
        
        self.sumo.simulationStep()
        logger.info(f'SIM: ==> Simulation Step: {self.sim_step} <==') # 日志中打印当前的仿真时间

        # update env
        obs = self.__computer_observation()
        reward = self.__computer_reward()
        info = self.__compute_info()
        done = self._computer_done()

        self.obs = obs.copy() # copy obs for render
        
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
            env_state.update(self.map_infos) # 地图信息是固定的, 只需要每次额外补充进去即可, 不需要每次计算
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
    
    def render(self, mode:str='rgb',
               focus_id:str=None, focus_type:str=None, focus_distance:float=None, 
               save_folder:str=None
        ) -> None:
        """对场景进行渲染

        Args:
            mode (str, optional): 渲染的模式，包含 rgb 和 sumo_gui. Defaults to rgb.
            focus_id (str, optional): 追踪 object 的 ID。mode='rgb' 时必填。
            focus_type (str, optional): 追踪 object 的类型，包含 vehicle 和 node。
                mode='rgb' 时必填。其中 node (路口) 是固定的，视野窗口整个 episode 都不变，
                因此路网图层只会构建一次。
            focus_distance (float, optional): 追踪覆盖的范围 (m)。mode='rgb' 时必填。
            save_folder (str, optional): 当 mode='sumo_gui' 的时候，图像保存的文件夹。

        Note:
            mode='rgb' 只提供**局部视角**（跟随某辆车或某个路口）。全网态势请用
            tshub.visualization.meso（中观大屏），它在大路网上快得多也清楚得多。

            返回的 figure 是复用的：下一次 render 之前要先保存或转成数组。
        """
        if not self.is_map_builder_initialized:
            raise ValueError('需要初始化地图信息')

        # 两种模式都只提供局部视角: 全网态势请用 tshub.visualization.meso (中观大屏)
        if (focus_id is None) or (focus_type is None) or (focus_distance is None):
            raise ValueError(
                "render() 只支持局部视角, 需要同时给出 focus_id / focus_type / focus_distance. "
                "如果想看全网的态势, 请使用 tshub.visualization.meso (中观大屏)."
            )
        x_range, y_range = compute_focus_window(
            self.obs, focus_id, focus_type, focus_distance
        )

        # Step 2. Render Image (rgb or sumo-gui)
        if mode == 'rgb':
            if (x_range is None) and (y_range is None):
                return None # 如果追踪的物体不在, 则 fig 直接返回 None

            if self._map_renderer is None: # 路网索引只建一次
                self._map_renderer = LocalMapRenderer(
                    map_lanes=self.obs['lane_shape'], map_nodes=self.obs['node'],
                )
            return self._map_renderer.render(
                focus_id, self.obs['vehicle'], x_range=x_range, y_range=y_range,
            )
        elif mode == 'sumo_gui':
            assert self.use_gui == True, '需要开启 GUI 界面才可以使用 SUMO-GUI 进行渲染。'
            assert save_folder is not None, '需要在 save_folder 设置文件保存的路径。'

            if self.render_count == 0: # 第一次初始化时候需要创建新的 view
                logger.warning(f'使用 SUMO-GUI 截图前确保窗口最大化。')
                import time; time.sleep(5)
                self.traci.gui.removeView('View #0')
                self.traci.gui.addView('RenderView', schemeName="real world")
            
            if (x_range is None) and (y_range is None):
                pass
            elif self.render_count>0:
                self.traci.gui.setBoundary(
                    viewID='RenderView', 
                    xmin=x_range[0], ymin=y_range[0], 
                    xmax=x_range[1], ymax=y_range[1]
                ) # 设置范围
                self.traci.gui.screenshot(
                    viewID='RenderView', 
                    filename=f'{save_folder}/{self.render_count}.png', 
                    width=600, height=600
                )
            self.render_count += 1
            return None
        else:
            raise ValueError(f'mode can only be rgb and sumo_gui, now is {mode}.')