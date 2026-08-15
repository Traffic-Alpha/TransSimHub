'''
@Author: WANG Maonan
@Date: 2026-08-11 10:00:00
@Description: 微观 + 中观 + 空中视角三视图合一
- 中观: 浏览器大屏, 全网路段/车道的拥堵着色 (打开终端打印的地址);
- 空中: UAV 从 A 点飞到 B 点后停下悬停, 机载俯拍相机常驻渲染, 图像每帧回传大屏;
        大屏上点击图像可以全屏放大 (放大后仍然是实时更新的);
- 关联: 每帧算出 UAV 附近有哪些车辆/路口, 大屏上与回传图像并排显示,
        所以能看到「UAV 此刻拍到的是哪一块路网、那一块正好有多堵」。
- 微观: use_gui=True 时会同时开 SUMO-GUI 逐车观察 (需要桌面环境)。

需要先有 3D 场景资产 (scenario_glb_dir), 见 examples/tshub_env3d/ 下的建场景脚本。
@LastEditTime: 2026-08-11 18:28:57
'''
import math
import time

from loguru import logger

from tshub.aircraft.aircraft_nearby import find_objects_near_aircraft
from tshub.visualization.meso import DashboardServer, build_static_payload, build_frame_payload, encode_image
from tshub.tshub_env3d.tshub_env3d import Tshub3DEnvironment
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'), terminal_log_level='ERROR')  # 大屏在前台, 日志调静

SCENARIO_GLB_DIR = path_convert("../tshub_env3d/single_junction/3d_assets")
SUMO_CFG = path_convert("../tshub_env3d/single_junction/sumo_net/single_junction.sumocfg")
NET_FILE = path_convert("../tshub_env3d/single_junction/sumo_net/single_junction.net.xml")

# UAV 从 A 点飞到 B 点, 到了就停下 (穿过路口, 沿途扫过不同的路段)
JUNCTION = (1557.0, 989.0)
POINT_A = (JUNCTION[0] - 130.0, JUNCTION[1])  # 起点: 路口以西
POINT_B = (JUNCTION[0] + 130.0, JUNCTION[1])  # 终点: 路口以东
UAV_ALTITUDE = 40.0
UAV_SPEED = 8.0
ARRIVE_TOLERANCE = 6.0  # 距离终点多近算「到了」
NEARBY_RADIUS = 80.0  # 认为 UAV「拍得到」的平面半径


def heading_index_towards(position, target) -> int:
    """朝目标点飞行的 horizontal_movement heading index (0~7, 每 45 度一档).

    horizontal_movement 的 0 度是 +X, 逆时针增大 (见 aircraft_type/horizontal_movement.py)。
    """
    dx = target[0] - position[0]
    dy = target[1] - position[1]
    return int(round(math.degrees(math.atan2(dy, dx)) % 360 / 45.0)) % 8


def distance_to(position, target) -> float:
    return math.hypot(target[0] - position[0], target[1] - position[1])


env = Tshub3DEnvironment(
    sumo_cfg=SUMO_CFG,
    net_file=NET_FILE,
    scenario_glb_dir=SCENARIO_GLB_DIR,
    # -- 中观视图需要的 builder --
    is_map_builder_initialized=True,   # obs['lane_shape'], 路网几何
    is_lane_builder_initialized=True,  # obs['lane_state'], 车道级拥堵
    is_edge_builder_initialized=True,  # obs['edge_state'], 路段级拥堵
    # -- 微观 / 空中 --
    is_vehicle_builder_initialized=True,
    is_aircraft_builder_initialized=True,
    is_traffic_light_builder_initialized=True,
    is_person_builder_initialized=False,
    tls_ids=['J3'],
    aircraft_inits={'drone_1': {
        'aircraft_type': 'drone', 'action_type': 'horizontal_movement',
        'position': (POINT_A[0], POINT_A[1], UAV_ALTITUDE),
        'speed': UAV_SPEED, 'heading': (1, 0, 0),
        'communication_range': 100, 'if_sumo_visualization': False,
    }},
    vehicle_action_type='lane_continuous_speed',
    use_gui=True,  # 改成 True 可同时开 SUMO-GUI 看微观
    is_libsumo=False,
    num_seconds=600, collision_action='warn', sumo_seed='7',
    # -- UAV 机载相机: 常驻渲染, 每步回传 --
    # 720P: 大屏上要看清路面, 320P 缩到侧栏里基本什么都看不出来
    preset='720P', render_mode='offscreen', rendering_backend='pandagl',
    # 只要俯拍: aircraft_rgb 是正交俯视相机 (机身正下方看地面), 与中观视图的
    # 俯视语义一致; aircraft_front (前下斜视) / aircraft_chase (外部跟拍) 都不需要
    sensor_config={'aircraft': {'drone_1': {
        'sensor_types': ['aircraft_rgb'],
    }}},
)

dashboard = DashboardServer(port=8910)
url = dashboard.start()
print(f'\n>>> 中观大屏: {url}   (Ctrl-C 结束)\n')

states = env.reset()
static_payload = build_static_payload(states)
dashboard.set_static(static_payload)

step, done, arrived = 0, False, False
infos = {'step_time': 0}  # 第一次 step 之前先占位, 免得到达判定里引用到未定义的变量
try:
    while not done:
        # UAV 从 A 飞向 B, 到了就停 (速度置 0, 之后原地悬停继续回传画面)
        uav_position = states['aircraft']['drone_1']['position']
        if distance_to(uav_position, POINT_B) <= ARRIVE_TOLERANCE:
            if not arrived:
                arrived = True
                print(f'>>> UAV arrived at B {POINT_B}, hovering. (t={infos["step_time"]}s)')
            uav_action = (0.0, heading_index_towards(uav_position, POINT_B))
        else:
            uav_action = (UAV_SPEED, heading_index_towards(uav_position, POINT_B))

        actions = {
            'vehicle': dict(),
            'tls': {'J3': 0},
            'aircraft': {'drone_1': uav_action},
        }
        states, _, infos, done, sensor_data = env.step(actions)

        # UAV 附近有哪些对象 (用于大屏高亮 + 与回传图像关联)
        nearby = find_objects_near_aircraft(
            states, radius=NEARBY_RADIUS, targets=['vehicle', 'tls'], max_per_type=20,
        )

        # UAV 机载相机的图像 -> base64 PNG, 直接塞进大屏
        images = {
            f'{element_id}/{sensor_type}': encode_image(image)
            for element_id, cameras in sensor_data.items()
            for sensor_type, image in cameras.items()
        }

        dashboard.push(build_frame_payload(
            sim_time=infos['step_time'], obs=states,
            static_payload=static_payload, images=images, nearby=nearby,
        ))
        time.sleep(0.03)
        step += 1
except KeyboardInterrupt:
    print('\n手动结束.')
finally:
    dashboard.stop()
    try:
        env.close()
    except SystemExit:
        pass
