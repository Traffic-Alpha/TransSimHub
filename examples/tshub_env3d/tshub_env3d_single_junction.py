'''
@Author: WANG Maonan
@Date: 2024-07-08 00:32:12
@Description: 单路口 3D 可视化
@LastEditTime: 2024-07-25 01:02:02
'''
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.tshub_env3d import Tshub3DEnvironment
from tshub.tshub_env3d.show_sensor_images import show_sensor_images # TODO, 检查这个会有 QT 的报错和提示
path_convert = get_abs_path(__file__)
set_logger(path_convert('./'), terminal_log_level='INFO')


aircraft_inits = {
    'a1': {
        "aircraft_type": "drone",
        "action_type": "horizontal_movement", # 水平移动
        "position":(1754, 896, 50), "speed":3, "heading":(1,1,0), # 初始信息
        "communication_range":100, 
        "if_sumo_visualization":True, "img_file":None,
        "custom_update_cover_radius":None # 使用自定义的计算
    },
    'a2': {
        "aircraft_type": "drone",
        "action_type": "vertical_movement", # 垂直移动
        "position":(1781, 932, 70), "speed":1, "heading":(1,1,0), # 初始信息1781.65,932.40
        "communication_range":100, 
        "if_sumo_visualization":True, "img_file":None,
        "custom_update_cover_radius":None
    }
}

if __name__ == '__main__':
    sumo_cfg = path_convert(f"../sumo_env/single_junction/env/single_junction.sumocfg")
    scenario_glb_dir = path_convert(f"./map_model/")
    tshub_env3d = Tshub3DEnvironment(
        sumo_cfg=sumo_cfg,
        scenario_glb_dir=scenario_glb_dir,
        is_map_builder_initialized=False,
        is_aircraft_builder_initialized=True, 
        is_vehicle_builder_initialized=True, 
        is_traffic_light_builder_initialized=True, # 需要打开信号灯才会有路口的摄像头
        aircraft_inits=aircraft_inits,
        tls_ids=['htddj_gsndj'],
        vehicle_action_type='lane_continuous_speed',
        use_gui=True, 
        num_seconds=1000,
        collision_action="warn",
        # 下面是用于渲染的参数
        render_mode="onscreen", # 如果设置了 use_render_pipeline, 此时只能是 onscreen
        sensor_config={
            # 'vehicle': ['front_all', 'back_all'],
            'aircraft': ['aircraft_all', 'aircraft_vehicle'],
            # 'tls': ['junction_front_all']
        }
    )

    for _ in range(3):
        obs = tshub_env3d.reset()
        done = False
        i_steps = 0
        while not done:
            actions = {
                'vehicle': dict(),
                'tls': {'htddj_gsndj': 0},
                'aircraft': {
                    "a1": (0.5, (i_steps//40)%8),
                    "a2": (0.5, (i_steps//60)%3),
                }
            }
            obs, reward, info, done, sensor_data = tshub_env3d.step(actions=actions)
            i_steps += 1

            # 将 sensor_data 的数据保存为图片, 文件夹为 element_id, 然后是每一个 element 中的 camera type


            # show_sensor_images(
            #     [
            #         # sensor_data.get('ego_gsndj_s4', {}).get('front_left_all', None),
            #         # sensor_data.get('ego_gsndj_s4', {}).get('front_all', None),
            #         # sensor_data.get('ego_gsndj_s4', {}).get('front_right_all', None),

            #         # sensor_data.get('ego_gsndj_s4', {}).get('back_left_all', None),
            #         # sensor_data.get('ego_gsndj_s4', {}).get('back_all', None),
            #         # sensor_data.get('ego_gsndj_s4', {}).get('back_right_all', None),

            #         # sensor_data.get('ego_gsndj_s4', {}).get('front_left_vehicle', None),
            #         # sensor_data.get('ego_gsndj_s4', {}).get('front_vehicle', None),
            #         # sensor_data.get('ego_gsndj_s4', {}).get('front_right_vehicle', None),

            #         # sensor_data.get('ego_gsndj_s4', {}).get('back_left_vehicle', None),
            #         # sensor_data.get('ego_gsndj_s4', {}).get('back_vehicle', None),
            #         # sensor_data.get('ego_gsndj_s4', {}).get('back_right_vehicle', None),
                    
            #         sensor_data.get('ego_gsndj_s4', {}).get('bev_all', None),
            #         sensor_data.get('ego_gsndj_s4', {}).get('bev_vehicle', None)
            #     ],
            #     scale=0.5,
            #     images_per_row=2
            # ) # 展示 ego 车辆的视角

            # show_sensor_images(
            #     [
            #         sensor_data.get('htddj_gsndj_0', {}).get('junction_back_all', None),
            #         sensor_data.get('htddj_gsndj_1', {}).get('junction_back_all', None),
            #         sensor_data.get('htddj_gsndj_2', {}).get('junction_back_all', None),
            #         sensor_data.get('htddj_gsndj_3', {}).get('junction_back_all', None),

            #         sensor_data.get('htddj_gsndj_0', {}).get('junction_back_vehicle', None),
            #         sensor_data.get('htddj_gsndj_1', {}).get('junction_back_vehicle', None),
            #         sensor_data.get('htddj_gsndj_2', {}).get('junction_back_vehicle', None),
            #         sensor_data.get('htddj_gsndj_3', {}).get('junction_back_vehicle', None),
            #     ],
            #     scale=1,
            #     images_per_row=4
            # ) # 展示路口的摄像头

            show_sensor_images(
                [
                    sensor_data.get('a1', {}).get('aircraft_all', None),
                    sensor_data.get('a2', {}).get('aircraft_all', None),

                    sensor_data.get('a1', {}).get('aircraft_vehicle', None),
                    sensor_data.get('a2', {}).get('aircraft_vehicle', None),
                ],
                scale=1,
                images_per_row=2
            ) # 展示 Aircraft 的摄像头
    tshub_env3d.close()