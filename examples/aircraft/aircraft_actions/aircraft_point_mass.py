'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: Aircraft 点质量动力学 (point_mass) 示例

与运动学 (kinematic, 默认) 不同, point_mass 将动作给出的速度视为「目标速度」,
通过有界加速度逼近, 因此飞行器具有惯性, 转向与加减速更平滑。
在 aircraft_inits 中通过 `dynamics_type` / `dynamics_params` / `dt` 进行配置,
动作输入仍为 (speed, heading_index), 与其他动作类型完全一致。
@LastEditTime: 2026-06-01 00:00:00
'''
import traci
import sumolib
from loguru import logger
import numpy as np

from tshub.utils.get_abs_path import get_abs_path
from tshub.aircraft.aircraft_builder import AircraftBuilder
from tshub.utils.init_log import set_logger
from tshub.utils.format_dict import dict_to_str

sumoBinary = sumolib.checkBinary('sumo-gui')

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

sumocfg_file = path_convert("../../sumo_env/single_junction/env/single_junction.sumocfg")
traci.start([sumoBinary, "-c", sumocfg_file], label='0')
conn = traci.getConnection('0')

aircraft_inits = {
    'a1': {
        "aircraft_type": "drone",
        "action_type": "horizontal_movement",
        "position": (1500, 1110, 100), "speed": 0, "heading": (1, 0, 0), "communication_range": 200,
        "if_sumo_visualization": True, "img_file": None,
        # 点质量动力学: 含惯性 + 最大速度/加速度约束
        "dynamics_type": "point_mass",
        "dynamics_params": {"max_speed": 15.0, "max_accel": 3.0, "max_climb_rate": 2.0},
        "dt": 1.0, # 每次 control 对应的物理时间步长 (秒)
    },
    'a2': {
        "aircraft_type": "drone",
        "action_type": "horizontal_movement",
        "position": (1900, 800, 100), "speed": 0, "heading": (1, 0, 0), "communication_range": 200,
        "if_sumo_visualization": True, "img_file": None,
        # 默认 kinematic (无惯性), 用于对照
        "dynamics_type": "kinematic",
    }
}

scene_aircraft = AircraftBuilder(sumo=conn, aircraft_inits=aircraft_inits)
while conn.simulation.getMinExpectedNumber() > 0:
    conn.simulationStep()
    actions = {
        "a1": (15, np.random.randint(8)), # 目标速度 15, point_mass 会逐步逼近
        "a2": (15, np.random.randint(8)),
    }
    scene_aircraft.control_objects(actions)
    aircraft_state = scene_aircraft.get_objects_infos()
    logger.info(f'SIM: {dict_to_str(aircraft_state)}')

conn.close()
