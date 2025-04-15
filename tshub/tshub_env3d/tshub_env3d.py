'''
@Author: WANG Maonan
@Date: 2024-07-07 23:30:33
@Description: TSHub 环境的 3D 版本, 整体的逻辑为:
- TshubEnvironment 与 SUMO 进行交互, 获得 SUMO 的数据 (这部分利用 TshubEnvironment)
- TSHubRenderer 对 SUMO 的环境进行渲染 (这部分利用 TSHubRenderer)
- TShubSensor 获得渲染的场景的数据, 作为新的 state 进行输出
LastEditTime: 2025-04-15 15:37:57
'''
from loguru import logger
from typing import Any, Dict, List, Callable

from .base_env3d import BaseSumoEnvironment3D

from ..tshub_env.tshub_env import TshubEnvironment # tshub 与 sumo 交互
from .vis3d_renderer.tshub_render import TSHubRenderer # tshub3D render

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
            preset:str = '480P', 
            resolution:float = 0.5,
            render_mode: str = "onscreen",
            debuger_print_node:bool = False, # 是否在 reset 的时候打印 node path
            debuger_spin_camera:bool = False, # 是否显示 spin camera
            sensor_config: Dict[str, List[str]] = None,
            modify_states:Callable[[Any],Any]=None, # 对 tshub 返回的 state 进行修改
        ) -> None:

        self.debuger_print_node = debuger_print_node
        self.debuger_spin_camera = debuger_spin_camera

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
            simid=f"tshub-{self.tshub_env.CONNECTION_LABEL}", # 场景的 ID
            scenario_glb_dir=scenario_glb_dir,
            sensor_config=sensor_config,
            preset=preset,
            resolution=resolution,
            render_mode=render_mode,
        )

        self.modify_states = modify_states
        
    def reset(self):
        state_infos = self.tshub_env.reset() # 重置 sumo 环境
        logger.info(f'SIM: 完成 TSHub 初始化, 得到地图和信号灯信息.')

        self.tshub_render.reset(state_infos) # 重置 render, 需要将信号灯的信息传入, 辅助进行路口 camera 的初始化

        # 加入一个简单任务, 避免 userExit 出错
        self.tshub_render._showbase_instance.taskMgr.add(
            self.tshub_render.dummyTask, "dummyTask"
        )

        # 重置后打印 node path (查看每次 reset 是否会重置所有 node 和 camera)
        if self.debuger_print_node:
            self.tshub_render.print_node_paths(self.tshub_render._root_np)

        # 场景添加相机, 可以进行可视化
        if self.debuger_spin_camera:
            self.tshub_render._showbase_instance.taskMgr.add(
                self.tshub_render.test_spin_camera_task, 
                "SpinCamera"
            )

        return state_infos
    
    def step(self, actions):
        # 1. 与 SUMO 进行交互
        states, rewards, infos, dones = self.tshub_env.step(actions)
        
        # 2. 可以对 states 进行修改 (例如添加新的车辆用于渲染)
        if self.modify_states:
            states = self.modify_states(states)

        # 3. 渲染 3D 的场景
        sensor_data = self.tshub_render.step(states) # 运行 panda3d
        
        # 将 image 的信息通过 sensor_data 进行返回
        return states, rewards, infos, dones, sensor_data

    def close(self) -> None:
        self.tshub_env._close_simulation()
        self.tshub_render.destroy()
