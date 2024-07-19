'''
@Author: WANG Maonan
@Date: 2023-08-24 17:07:29
@Description: 通过 SUMO 获得信号灯控制的路口
@LastEditTime: 2024-07-19 18:49:14
'''
from typing import List

class tls_connection(object):
    """获得路口(有信号灯控制的)的所有连接, 可以得到如下的形式:
    {
        'tlsID_1':[
            [fromEdge, toEdge, fromLane, toLane, direction, fromLane_length],
            [fromEdge, toEdge, fromLane, toLane, direction, fromLane_length],
            ...
        ],
        'tlsID_2':[
            [fromEdge, toEdge, fromLane, toLane, direction, fromLane_length],
            [fromEdge, toEdge, fromLane, toLane, direction, fromLane_length],
            ...
        ],
        ...
    }
    """

    def __init__(self, sumo):
        """
        Args:
            sumo: 与仿真相连
        """
        self.sumo = sumo

    def _get_lane_direction(self, tls_id):
        """获得 laneA-laneB 的方向, 输出的结果为:
        {
            fromLaneID1_toLaneID1: driection, 
            fromLaneID2_toLaneID2: driection, 
            ...
        }
        """
        lane2lane_direction = {}  # {fromLaneID_toLaneID:driection}
        # 一个 tls 周围所有的 lane
        for laneID in self.sumo.trafficlight.getControlledLanes(tls_id):
            # 从这个lane出发, 可以达到的lane
            for lanelink in self.sumo.lane.getLinks(laneID):
                fromLaneID_toLaneID = '{}_{}'.format(laneID, lanelink[0])
                if fromLaneID_toLaneID not in lane2lane_direction:
                    # direction
                    lane2lane_direction[fromLaneID_toLaneID] = lanelink[-2]
        return lane2lane_direction

    def _get_tls_connection(self, tls_id, keep_connection:bool=False):
        """获得一个 tls 下所有 lane 连接的信息, 返回的结果为:
        [
            [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length], 
            [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length],
            ...
        ]
        这里信息是最全的, 后面的都是基于这个数据结构进行生成.
        Note: 这里 direction 只会有一个方向, 但是由于道路有多功能车道, 所以会出现 rs 这样的 diraction, 因此需要进行拆分

        keep_connection (bool): 是否保留 getControlledLinks 中的空值，从而提取的 connection 可以与 phase.state 的字母对应上
        """
        lane2lane_direction = self._get_lane_direction(tls_id)  # 只是为了获取 direction
        # 把一个 connection 扩展为, {fromEdge, toEdge, fromLane, toLane, direction}
        connection_list = []
        # 获得所有的 connection, 这个顺序和信号灯 state 的顺序是一样的
        for connection in self.sumo.trafficlight.getControlledLinks(tls_id): # [fromLane, toLane, internalLane]
            if connection: # connection 不为空
                fromEdge = self.sumo.lane.getEdgeID(connection[0][0]) # lane -> edge
                toEdge = self.sumo.lane.getEdgeID(connection[0][1])
                fromLane = connection[0][0]
                toLane = connection[0][1]
                viaLane = connection[0][2] # internal lane
                direction = lane2lane_direction['{}_{}'.format(fromLane, toLane)]
                fromLane_length = self.sumo.lane.getLength(fromLane) # fromLane 的长度
                allowed = self.sumo.lane.getAllowed(fromLane)
                condition = ('pedestrian' not in allowed) or ('passenger' in allowed)
                if condition: # 我们不考虑人行道
                    connection_list.append(
                        [fromEdge, toEdge, fromLane, toLane, viaLane, direction, fromLane_length])
            elif keep_connection:
                connection_list.append([None, None, None, None, None, None, None])
                
        return connection_list
    
    def get_tls_connections(self, tls_list:List):
        """获得多个信号灯的 connection

        Args:
            tls_list (List): 信号灯 id, 例如 ['0', '1', '2']

        Returns:
            Dict[List]: 返回每个 tls lane 的情况, 样例数据如下所示:

        {
            'tlsID_1':[
                [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length],
                [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length],
                ...
            ],
            'tlsID_2':[
                [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length],
                [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length],
                ...
            ],
            ...
        }
        """
        tls_connections = {}
        for tls_id in tls_list:
            tls_connections[tls_id] = self._get_tls_connection(tls_id)
        return tls_connections