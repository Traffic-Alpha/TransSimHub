'''
@Author: WANG Maonan
@Date: 2024-07-26 03:49:43
@Description: 多路口的 3D 可视化 (路口视角, 十字路口 & 丁字路口)
LastEditTime: 2025-04-15 15:30:36
'''
import random
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.tshub_env3d import Tshub3DEnvironment
from tshub.tshub_env3d.show_sensor_images import show_sensor_images
path_convert = get_abs_path(__file__)
set_logger(path_convert('./'), terminal_log_level='INFO')


if __name__ == '__main__':
    sumo_cfg = path_convert(f"./sumo_net/multi_junctions.sumocfg")
    scenario_glb_dir = path_convert(f"./3d_assets/")
    tshub_env3d = Tshub3DEnvironment(
        sumo_cfg=sumo_cfg,
        scenario_glb_dir=scenario_glb_dir,
        is_map_builder_initialized=False,
        is_aircraft_builder_initialized=False, 
        is_vehicle_builder_initialized=True, 
        is_traffic_light_builder_initialized=True, # 需要打开信号灯才会有路口的摄像头
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
            'tls': {
                "J1":{
                    'sensor_types': ['junction_front_all'],
                    'tls_camera_height': 15,
                },
                "J4":{
                    'sensor_types': ['junction_back_all'],
                    'tls_camera_height': 10,
                },
            } # 每个路口设置不同的传感器
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
                    # 十字路口
                    sensor_data.get('J1_0', {}).get('junction_front_all', None),
                    sensor_data.get('J1_1', {}).get('junction_front_all', None),
                    sensor_data.get('J1_2', {}).get('junction_front_all', None),
                    sensor_data.get('J1_3', {}).get('junction_front_all', None),

                    # 丁字路口
                    sensor_data.get('J4_0', {}).get('junction_back_all', None),
                    sensor_data.get('J4_1', {}).get('junction_back_all', None),
                    sensor_data.get('J4_2', {}).get('junction_back_all', None),
                ],
                scale=0.5,
                images_per_row=4
            ) # 展示路口的摄像头

    tshub_env3d.close()