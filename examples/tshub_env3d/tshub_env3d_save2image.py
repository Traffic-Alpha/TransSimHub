'''
@Author: WANG Maonan
@Date: 2024-07-21 04:18:03
@Description: 将传感器的数据保存下来
@LastEditTime: 2024-07-21 04:34:12
'''
import os
import cv2
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.tshub_env3d import Tshub3DEnvironment
path_convert = get_abs_path(__file__)
set_logger(path_convert('./'), terminal_log_level='INFO')

def convert_rgb_to_bgr(image):
    # Convert an RGB image to BGR
    return image[:, :, ::-1]

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
    route_xml = path_convert(f"../sumo_env/single_junction/env/random.rou.xml")
    scenario_glb_dir = path_convert(f"./map_model/")
    tshub_env3d = Tshub3DEnvironment(
        sumo_cfg=sumo_cfg,
        route_file=route_xml,
        scenario_glb_dir=scenario_glb_dir,
        is_map_builder_initialized=False,
        is_aircraft_builder_initialized=True, 
        is_vehicle_builder_initialized=True, 
        is_traffic_light_builder_initialized=True, # 需要打开信号灯才会有路口的摄像头
        aircraft_inits=aircraft_inits,
        tls_ids=['htddj_gsndj'],
        vehicle_action_type='lane_continuous_speed',
        use_gui=False, 
        num_seconds=300,
        collision_action="warn",
        use_render_pipeline=False,
        render_mode="onscreen", # 如果设置了 use_render_pipeline, 此时只能是 onscreen
    )


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

        # 将 sensor_data 的数据保存为图片
        base_path = path_convert(f"./env3d_images/")
        for element_id, cameras in sensor_data.items():
            # Iterate over each camera type
            for camera_type, image_array in cameras.items():
                # Create directory for the camera_type if it doesn't exist
                camera_dir = os.path.join(base_path, element_id, camera_type)
                if not os.path.exists(camera_dir):
                    os.makedirs(camera_dir)

                # Construct the image file path
                image_path = os.path.join(camera_dir, f"{i_steps}.png")
                # Save the numpy array as an image
                cv2.imwrite(image_path, convert_rgb_to_bgr(image_array))
    tshub_env3d.close()