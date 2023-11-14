'''
@Author: WANG Maonan
@Date: 2023-11-12 14:54:32
@Description: 对场景进行可视化, 对 vehicle 进行 render
@LastEditTime: 2023-11-13 23:31:12
'''
from loguru import logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.check_folder import check_folder
from tshub.utils.init_log import set_logger
from tshub.tshub_env.tshub_env import TshubEnvironment


path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumo_cfg = path_convert("../../sumo_env/osm_berlin/env/berlin.sumocfg")
net_file = path_convert("../../sumo_env/osm_berlin/env/berlin.net.xml")
osm_file = path_convert("../../sumo_env/osm_berlin/berlin.osm")
poly_file = path_convert("../../sumo_env/osm_berlin/env/berlin.poly.xml")

# 创建存储图像的文件夹
image_save_folder = path_convert('./vehicle/')
check_folder(image_save_folder)

# 初始化环境
tshub_env = TshubEnvironment(
    sumo_cfg=sumo_cfg,
    net_file=net_file,
    is_map_builder_initialized=True,
    is_vehicle_builder_initialized=True, 
    is_aircraft_builder_initialized=False, 
    is_traffic_light_builder_initialized=False,
    # map builder
    osm_file=osm_file,
    poly_file=poly_file,
    # vehicle builder
    vehicle_action_type='lane',
    use_gui=True, num_seconds=300
)

# 开始仿真
obs = tshub_env.reset()
done = False

while not done:
    actions = {
        'vehicle': dict(), # 不控制车辆
    }
    obs, reward, info, done = tshub_env.step(actions=actions)
    fig = tshub_env.render(
        focus_id='-1105574288#1__0__background.1', 
        focus_type='vehicle', 
        focus_distance=80,
        mode='sumo_gui',
        save_folder=image_save_folder
    )
    step_time = int(info["step_time"])
    logger.info(f"SIM: {step_time}")

tshub_env._close_simulation()