'''
@Author: WANG Maonan
@Date: 2024-07-08 00:32:12
@Description: 单路口 3D 可视化 (车辆视角)
LastEditTime: 2025-03-25 19:03:17
'''
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.tshub_env3d import Tshub3DEnvironment
from tshub.tshub_env3d.show_sensor_images import show_sensor_images # TODO, 检查这个会有 QT 的报错和提示
path_convert = get_abs_path(__file__)
set_logger(path_convert('./'), terminal_log_level='INFO')




if __name__ == '__main__':
    sumo_cfg = path_convert(f"../sumo_env/single_junction/env/single_junction.sumocfg")
    scenario_glb_dir = path_convert(f"./map_model_single/")
    tshub_env3d = Tshub3DEnvironment(
        sumo_cfg=sumo_cfg,
        scenario_glb_dir=scenario_glb_dir,
        is_map_builder_initialized=False,
        is_aircraft_builder_initialized=False, 
        is_vehicle_builder_initialized=True, 
        is_traffic_light_builder_initialized=True, # 需要打开信号灯才会有路口的摄像头
        tls_ids=['htddj_gsndj'],
        vehicle_action_type='lane_continuous_speed',
        use_gui=True, 
        num_seconds=200,
        collision_action="warn",
        # 下面是用于渲染的参数
        render_mode="offscreen", # 如果设置了 use_render_pipeline, 此时只能是 onscreen
        debuger_print_node=False,
        debuger_spin_camera=True,
        preset="480P",
        resolution=1,
        sensor_config={
            'vehicle': {
                'ego_gsndj_s4': {
                    'sensor_types': [
                        'front_left_all', 'front_all', 'front_right_all',
                        'back_left_all', 'back_all', 'back_right_all',
                        'front_left_vehicle', 'front_vehicle', 'front_right_vehicle',
                        'back_left_vehicle', 'back_vehicle', 'back_right_vehicle',
                        'bev_all', 'bev_vehicle'
                    ],
                } # 只给指定车辆安装传感器
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
                'tls': {'htddj_gsndj': 0},
            }
            obs, reward, info, done, sensor_data = tshub_env3d.step(actions=actions)
            i_steps += 1

            # 车辆会在 120 step 的时候进入仿真
            show_sensor_images(
                [
                    sensor_data.get('ego_gsndj_s4', {}).get('front_left_all', None),
                    sensor_data.get('ego_gsndj_s4', {}).get('front_all', None),
                    sensor_data.get('ego_gsndj_s4', {}).get('front_right_all', None),

                    sensor_data.get('ego_gsndj_s4', {}).get('back_left_all', None),
                    sensor_data.get('ego_gsndj_s4', {}).get('back_all', None),
                    sensor_data.get('ego_gsndj_s4', {}).get('back_right_all', None),

                    sensor_data.get('ego_gsndj_s4', {}).get('front_left_vehicle', None),
                    sensor_data.get('ego_gsndj_s4', {}).get('front_vehicle', None),
                    sensor_data.get('ego_gsndj_s4', {}).get('front_right_vehicle', None),

                    sensor_data.get('ego_gsndj_s4', {}).get('back_left_vehicle', None),
                    sensor_data.get('ego_gsndj_s4', {}).get('back_vehicle', None),
                    sensor_data.get('ego_gsndj_s4', {}).get('back_right_vehicle', None),
                    
                    sensor_data.get('ego_gsndj_s4', {}).get('bev_all', None),
                    sensor_data.get('ego_gsndj_s4', {}).get('bev_vehicle', None)
                ],
                scale=0.5,
                images_per_row=3
            ) # 展示 ego 车辆的视角
    tshub_env3d.close()