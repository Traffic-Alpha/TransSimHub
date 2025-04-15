'''
@Author: WANG Maonan
@Date: 2024-07-26 03:49:43
@Description: 多路口的 3D 可视化 (飞行器视角)
LastEditTime: 2025-04-15 15:38:31
'''
import random
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.tshub_env3d import Tshub3DEnvironment
from tshub.tshub_env3d.show_sensor_images import show_sensor_images
path_convert = get_abs_path(__file__)
set_logger(path_convert('./'), terminal_log_level='INFO')

aircraft_inits = {
    'a1': {
        "aircraft_type": "drone",
        "action_type": "stationary", # 静止不动
        "position":(125, -6, 50), "speed":3, "heading":(1,1,0), # 初始位置
        "communication_range":100, 
        "if_sumo_visualization":True, "img_file":None,
        "custom_update_cover_radius":None # 使用自定义的计算
    },
}

if __name__ == '__main__':
    sumo_cfg = path_convert(f"./sumo_net/multi_junctions.sumocfg")
    scenario_glb_dir = path_convert(f"./3d_assets/")
    tshub_env3d = Tshub3DEnvironment(
        sumo_cfg=sumo_cfg,
        scenario_glb_dir=scenario_glb_dir,
        is_map_builder_initialized=False,
        is_aircraft_builder_initialized=True, 
        is_vehicle_builder_initialized=True, 
        is_traffic_light_builder_initialized=True, # 需要打开信号灯才会有路口的摄像头
        aircraft_inits=aircraft_inits,
        tls_ids=['J1', 'J4', 'J5'],
        vehicle_action_type='lane_continuous_speed',
        use_gui=True, 
        num_seconds=200,
        collision_action="warn",
        # 下面是用于渲染的参数
        preset="480P", resolution=1,
        render_mode="onscreen", # 如果设置了 use_render_pipeline, 此时只能是 onscreen
        debuger_print_node=False,
        debuger_spin_camera=True,
        sensor_config={
            'aircraft': {
                "a1": {"sensor_types": ['aircraft_all']},
            }
        }
    )

    for _ in range(10):
        obs = tshub_env3d.reset()
        done = False
        i_steps = 0
        while not done:
            actions = {
                'vehicle': dict(),
                'tls': {
                    'J1': random.randint(0, 3),
                    'J4': random.randint(0, 2),
                    'J5': random.randint(0, 3),
                },
            }
            obs, reward, info, done, sensor_data = tshub_env3d.step(actions=actions)
            i_steps += 1

            show_sensor_images(
                [
                    sensor_data.get('a1', {}).get('aircraft_all', None),
                ],
                scale=1,
            ) # 无人机视角

    tshub_env3d.close()