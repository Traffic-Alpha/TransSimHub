'''
@Author: WANG Maonan
@Date: 2023-08-31 18:08:48
@Description: 生成 turndef 文件
@LastEditTime: 2023-08-31 20:14:38
'''
import os
import sumolib
import numpy as np
import xml.etree.ElementTree as ET
from typing import Dict, List
from loguru import logger
from collections import defaultdict

from ..sumo_infos.edge_info import get_in_outgoing
from ..sumo_infos.turndef.connections import from_stream
from ..sumo_infos.turndef.turndefinitions import from_connections, to_xml
from ...utils.check_folder import check_folder
from ...utils.nested_dict_conversion import defaultdict2dict
from ...utils.format_dict import dict_to_str

class GenerateTurnDef(object):
    def __init__(self,
                intervals:List,
                edge_turndef:Dict[str, List],
                sumo_net:str,
                output_file:str='testflow.turndefs.xml'
            ) -> None:
        """根据「开始结束时间」，「每个 connection 的概率」,「sumo 的网络」 生成 .turndefs.xml 文件
        下面是 .turndefs.xml 文件的样例:

            <turns>
                <interval begin="0" end="600">
                    <edgeRelation from="-171860080#0" to="wjj_n7" probability="100" />
                    <edgeRelation from="-171860080#2.50" to="-171860080#1" probability="75" />
                    <edgeRelation from="-171860080#2.50" to="-171860092" probability="25" />
                </interval>
                <interval begin="600" end="1800">
                    <edgeRelation from="-171860080#0" to="wjj_n7" probability="100" />
                    <edgeRelation from="-171860080#2.50" to="-171860080#1" probability="75" />
                    <edgeRelation from="-171860080#2.50" to="-171860092" probability="25" />
                </interval>
            </turns>

        Args:
            intervals (List): 时间的间隔，每段时间的持续时间（分钟），例如两段时间，[20, 30]，表示第一段时间为 20 分钟，第二段时间为 30 分钟
            edge_turndef (Dict[str, List]): 每一个 connection 每一个时间间隔的概率
            {
                'fromEdge1__toEdge1': [0.5, 0.5, 0.2],
                'fromEdge2__toEdge2': [0.2, 0.3, 0.4],
                'fromEdge3__toEdge3': [0.6, 0.1, 0.3],
                ...
            }
            sumo_net (str): sumo 路网文件路径
            output_file (str, optional): 最终输出的 .turndefs.xml 文件. Defaults to 'testflow.turndefs.xml'.
        """
        self.intervals = intervals # 时间间隔
        self.edge_turndef = edge_turndef # 需要修改的 edge 的 turndef
        self.sumo_net = sumo_net
        self.output_file = output_file

        self._expand_turn_definition() 
        folder_path, _ = os.path.split(self.output_file)
        check_folder(folder_path)

    def _expand_turn_definition(self) -> None:
        """对 self.edge_turndef 的值进行拓展. 
            => 在 self.edge_turndef 中包含了 fromEdge1__toEdge1 的概率.
            => 但是实际上 fromEdge1 会有好几个 output, 例如 fromEdge1__toEdge1, fromEdge1__toEdge2
            => 如果我们只设置了 fromEdge1__toEdge1=0.9, fromEdge1__toEdge2 也需要进行调整, 调整为 0.1.
            
            下面是实际的操作:
            -> 在 self.edge_turndef 中找出所有的 fromEdge, fromEdge_set
            -> 将 fromEdge_set 调整为如下的格式: 
                {
                    fromEdge1: {connection:None, connection:None}, 
                    fromEdge2: {connection:None, connection:None},
                    ...
                } 
                其中 connection 就是 fromEdge__toEdge, p 为概率, 初始均设置为 None, 结果保存在 fromEdge_connection
            -> 根据 self.edge_turndef 将上面的 None 改写为设置的概率:
                {
                    fromEdge1: {connection:[0.7, 0.2], connection:None}, 
                    fromEdge2: {connection:[0.4. 0.5], connection:[0.6,0.5]},
                    ...
                }
            -> 这个时候 fromEdge_connection 中有些 connection 有值, 有些没有.
                -> 如果全部有值, 则不变;
                -> 如果存在 None, 则是 mean(1-p)
            -> 将 fromEdge_connection 转换为 self.edge_turndef 的格式
        """
        logger.debug(f'SIM: edge_turndef 修改前:\n{dict_to_str(self.edge_turndef)}')
        net = sumolib.net.readNet(self.sumo_net) # 读取 sumo net
        fromEdge_set = set() # 所有出现的 fromEdge
        for _fromEdge_toEdge, _ in self.edge_turndef.items():
            fromEdge = _fromEdge_toEdge.split('__')[0]
            fromEdge_set.add(fromEdge)
        
        fromEdge_connections = defaultdict(dict) # 找到一个 edge 的所有 connection
        for _fromEdge in fromEdge_set:
            out_info = get_in_outgoing(net, _fromEdge)['Out']
            for _toEdge, _ in out_info.items():
                _connection = '{}__{}'.format(_fromEdge, _toEdge)
                fromEdge_connections[_fromEdge][_connection] = None # 初始为 None
        fromEdge_connections = defaultdict2dict(fromEdge_connections)
        
        for _fromEdge_toEdge, _probability_list in self.edge_turndef.items(): # 将 edge_turndef 出现的修改为列表
            fromEdge = _fromEdge_toEdge.split('__')[0]
            fromEdge_connections[fromEdge][_fromEdge_toEdge] = _probability_list

        for _fromEdge, _fromEdge_connection in fromEdge_connections.items(): # 处理一个 fromEdge
            _none_num = list(_fromEdge_connection.values()).count(None) # fromEdge 中所有的 connection None 出现的次数
            _total_probability = np.array([0.0]*len(self.intervals)) # fromEdge 所有转向概率和, [0.1, 0.2], [0.2, 0.3] -> [0.3, 0.5]
            for _, _probability in _fromEdge_connection.items():
                if _probability is not None:
                    _total_probability += np.array(_probability)
            for _connection, _probability in _fromEdge_connection.items():
                if _probability == None:
                    assert ((1 - _total_probability)>=0).all(), '检查 {} 的概率设置'.format(_fromEdge)
                    fromEdge_connections[_fromEdge][_connection] = (1 - _total_probability)/_none_num

        self.edge_turndef = dict()
        for _, _fromEdge_connection in fromEdge_connections.items():
            for _connection, _probability in _fromEdge_connection.items():
                self.edge_turndef[_connection] = _probability

        logger.debug(f'SIM: edge_turndef 修改后: \n{dict_to_str(self.edge_turndef)}')

    def generate_turn_definition(self):
        """初始化一个 testflow.turndefs.xml 文件, 包含所有 connection 的转弯概率
        """
        connections_file = open(self.sumo_net, "r") # 路网文件
        turn_definitions_file = open(self.output_file, "w") # 输出的 sumo turndef 文件

        connections = from_stream(connections_file)
        turn_definitions = from_connections(connections)
        turn_definitions_xml = to_xml(turn_definitions,
                                      str(0),
                                      str(36000))
        turn_definitions_file.write(turn_definitions_xml)

        connections_file.close()
        turn_definitions_file.close()

        logger.info('SIM: =>turn definition 生成成功.')

    def edit_turn_definition(self) -> None:
        """根据 edge_turndef, 对上面生成的 testflow.turndefs.xml 文件进行修改
        同时, 如果有多个时间段, 每个时间段的转弯概率都不同
        """
        loop = len(self.intervals) # 一共有多少个时间段

        # 修改 xml 文件
        tree = ET.parse(self.output_file)  # 处理 edge 与 edge 之间连通的概率
        final_turn_defination = '<turns>\n    '
        for loop_index in range(loop): # 将一段时间重复 N 次
            for child in tree.iter():  # 遍历整个 xml 文件
                if child.tag == 'interval':  # 修改开始和结束的时间
                    child.attrib['begin'] = str(60 * sum(self.intervals[:loop_index]))
                    child.attrib['end'] = str(60 * sum(self.intervals[:loop_index + 1]))
                if child.tag == 'edgeRelation':  # 修改转弯的概率
                    from_edge = child.attrib['from'] # .turndefs.xml 中一行的 fromEdge
                    to_edge = child.attrib['to'] # .turndefs.xml 中一行的 toEdge
                    replace_index = '{}__{}'.format(from_edge, to_edge)
                    if replace_index in self.edge_turndef: # 
                        child.attrib['probability'] = str(
                            self.edge_turndef[replace_index][loop_index] * 100) # 新的概率
            final_turn_defination = final_turn_defination + \
                ET.tostring(tree.getroot().find('interval'),
                            encoding='unicode') + '    '
        final_turn_defination = final_turn_defination.strip() + '\n</turns>'
        with open(self.output_file, 'w') as f:
            f.write(final_turn_defination)

        logger.info('SIM: =>turn definition 修改成功.')