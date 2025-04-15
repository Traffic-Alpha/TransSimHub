'''
Author: Maonan Wang
Date: 2025-04-11 18:24:32
LastEditTime: 2025-04-14 19:55:24
LastEditors: Maonan Wang
Description: 摄像头视角保存图片
FilePath: /TransSimHub/examples/tshub_env3d/map_model_single/tls_view_save_image.py
'''
import os
import cv2
import random
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.tshub_env3d import Tshub3DEnvironment
path_convert = get_abs_path(__file__)
set_logger(path_convert('./'), terminal_log_level='INFO')

def convert_rgb_to_bgr(image):
    # Convert an RGB image to BGR
    return image[:, :, ::-1]

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
        use_gui=False, 
        num_seconds=500,
        collision_action="warn",
        # 下面是用于渲染的参数
        preset="1080P",
        render_mode="onscreen", # 如果设置了 use_render_pipeline, 此时只能是 onscreen
        debuger_print_node=False,
        debuger_spin_camera=True,
        sensor_config={
            'tls': {
                "J3":{
                    'sensor_types': ['junction_front_all'],
                    'tls_camera_height': 15,
                }

            } # 每个路口设置不同的传感器
        }
    )

    for _ in range(3):
        obs = tshub_env3d.reset()
        done = False
        i_steps = 0
        while not done:
            random_phase = random.randint(0, 3)
            actions = {
                'vehicle': dict(),
                'tls': {'J3': random_phase},
            }
            obs, reward, info, done, sensor_data = tshub_env3d.step(actions=actions)
            i_steps += 1


            # 将 sensor_data 的数据保存为图片
            base_path = path_convert(f"./_outputs/")
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