'''
@Author: WANG Maonan
@Date: 2024-07-08 00:32:12
@Description: 单路口 3D 可视化, 查看信號燈的可視化
@LastEditTime: 2024-08-12 14:55:04
'''
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.tshub_env3d import Tshub3DEnvironment
from tshub.tshub_env3d.show_sensor_images import show_sensor_images
path_convert = get_abs_path(__file__)
set_logger(path_convert('./'), terminal_log_level='INFO')


if __name__ == '__main__':
    sumo_cfg = path_convert(f"../sumo_env/single_junction/env/single_junction.sumocfg")
    scenario_glb_dir = path_convert(f"./map_model_single/")
    tshub_env3d = Tshub3DEnvironment(
        sumo_cfg=sumo_cfg,
        scenario_glb_dir=scenario_glb_dir,
        is_aircraft_builder_initialized=False,
        is_map_builder_initialized=False,
        is_vehicle_builder_initialized=True, 
        is_traffic_light_builder_initialized=True, # 需要打开信号灯才会有路口的摄像头
        tls_ids=['htddj_gsndj'],
        vehicle_action_type='lane_continuous_speed',
        use_gui=True, 
        num_seconds=500,
        collision_action="warn",
        # 下面是用于渲染的参数
        render_mode="offscreen", # 如果设置了 use_render_pipeline, 此时只能是 onscreen
        debuger_print_node=False,
        debugr_spin_camera=True,
        sensor_config={
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
                'tls': {'htddj_gsndj': 0},
            }
            obs, reward, info, done, sensor_data = tshub_env3d.step(actions=actions)
            i_steps += 1

            show_sensor_images(
                [
                    sensor_data.get('htddj_gsndj_0', {}).get('junction_front_all', None),
                    sensor_data.get('htddj_gsndj_1', {}).get('junction_front_all', None),
                    sensor_data.get('htddj_gsndj_2', {}).get('junction_front_all', None),
                    sensor_data.get('htddj_gsndj_3', {}).get('junction_front_all', None),
                ],
                scale=1,
                images_per_row=4
            ) # 展示路口的摄像头

    tshub_env3d.close()