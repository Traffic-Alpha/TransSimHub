'''
@Author: WANG Maonan
@Date: 2024-07-08 00:32:12
@Description: 单路口 3D 可视化, 对信号灯四个方向的可视化 (分别是前拍和后拍)
LastEditTime: 2025-04-15 12:05:01
'''
import random
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.tshub_env3d import Tshub3DEnvironment
from tshub.tshub_env3d.show_sensor_images import show_sensor_images
path_convert = get_abs_path(__file__)
set_logger(path_convert('./'), terminal_log_level='INFO')


if __name__ == '__main__':
    sumo_cfg = path_convert(f"./sumo_net/single_junction.sumocfg")
    scenario_glb_dir = path_convert(f"./3d_assets/")
    tshub_env3d = Tshub3DEnvironment(
        sumo_cfg=sumo_cfg,
        scenario_glb_dir=scenario_glb_dir,
        is_aircraft_builder_initialized=False,
        is_map_builder_initialized=False,
        is_vehicle_builder_initialized=True, 
        is_traffic_light_builder_initialized=True, # 需要打开信号灯才会有路口的摄像头
        tls_ids=['J3'],
        vehicle_action_type='lane_continuous_speed',
        use_gui=True, 
        num_seconds=500,
        collision_action="warn",
        # 下面是用于渲染的参数
        preset="320P",
        render_mode="onscreen", # 如果设置了 use_render_pipeline, 此时只能是 onscreen
        debuger_print_node=False,
        debuger_spin_camera=True,
        sensor_config={
            'tls': {
                "J3":{
                    'sensor_types': [
                        'junction_front_all', 'junction_front_vehicle',
                        'junction_back_all', 'junction_back_vehicle'
                    ],
                    'tls_camera_height': 15,
                }

            } # 每个路口设置不同的传感器
        }
    )

    for _ in range(10):
        obs = tshub_env3d.reset()
        done = False
        i_steps = 0
        while not done:
            random_phase = random.randint(0, 3) # 随机选择相位
            actions = {
                'vehicle': dict(),
                'tls': {'J3': random_phase},
            }
            obs, reward, info, done, sensor_data = tshub_env3d.step(actions=actions)
            i_steps += 1

            show_sensor_images(
                [
                    sensor_data.get('J3_0', {}).get('junction_front_all', None),
                    sensor_data.get('J3_1', {}).get('junction_front_all', None),
                    sensor_data.get('J3_2', {}).get('junction_front_all', None),
                    sensor_data.get('J3_3', {}).get('junction_front_all', None),

                    sensor_data.get('J3_0', {}).get('junction_front_vehicle', None),
                    sensor_data.get('J3_1', {}).get('junction_front_vehicle', None),
                    sensor_data.get('J3_2', {}).get('junction_front_vehicle', None),
                    sensor_data.get('J3_3', {}).get('junction_front_vehicle', None),

                    sensor_data.get('J3_0', {}).get('junction_back_all', None),
                    sensor_data.get('J3_1', {}).get('junction_back_all', None),
                    sensor_data.get('J3_2', {}).get('junction_back_all', None),
                    sensor_data.get('J3_3', {}).get('junction_back_all', None),

                    sensor_data.get('J3_0', {}).get('junction_back_vehicle', None),
                    sensor_data.get('J3_1', {}).get('junction_back_vehicle', None),
                    sensor_data.get('J3_2', {}).get('junction_back_vehicle', None),
                    sensor_data.get('J3_3', {}).get('junction_back_vehicle', None),
                ],
                scale=1,
                images_per_row=4
            ) # 展示路口的摄像头

    tshub_env3d.close()