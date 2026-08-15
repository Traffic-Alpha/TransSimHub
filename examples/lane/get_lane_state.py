'''
@Author: WANG Maonan
@Date: 2026-08-11 10:00:00
@Description: 获得场景中所有车道的交通状态 (中观视图的数据来源)
- 每一步一次订阅交互拿到全路网车道的速度/占有率/排队;
- speed_relative (实际速度/限速) 就是拥堵指数, 越小越堵。
@LastEditTime: 2026-08-11 10:00:00
'''
import sumolib
from loguru import logger

from tshub.utils.get_abs_path import get_abs_path
from tshub.lane.lane_builder import LaneBuilder
from tshub.utils.init_log import set_logger

import traci
sumoBinary = sumolib.checkBinary('sumo')

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'), terminal_log_level='INFO')

sumocfg_file = path_convert("../sumo_env/three_junctions/env/3junctions.sumocfg")
traci.start([sumoBinary, "-c", sumocfg_file], label='0')
conn = traci.getConnection('0')

scene_lanes = LaneBuilder(sumo=conn)

step = 0
while conn.simulation.getMinExpectedNumber() > 0:
    data = scene_lanes.get_objects_infos()  # 获得所有车道的交通状态

    if step % 100 == 0:  # 每 100 步看一次最堵的 5 条车道
        most_congested = sorted(data.items(), key=lambda kv: kv[1]['speed_relative'])[:5]
        logger.info(f'SIM: === Step {step}, 最堵的 5 条车道 ===')
        for lane_id, lane_state in most_congested:
            logger.info(
                f"SIM: {lane_id:20s} 拥堵指数={lane_state['speed_relative']:.2f} "
                f"车辆数={lane_state['vehicle_count']:3d} "
                f"停车数={lane_state['halting_number']:3d} "
                f"占有率={lane_state['occupancy']:.2f}"
            )

    conn.simulationStep()
    step += 1

conn.close()
