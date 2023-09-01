'''
@Author: WANG Maonan
@Date: 2023-08-31 19:32:36
@Description: 
@LastEditTime: 2023-08-31 19:35:55
'''
import sumolib
from loguru import logger
from typing import Dict

def get_in_outgoing(net: sumolib.net.Net, edge_id: str) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    获取某个 edge 的 in 和 out 的 lane 的信息，返回的格式如下:
    {
        'In': {
            '161701303#10': [
                {'fromLane': 'gsndj_n7_0', 'toLane': '161701303#10_0', 'direction': 'r'},
                {'fromLane': 'gsndj_n7_1', 'toLane': '161701303#10_1', 'direction': 'r'}
            ],
            'gsndj_n6': [
                {'fromLane': 'gsndj_n7_1', 'toLane': 'gsndj_n6_1', 'direction': 's'},
                {'fromLane': 'gsndj_n7_2', 'toLane': 'gsndj_n6_2', 'direction': 's'}
            ],
            '29257863#5': [
                {'fromLane': 'gsndj_n7_3', 'toLane': '29257863#5_2', 'direction': 'l'}
            ]
        },
        'Out': {
            ...
        }
    }

    Args:
        net (sumolib.net.Net): 路网对象
        edge_id (str): 查询的 edge_id
    """
    inout_info = {'In': {}, 'Out': {}}

    # 解析Incoming的edge和信息
    for incoming_edge_info, connection_infos in net.getEdge(edge_id).getIncoming().items():
        incoming_edge_id = incoming_edge_info.getID()  # 获得Incoming Edge ID
        logger.debug(f'SIM: {incoming_edge_id}-->{edge_id}')
        inout_info['In'][incoming_edge_id] = []
        for connection_info in connection_infos:
            _info = {
                'fromLane': connection_info._fromLane.getID(),
                'toLane': connection_info._toLane.getID(),
                'direction': connection_info._direction
            }
            inout_info['In'][incoming_edge_id].append(_info)

    # 解析Outgoing的edge的信息
    for outgoing_edge_info, connection_infos in net.getEdge(edge_id).getOutgoing().items():
        outgoing_edge_id = outgoing_edge_info.getID()
        logger.debug(f'SIM: {edge_id}-->{outgoing_edge_id}')
        inout_info['Out'][outgoing_edge_id] = []
        for connection_info in connection_infos:
            _info = {
                'fromLane': connection_info._fromLane.getID(),
                'toLane': connection_info._toLane.getID(),
                'direction': connection_info._direction
            }
            inout_info['Out'][outgoing_edge_id].append(_info)

    return inout_info
