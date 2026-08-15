'''
@Author: WANG Maonan
@Date: 2024-07-07 23:30:33
@Description: TSHub 环境的 3D 版本, 整体的逻辑为:
- TshubEnvironment 与 SUMO 进行交互, 获得 SUMO 的数据 (这部分利用 TshubEnvironment)
- TSHubRenderer 对 SUMO 的环境进行渲染 (这部分利用 TSHubRenderer)
- TShubSensor 获得渲染的场景的数据, 作为新的 state 进行输出
LastEditTime: 2025-07-28 21:16:41
'''
from loguru import logger
from typing import Any, Dict, List

from .base_env3d import BaseSumoEnvironment3D

from ..tshub_env.tshub_env import TshubEnvironment # tshub 与 sumo 交互
from tshub.tshub_env3d.renderers import create_renderer # 按名称选择渲染后端
from tshub.tshub_env3d.scene import SceneStatic, build_frame, build_tls_rigs # 渲染器无关的场景描述

class Tshub3DEnvironment(BaseSumoEnvironment3D):
    def __init__(
            # TshubEnvironment 的参数 (与 SUMO 交互)
            self, sumo_cfg: str, 
            scenario_glb_dir: str, # 场景 3D 模型存储的位置
            is_map_builder_initialized: bool = False, 
            is_vehicle_builder_initialized: bool = True, 
            is_aircraft_builder_initialized: bool = True, 
            is_traffic_light_builder_initialized: bool = True, 
            is_person_builder_initialized: bool = True,
            is_lane_builder_initialized: bool = False, # 车道级交通状态 (中观视图)
            is_edge_builder_initialized: bool = False, # 路段级交通状态 (中观视图)
            poly_file: str = None,
            osm_file: str = None, 
            radio_map_files: Dict[str, str] = None, 
            tls_ids: List[str] = None, 
            aircraft_inits: Dict[str, Any] = None, 
            vehicle_action_type: str = 'lane', 
            hightlight: bool = False, 
            tls_action_type: str = 'next_or_not', 
            delta_time: int = 5, 
            net_file: str = None, route_file: str = None, 
            trip_info: str = None, statistic_output: str = None, 
            summary: str = None, queue_output: str = None, fcd_output: str = None,
            tls_state_add: List = None,
            use_gui: bool = False, is_libsumo: bool = False, 
            begin_time=0, num_seconds=20000, 
            max_depart_delay=100000, time_to_teleport=-1, sumo_seed: str = 'random', 
            tripinfo_output_unfinished: bool = True, 
            collision_action: str = None, # 车辆发生碰撞之后做的事情
            remote_port: int = None, 
            num_clients: int = 1,
            # 渲染后端的参数
            renderer: str = 'panda', # 渲染后端 (在线): 目前 'panda'
            sky: str = 'day', # 天空: 'day' / 'dust' (Panda 程序化 city-builder 渐变)
            preset:str = '480P',
            resolution:float = 0.5,
            render_mode: str = "onscreen",
            rendering_backend: str = "pandagl",
            should_count_vehicles: bool = False, # 是否返回的时候获得车辆信息, 将车辆信息保存为 JSON 进行额外的渲染
            debuger_print_node:bool = False, # 是否在 reset 的时候打印 node path
            debuger_spin_camera:bool = False, # 是否显示 spin camera
            sensor_config: Dict[str, List[str]] = None,
        ) -> None:

        self.debuger_print_node = debuger_print_node
        self.debuger_spin_camera = debuger_spin_camera
        self.should_count_vehicles = should_count_vehicles
        # 渲染器无关的场景描述所需信息
        self.scenario_glb_dir = scenario_glb_dir
        self.sensor_config = sensor_config if sensor_config is not None else {}

        # 初始化 tshub 环境与 sumo 交互 (全部使用关键字传参, 避免 TshubEnvironment 增删参数时错位)
        self.tshub_env = TshubEnvironment(
            sumo_cfg=sumo_cfg,
            is_map_builder_initialized=is_map_builder_initialized,
            is_vehicle_builder_initialized=is_vehicle_builder_initialized,
            is_aircraft_builder_initialized=is_aircraft_builder_initialized,
            is_traffic_light_builder_initialized=is_traffic_light_builder_initialized,
            is_person_builder_initialized=is_person_builder_initialized,
            is_lane_builder_initialized=is_lane_builder_initialized,
            is_edge_builder_initialized=is_edge_builder_initialized,
            poly_file=poly_file, osm_file=osm_file, radio_map_files=radio_map_files,
            tls_ids=tls_ids, aircraft_inits=aircraft_inits,
            vehicle_action_type=vehicle_action_type, hightlight=hightlight,
            tls_action_type=tls_action_type, delta_time=delta_time,
            net_file=net_file, route_file=route_file,
            trip_info=trip_info, statistic_output=statistic_output, summary=summary,
            queue_output=queue_output, fcd_output=fcd_output,
            tls_state_add=tls_state_add, use_gui=use_gui, is_libsumo=is_libsumo,
            begin_time=begin_time, num_seconds=num_seconds,
            max_depart_delay=max_depart_delay, time_to_teleport=time_to_teleport,
            sumo_seed=sumo_seed, tripinfo_output_unfinished=tripinfo_output_unfinished,
            collision_action=collision_action,
            remote_port=remote_port, num_clients=num_clients,
        )

        # 初始化渲染后端 (按 renderer 选择, 目前 panda), 将场景渲染为 3D
        self.tshub_render = create_renderer(
            renderer,
            simid=f"tshub-{self.tshub_env.CONNECTION_LABEL}", # 场景的 ID
            scenario_glb_dir=scenario_glb_dir,
            sensor_config=sensor_config,
            preset=preset,
            resolution=resolution,
            render_mode=render_mode,
            rendering_backend=rendering_backend,
            sky=sky,
            debuger_print_node=debuger_print_node,
            debuger_spin_camera=debuger_spin_camera,
        )
        
    def reset(self):
        state_infos = self.tshub_env.reset() # 重置 sumo 环境
        logger.info(f'SIM: 完成 TSHub 初始化, 得到地图和信号灯信息.')

        # 构建渲染器无关的静态场景描述 (路口相机 rig 在这里计算), 再交给渲染后端
        static = SceneStatic(
            scenario_glb_dir=self.scenario_glb_dir,
            sensor_config=self.sensor_config,
            tls_rigs=build_tls_rigs(state_infos, self.sensor_config),
        )
        self.tshub_render.reset(static) # 重置 render, 初始化路口 camera (后端各自处理调试任务)

        return state_infos
    
    def step(self, actions):
        # 1. 与 SUMO 进行交互
        states, rewards, infos, dones = self.tshub_env.step(actions)

        # 2. 构建渲染器无关的 SceneFrame, 交给渲染后端出图
        frame = build_frame(states)
        sensor_data = self.tshub_render.sync(frame, should_count_vehicles=self.should_count_vehicles) # 运行 panda3d
        
        # 将 image 的信息通过 sensor_data 进行返回
        return states, rewards, infos, dones, sensor_data

    def close(self) -> None:
        self.tshub_env._close_simulation()
        self.tshub_render.destroy()
