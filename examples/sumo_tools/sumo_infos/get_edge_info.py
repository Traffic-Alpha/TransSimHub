'''
@Author: WANG Maonan
@Date: 2023-08-31 19:34:43
@Description: 获得 edge in 和 out 的信息
@LastEditTime: 2023-08-31 19:39:51
'''
import sumolib
from loguru import logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.format_dict import dict_to_str
from tshub.sumo_tools.sumo_infos.edge_info import get_in_outgoing

current_file_path = get_abs_path(__file__)

sumo_net = current_file_path("../../sumo_env/three_junctions/env/3junctions.net.xml")
net = sumolib.net.readNet(sumo_net) # 读取 sumo net

edge_info = get_in_outgoing(net=net, edge_id='-E9')
logger.info(f'SIM: \n{dict_to_str(edge_info)}.')