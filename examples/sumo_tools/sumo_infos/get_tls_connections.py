'''
@Author: WANG Maonan
@Date: 2023-08-24 17:16:06
@Description: 获得多个路口, 每一个路口的所有的 connection
@LastEditTime: 2023-08-24 17:36:33
'''
from loguru import logger
import libsumo as traci
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.format_dict import dict_to_str
from tshub.sumo_tools.sumo_infos.tls_connections import tls_connection

current_file_path = get_abs_path(__file__)

# 开启环境
traci.start(["sumo", "-c", current_file_path("../../sumo_env/three_junctions/env/3junctions.sumocfg")])
conn = traci

# 打印对应 traffic junction 的 id 的信息
junctions = ['J1','J2','J3']
junctions_info = tls_connection(conn)
results = junctions_info.get_tls_connections(junctions)
json_str = dict_to_str(results) # dict -> str
logger.info(json_str)