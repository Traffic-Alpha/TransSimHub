'''
@Author: WANG Maonan
@Date: 2026-08-11 10:00:00
@Description: 获得场景中所有路段的交通状态 (中观视图的默认粒度)
- 路段级由 SUMO 自己聚合, 数量比车道少, 用来驱动路网着色;
- 需要更细的差异 (如左转道排队/直行道畅通) 时, 再用 lane_ids 下钻到 tshub.lane。
@LastEditTime: 2026-08-11 10:00:00
'''
import sumolib
from loguru import logger

from tshub.utils.get_abs_path import get_abs_path
from tshub.edge.edge_builder import EdgeBuilder
from tshub.utils.init_log import set_logger

import traci
sumoBinary = sumolib.checkBinary('sumo')

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'), terminal_log_level='INFO')

sumocfg_file = path_convert("../sumo_env/three_junctions/env/3junctions.sumocfg")
traci.start([sumoBinary, "-c", sumocfg_file], label='0')
conn = traci.getConnection('0')

scene_edges = EdgeBuilder(sumo=conn)

step = 0
while conn.simulation.getMinExpectedNumber() > 0:
    data = scene_edges.get_objects_infos()  # 获得所有路段的交通状态

    if step % 100 == 0:  # 每 100 步看一次最堵的 5 个路段
        most_congested = sorted(data.items(), key=lambda kv: kv[1]['speed_relative'])[:5]
        logger.info(f'SIM: === Step {step}, 最堵的 5 个路段 ===')
        for edge_id, edge_state in most_congested:
            logger.info(
                f"SIM: {edge_id:12s} 拥堵指数={edge_state['speed_relative']:.2f} "
                f"车辆数={edge_state['vehicle_count']:3d} "
                f"停车数={edge_state['halting_number']:3d} "
                f"车道={edge_state['lane_ids']}"
            )

    conn.simulationStep()
    step += 1

conn.close()
