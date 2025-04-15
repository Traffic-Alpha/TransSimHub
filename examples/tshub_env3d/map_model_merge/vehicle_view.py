'''
Author: Maonan Wang
Date: 2025-03-28 18:46:40
LastEditTime: 2025-04-15 12:33:19
LastEditors: Maonan Wang
Description: 车辆视角可视化 (单车, 测试 SUMO 和 TSHub3D 同步)
FilePath: /TransSimHub/examples/tshub_env3d/map_model_merge/vehicle_view.py
'''
from loguru import logger
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.tshub_env3d import Tshub3DEnvironment
from tshub.tshub_env3d.show_sensor_images import show_sensor_images
path_convert = get_abs_path(__file__)
set_logger(path_convert('./'), terminal_log_level='DEBUG')

aircraft_inits = {
    'a1': {
        "aircraft_type": "drone",
        "action_type": "stationary", # 静止不动
        "position":(16.95, -3.15, 30), "speed":0, "heading":(0,0,0), # 初始信息
        "communication_range":5, 
        "if_sumo_visualization":True, "img_file":None,
        "custom_update_cover_radius":None # 使用自定义的计算
    },
}

if __name__ == '__main__':
    sumo_cfg = path_convert(f"./sumo/merge.sumocfg")
    scenario_glb_dir = path_convert(f"./model/")
    tshub_env3d = Tshub3DEnvironment(
        sumo_cfg=sumo_cfg,
        scenario_glb_dir=scenario_glb_dir,
        is_map_builder_initialized=False,
        is_aircraft_builder_initialized=True, 
        is_vehicle_builder_initialized=True, 
        is_traffic_light_builder_initialized=False,
        is_person_builder_initialized=False,
        aircraft_inits=aircraft_inits,
        vehicle_action_type='lane_continuous_speed',
        use_gui=True, 
        num_seconds=30,
        collision_action="warn",
        # 下面是用于渲染的参数
        preset="480P",
        render_mode="offscreen", # 如果设置了 use_render_pipeline, 此时只能是 onscreen
        debuger_print_node=False,
        debuger_spin_camera=False,
        sensor_config={
            'vehicle': {
                '0': {'sensor_types': ['bev_all']},
            }, # 只给一辆车挂载摄像头
            'aircraft': {
                "a1": {"sensor_types": ['aircraft_all']}
            },
        }
    )

    obs = tshub_env3d.reset()
    done = False
    i_steps = 0
    
    while not done:
        actions = {
            'vehicle': dict(),
        }
        obs, reward, info, done, sensor_data = tshub_env3d.step(actions=actions)

        # 解析 obs, 获得车辆的实时信息
        vehicle_info = obs['vehicle'].get('0', {})
        vehicle_pos = vehicle_info.get('position', None) # 车辆的位置 (x,y)
        lane_id = vehicle_info.get('lane_id', None) # 车辆所在的 lane id
        lane_position = vehicle_info.get('lane_position', None) # 车辆在 lane 上面的位置
        logger.info(f"SIM: Vehicle Lane, {lane_id}; Lane Position: {lane_position}; Vehicle Position: {vehicle_pos};")

        # 显示图像
        try:
            show_sensor_images(
                [
                    sensor_data.get('0', {}).get('bev_all', None),
                    sensor_data.get('a1', {}).get('aircraft_all', None),
                ],
                scale=1,
                images_per_row=2
            ) # 展示路口的摄像头
        except:
            pass

        # 仿真 Next Step
        i_steps += 1

    tshub_env3d.close()