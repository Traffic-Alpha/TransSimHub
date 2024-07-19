'''
@Author: WANG Maonan
@Date: 2024-07-07 23:30:33
@Description: TSHub 环境的 3D 版本, 整体的逻辑为:
- TshubEnvironment 与 SUMO 进行交互, 获得 SUMO 的数据 (这部分利用 TshubEnvironment)
- TSHubRenderer 对 SUMO 的环境进行渲染 (这部分利用 TSHubRenderer)
- TShubSensor 获得渲染的场景的数据, 作为新的 state 进行输出
@LastEditTime: 2024-07-14 01:53:51
'''
from loguru import logger
from typing import Any, Dict, List

from .base_env3d import BaseSumoEnvironment3D

from ..tshub_env.tshub_env import TshubEnvironment # tshub 与 sumo 交互
from .vis3d_renderer.tshub_render import TSHubRenderer # tshub3D render

class Tshub3DEnvironment(BaseSumoEnvironment3D):
    def __init__(
            # TshubEnvironment 的参数
            self, sumo_cfg: str, 
            scenario_glb_dir: str, # 场景 3D 模型存储的位置
            is_map_builder_initialized: bool = False, 
            is_vehicle_builder_initialized: bool = True, 
            is_aircraft_builder_initialized: bool = True, 
            is_traffic_light_builder_initialized: bool = True, 
            is_person_builder_initialized: bool = True, 
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
            summary: str = None, queue_output: str = None, 
            tls_state_add: List = None, 
            use_gui: bool = False, is_libsumo: bool = False, 
            begin_time=0, num_seconds=20000, 
            max_depart_delay=100000, time_to_teleport=-1, sumo_seed: str = 'random', 
            tripinfo_output_unfinished: bool = True, 
            collision_action: str = None, # 车辆发生碰撞之后做的事情
            remote_port: int = None, 
            num_clients: int = 1,
            # TSHubRenderer 的参数
            use_render_pipeline: bool = False,
            render_mode: str = "onscreen"
        ) -> None:

        # 初始化 tshub 环境与 sumo 交互
        self.tshub_env = TshubEnvironment(
            sumo_cfg, 
            is_map_builder_initialized, 
            is_vehicle_builder_initialized, 
            is_aircraft_builder_initialized, 
            is_traffic_light_builder_initialized, 
            is_person_builder_initialized, 
            poly_file, osm_file, radio_map_files, tls_ids, aircraft_inits, 
            vehicle_action_type, hightlight, tls_action_type, delta_time, 
            net_file, route_file, trip_info, statistic_output, summary, queue_output, 
            tls_state_add, use_gui, is_libsumo, begin_time, num_seconds, max_depart_delay, 
            time_to_teleport, sumo_seed, tripinfo_output_unfinished, collision_action, 
            remote_port, num_clients
        )

        # 初始化渲染器, 将场景渲染为 3D
        self.tshub_render = TSHubRenderer(
            use_render_pipeline=use_render_pipeline,
            render_mode=render_mode,
            simid=f"tshub-{self.tshub_env.CONNECTION_LABEL}", # 场景的 ID
            scenario_glb_dir=scenario_glb_dir,
        )

        # 需要在 ego vehicles 中加入 sensor

        # 在路口的四个方向加入 sensor

        # 在 aircraft 上加入 sensor

        
    def reset(self):
        state_infos = self.tshub_env.reset() # 重置 sumo 环境
        self.tshub_render.reset() # 重置 render
        # self.tshub_render.print_node_paths(self.tshub_render._root_np) # 重置后打印 node path
        self.tshub_render._showbase_instance.taskMgr.add(
            self.tshub_render.test_spin_camera_task, 
            "SpinCamera"
        ) # TODO, 这里需要转移到 debug 的地方

        return state_infos
    
    def step(self, actions):
        # 1. 与 SUMO 进行交互
        states, rewards, infos, dones = self.tshub_env.step(actions)
        # 2. 渲染 3D 的场景
        sensor_data = self.tshub_render.step(states) # 运行 panda3d
        
        # TODO, sensor_data 需要放在 state 里面返回，而不是单独返回
        return states, rewards, infos, dones, sensor_data

    def close(self) -> None:
        self.tshub_env._close_simulation()
        self.tshub_render.destroy()
