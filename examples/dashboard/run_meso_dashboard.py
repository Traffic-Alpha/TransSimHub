'''
@Author: WANG Maonan
@Date: 2026-08-11 10:00:00
@Description: 实时中观交通大屏 —— 跑仿真的同时在浏览器里看全网拥堵的形成与消散
运行后打开终端里打印的地址 (默认 http://127.0.0.1:8910)。

大屏与环境是解耦的: DashboardServer 只吃 obs 里的数据, 不反向依赖 env,
所以任何拿得到 lane_shape / edge_state 的循环都可以推给它。
@LastEditTime: 2026-08-11 10:00:00
'''
import time
from loguru import logger

from tshub.visualization.meso import DashboardServer, build_static_payload, build_frame_payload
from tshub.tshub_env.tshub_env import TshubEnvironment
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'), terminal_log_level='WARNING')  # 大屏在前台, 日志调静一些

# 用 kowloon 场景: 它带完整的 poly 文件 (7000+ 个多边形, 建筑/公园/树林/水系俱全),
# 大屏才画得出 Google Maps 那样的底图。没有底图的话路网就是悬空的几根线,
# 看不出哪一处堵在市中心、哪一处堵在海边。
KOWLOON = "../sumo_env/kowloon_police_uav"
sumo_cfg = path_convert(f"{KOWLOON}/map.sumocfg")
net_file = path_convert(f"{KOWLOON}/map.net.xml")
poly_file = path_convert(f"{KOWLOON}/add/map.poly.xml")
# 早高峰需求 (梯形的插入率曲线, 由 peak_route.py 生成): 平的插入率只会让车辆一直堆积,
# 看不到「拥堵形成 -> 扩散 -> 消散」的过程, 而那正是中观视图要展示的东西
route_file = path_convert(f"{KOWLOON}/peak.rou.xml")

PUSH_EVERY = 5  # 每 5 个仿真步推一帧, 中观视图不需要每步都更新
STEP_DELAY = 0.05  # 放慢一点, 便于在浏览器里看清拥堵的演化

tshub_env = TshubEnvironment(
    sumo_cfg=sumo_cfg,
    net_file=net_file,
    route_file=route_file,
    poly_file=poly_file,  # 底图: 建筑 / 绿地 / 水系
    is_map_builder_initialized=True,  # 提供路网几何
    is_lane_builder_initialized=True,  # 车道级拥堵 (下钻)
    is_edge_builder_initialized=True,  # 路段级拥堵 (着色)
    is_vehicle_builder_initialized=False,
    is_aircraft_builder_initialized=False,
    is_traffic_light_builder_initialized=False,
    is_person_builder_initialized=False,
    # 4500s: peak.rou.xml 的需求曲线是 t<1200 基线 -> t≈2100~2700 峰值 -> t≈3900 回到基线,
    # 跑到 4500 才能完整看到拥堵的形成、饱和与消散
    use_gui=False, num_seconds=4500,
)

dashboard = DashboardServer(port=8910)
url = dashboard.start()
logger.warning(f'SIM: 中观大屏: {url}  (Ctrl-C 结束)')

obs = tshub_env.reset()
static_payload = build_static_payload(obs)
dashboard.set_static(static_payload)

step, done = 0, False
try:
    while not done:
        obs, _, infos, done = tshub_env.step(actions={})
        if step % PUSH_EVERY == 0:
            dashboard.push(build_frame_payload(
                sim_time=infos['step_time'],
                obs=obs,
                static_payload=static_payload,
            ))
            time.sleep(STEP_DELAY)
        step += 1
except KeyboardInterrupt:
    logger.warning('SIM: 手动结束.')
finally:
    dashboard.stop()
    tshub_env._close_simulation()
