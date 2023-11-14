'''
@Author: WANG Maonan
@Date: 2023-11-12 14:54:32
@Description: 对场景进行可视化, 对 node 进行 render
@LastEditTime: 2023-11-13 23:29:37
'''
from loguru import logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.check_folder import check_folder
from tshub.utils.init_log import set_logger
from tshub.tshub_env.tshub_env import TshubEnvironment
from tshub.utils.plt_to_array import plt2arr

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumo_cfg = path_convert("../../sumo_env/osm_berlin/env/berlin.sumocfg")
net_file = path_convert("../../sumo_env/osm_berlin/env/berlin.net.xml")
osm_file = path_convert("../../sumo_env/osm_berlin/berlin.osm")
poly_file = path_convert("../../sumo_env/osm_berlin/env/berlin.poly.xml")

# 创建存储图像的文件夹
image_save_folder = path_convert('./node/')
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
        focus_id='25663429', 
        focus_type='node', 
        focus_distance=80,
        mode='rgb'
    )
    fig_array = plt2arr(fig) # convert fig to array

    step_time = int(info["step_time"])
    fig.savefig(f'{image_save_folder}/{step_time}.png', bbox_inches='tight', pad_inches=0)
    logger.info(f"SIM: {step_time}")

tshub_env._close_simulation()