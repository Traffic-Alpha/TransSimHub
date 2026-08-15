'''
@Author: WANG Maonan
@Date: 2026-08-11 10:00:00
@Description: 中观视图的数据链路: 在 TshubEnvironment 里同时打开 lane/edge builder
- obs['lane_shape'] : 车道的静态几何 (来自 map builder), 用来画路网;
- obs['edge_state'] : 路段的动态交通状态, 用来给路网着色 (中观视图的默认粒度);
- obs['lane_state'] : 车道的动态交通状态, 点开某个路段时下钻用。
三者用 lane_id / edge_id 关联。
@LastEditTime: 2026-08-11 10:00:00
'''
from loguru import logger

from tshub.tshub_env.tshub_env import TshubEnvironment
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'), terminal_log_level='INFO')

sumo_cfg = path_convert("../sumo_env/three_junctions/env/3junctions.sumocfg")
net_file = path_convert("../sumo_env/three_junctions/env/3junctions.net.xml")

tshub_env = TshubEnvironment(
    sumo_cfg=sumo_cfg,
    net_file=net_file,  # map builder 需要 net 文件来解析几何
    is_map_builder_initialized=True,  # 提供 obs['lane_shape'] (静态几何)
    is_vehicle_builder_initialized=False,  # 中观视图不需要逐车信息
    is_aircraft_builder_initialized=False,
    is_traffic_light_builder_initialized=False,
    is_person_builder_initialized=False,
    is_lane_builder_initialized=True,  # 提供 obs['lane_state'] (车道级动态状态)
    is_edge_builder_initialized=True,  # 提供 obs['edge_state'] (路段级动态状态)
    use_gui=False, num_seconds=600,
)

obs = tshub_env.reset()
logger.info(f"SIM: obs 的 key: {sorted(obs.keys())}")
logger.info(
    f"SIM: 静态几何 {len(obs['lane_shape'])} 条车道, "
    f"动态状态 {len(obs['lane_state'])} 条车道 / {len(obs['edge_state'])} 个路段."
)

step = 0
done = False
while not done:
    obs, _, _, done = tshub_env.step(actions={})

    if step % 100 == 0:
        edge_state = obs['edge_state']
        # 全网平均拥堵指数 + 最堵的 3 个路段
        mean_congestion = sum(e['speed_relative'] for e in edge_state.values()) / len(edge_state)
        worst = sorted(edge_state.items(), key=lambda kv: kv[1]['speed_relative'])[:3]
        logger.info(f'SIM: === Step {step}, 全网平均拥堵指数 {mean_congestion:.2f} ===')
        for edge_id, state in worst:
            # 从最堵的路段下钻到它的车道, 看车道之间的差异
            lane_detail = ' | '.join(
                f"{lane_id}:{obs['lane_state'][lane_id]['speed_relative']:.2f}"
                for lane_id in state['lane_ids']
            )
            logger.info(f"SIM: {edge_id:10s} {state['speed_relative']:.2f}  下钻车道 -> {lane_detail}")
    step += 1

tshub_env._close_simulation()
