'''
Author: Maonan Wang
Date: 2025-03-25 17:05:36
LastEditTime: 2025-03-25 17:05:38
LastEditors: Maonan Wang
Description: 
FilePath: /TransSimHub/examples/tshub_env3d/multi_junctions_aircraft copy.py
'''
'''
Author: Maonan Wang
Date: 2025-03-25 17:05:27
LastEditTime: 2025-03-25 17:05:29
LastEditors: Maonan Wang
Description: 
FilePath: /TransSimHub/examples/tshub_env3d/multi_junctions_tls copy.py
'''
'''
@Author: WANG Maonan
@Date: 2024-07-26 03:49:43
@Description: 多路口的 3D 可视化
LastEditTime: 2025-01-16 14:37:00
'''
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.tshub_env3d import Tshub3DEnvironment
from tshub.tshub_env3d.show_sensor_images import show_sensor_images
path_convert = get_abs_path(__file__)
set_logger(path_convert('./'), terminal_log_level='INFO')


if __name__ == '__main__':
    sumo_cfg = path_convert(f"../sumo_env/osm_berlin/env/berlin.sumocfg")
    scenario_glb_dir = path_convert(f"./map_model_multi/")
    tshub_env3d = Tshub3DEnvironment(
        sumo_cfg=sumo_cfg,
        scenario_glb_dir=scenario_glb_dir,
        is_map_builder_initialized=False,
        is_aircraft_builder_initialized=False, 
        is_vehicle_builder_initialized=True, 
        is_traffic_light_builder_initialized=True, # 需要打开信号灯才会有路口的摄像头
        tls_ids=[
            '25663405', '25663436', 
            '25663407', '25663429',
            '25663423', '25663426'
        ],
        vehicle_action_type='lane_continuous_speed',
        use_gui=True, 
        num_seconds=200,
        collision_action="warn",
        # 下面是用于渲染的参数
        render_mode="onscreen", # 如果设置了 use_render_pipeline, 此时只能是 onscreen
        debuger_print_node=False,
        debuger_spin_camera=True,
        sensor_config={
            # 'vehicle': ['bev_all', 'bev_vehicle'],
            # 'aircraft': ['aircraft_all', 'aircraft_vehicle'],
            'tls': ['junction_front_all']
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
                    '25663405': 0, '25663436': 0, 
                    '25663407': 0, '25663429': 0,
                    '25663423': 0, '25663426': 0
                },
            }
            obs, reward, info, done, sensor_data = tshub_env3d.step(actions=actions)
            i_steps += 1

            show_sensor_images(
                [
                    sensor_data.get('25663405_0', {}).get('junction_front_all', None),
                    sensor_data.get('25663405_1', {}).get('junction_front_all', None),
                    sensor_data.get('25663405_2', {}).get('junction_front_all', None),
                    sensor_data.get('25663405_3', {}).get('junction_front_all', None),

                    # 丁字路口有四个相机
                    sensor_data.get('25663436_0', {}).get('junction_front_all', None),
                    sensor_data.get('25663436_1', {}).get('junction_front_all', None),
                    sensor_data.get('25663436_2', {}).get('junction_front_all', None),
                    sensor_data.get('25663436_3', {}).get('junction_front_all', None),
                ],
                scale=1,
                images_per_row=4
            ) # 展示路口的摄像头

    tshub_env3d.close()