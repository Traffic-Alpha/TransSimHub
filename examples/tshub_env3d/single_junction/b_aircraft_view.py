'''
@Author: WANG Maonan
@Date: 2024-07-08 00:32:12
@Description: 单路口 3D 可视化 (无人机视角)
LastEditTime: 2025-04-15 12:00:34
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
        "action_type": "horizontal_movement", # 水平移动
        "position":(1542, 1007, 50), "speed":3, "heading":(1,1,0), # 初始位置
        "communication_range":100, 
        "if_sumo_visualization":True, "img_file":None,
        "custom_update_cover_radius":None # 使用自定义的计算
    },
    'a2': {
        "aircraft_type": "drone",
        "action_type": "vertical_movement", # 垂直移动
        "position":(1542, 1007, 70), "speed":1, "heading":(1,1,0), # 初始位置
        "communication_range":100, 
        "if_sumo_visualization":True, "img_file":None,
        "custom_update_cover_radius":None
    }
}

if __name__ == '__main__':
    sumo_cfg = path_convert(f"./sumo_net/single_junction.sumocfg")
    scenario_glb_dir = path_convert(f"./3d_assets/")
    tshub_env3d = Tshub3DEnvironment(
        sumo_cfg=sumo_cfg,
        scenario_glb_dir=scenario_glb_dir,
        is_map_builder_initialized=False,
        is_aircraft_builder_initialized=True, 
        is_vehicle_builder_initialized=True, 
        is_traffic_light_builder_initialized=True, # 需要打开信号灯才会有路口的摄像头
        aircraft_inits=aircraft_inits,
        tls_ids=['J3'],
        vehicle_action_type='lane_continuous_speed',
        use_gui=True, 
        num_seconds=200,
        collision_action="warn",
        # 下面是用于渲染的参数
        render_mode="onscreen", # 如果设置了 use_render_pipeline, 此时只能是 onscreen
        debuger_print_node=False,
        debuger_spin_camera=True,
        preset="480P",
        resolution=1,
        sensor_config={
            'aircraft': {
                "a1": {"sensor_types": ['aircraft_all']},
                "a2": {"sensor_types": ['aircraft_vehicle']}
            }
        }
    )

    for _ in range(10):
        obs = tshub_env3d.reset()
        done = False
        i_steps = 0
        while not done:
            random_phase = random.randint(0, 3)
            actions = {
                'vehicle': dict(),
                'tls': {'J3': random_phase},
                'aircraft': {
                    "a1": (0.5, (i_steps//40)%8),
                    "a2": (0.5, (i_steps//60)%3),
                }
            }
            obs, reward, info, done, sensor_data = tshub_env3d.step(actions=actions)
            i_steps += 1

            show_sensor_images(
                [
                    sensor_data.get('a1', {}).get('aircraft_all', None),
                    sensor_data.get('a2', {}).get('aircraft_vehicle', None),
                ],
                scale=1,
                images_per_row=2
            ) # 展示 Aircraft 的摄像头
    tshub_env3d.close()