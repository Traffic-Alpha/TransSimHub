'''
@Author: WANG Maonan
@Date: 2023-08-25 17:11:46
@Description: 基础 TLS 的信息
LastEditTime: 2025-07-16 19:18:12
'''
import sumolib
from abc import ABC, abstractmethod
from ...sumo_tools.sumo_infos.tls_connections import tls_connection

class BaseTLS(ABC):
    """
    This class represents a Traffic Signal of an intersection
    It is responsible for retrieving information and changing the traffic phase using Traci API
    """
    def __init__(self, ts_id, sumo) -> None:
        self.id = ts_id # 信号灯的 id
        self.sumo = sumo

        # 获得路口连接
        tls_info = tls_connection(self.sumo)
        self.tls_connections = tls_info._get_tls_connection(self.id, keep_connection=True) # 获得当前路口的连接

        # 初始化路口
        self.fromEdge_toEdge = self.generate_fromEdge_toEdge_dict()

        # 信号灯 movement 和 phase 的基本信息
        self.movement_ids = set()
        self.movement_directions = {}
        self.movement_lane_numbers = {}
        self.movement_lane_ids = {} # 每个 movement 包含的 lane ids
        self.phase2movements = {} # 记录每个 phase 由哪些 movement 组成

        self.lanes = list(dict.fromkeys(self.sumo.trafficlight.getControlledLanes(self.id)))  # Remove duplicates and keep order
        # getControlledLinks 返回的格式为 [('29257863#2_0', 'gsndj_n6_0', ':htddj_gsndj_0_0')]
        self.in_out_lanes = [
            (link[0][0], link[0][1]) 
            for link in self.sumo.trafficlight.getControlledLinks(self.id) if link
        ] # 获得所有的 in 和 out lanes
        self.in_lanes = [_lanes[0] for _lanes in self.in_out_lanes] # 获得所有进入的 lanes
        self.out_lanes = [_lanes[1] for _lanes in self.in_out_lanes] # 获得所有离开的 lane
        self.lanes_lenght = {lane: self.sumo.lane.getLength(lane) for lane in self.lanes}

        # 获得 road 相关信息 (edge info)
        self.in_roads = self.lanes_to_edges(self.in_lanes)
        self.out_roads = self.lanes_to_edges(self.out_lanes)
        self.roads_lanes = self.extract_from_lanes() # 每个 roads 包含的 lanes

        # 计算进入 road 的角度（可以用于将摄像头按这个角度布置）
        self.in_roads_heading = {_road_id:self.sumo.edge.getAngle(_road_id) for _road_id in self.in_roads}
        self.out_roads_heading = {_road_id:self.sumo.edge.getAngle(_road_id) for _road_id in self.out_roads}

        # 获得每一个 in road 的 stop line 的坐标
        self.in_road_stop_line = {_road_id:list() for _road_id in self.in_roads}
        for _lane_id in self.in_lanes:
            _road_name = self.sumo.lane.getEdgeID(_lane_id)
            _lane_end_position = self.sumo.lane.getShape(_lane_id)[-1] # 这个是 lane 出口中心的点
            self.in_road_stop_line[_road_name].append(_lane_end_position)

        self.program_id = self.sumo.trafficlight.getProgram(self.id) # 获得这个信号的当前的 program id

        # 初始化 traffic light
        self.collect_movements_infos()
        self.collect_controled_phase_movements()

    @abstractmethod
    def set_next_phases(self) -> None:
        """实现控制信号灯不同的动作
        """
        pass
    
    @property
    def sim_step(self):
        """Return current simulation second on SUMO
        """
        return self.sumo.simulation.getTime()

    def build_phases(self) -> None:
        """初始化信号灯的方案, 在中间添加黄灯状态, 下面是一个例子.
        输入为：
            {
                0: Phase(duration=27.0, state='rrrrrrGGGGrrrrrGGGr', minDur=27.0, maxDur=27.0, next=()),
                1: Phase(duration=6.0, state='rrrrrryyyyrrrrryyyr', minDur=6.0, maxDur=6.0, next=()), 
                2: Phase(duration=6.0, state='rrrrrrrrrrGrrrrrrrG', minDur=6.0, maxDur=6.0, next=()), 
                3: Phase(duration=6.0, state='rrrrrrrrrryrrrrrrry', minDur=6.0, maxDur=6.0, next=()), 
                4: Phase(duration=27.0, state='GGGGrrrrrrrGGGrrrrr', minDur=27.0, maxDur=27.0, next=()), 
                5: Phase(duration=6.0, state='yyyyrrrrrrryyyrrrrr', minDur=6.0, maxDur=6.0, next=()), 
                6: Phase(duration=6.0, state='rrrrGGrrrrrrrrGrrrr', minDur=6.0, maxDur=6.0, next=()), 
                7: Phase(duration=6.0, state='rrrryyrrrrrrrryrrrr', minDur=6.0, maxDur=6.0, next=()))
            }

        输出如下, 生成了所有绿灯转换之间的黄灯相位:
            self.all_phases = {
                0: Phase(duration=3600, state='rrrrrrGGGGrrrrrGGGr', minDur=-1, maxDur=-1, next=()), 
                1: Phase(duration=3600, state='rrrrrrrrrrGrrrrrrrG', minDur=-1, maxDur=-1, next=()), 
                2: Phase(duration=3600, state='GGGGrrrrrrrGGGrrrrr', minDur=-1, maxDur=-1, next=()), 
                3: Phase(duration=3600, state='rrrrGGrrrrrrrrGrrrr', minDur=-1, maxDur=-1, next=()), 
                4: Phase(duration=3, state='rrrrrryyyyrrrrryyyr', minDur=-1, maxDur=-1, next=()), 
                5: Phase(duration=3, state='rrrrrryyyyrrrrryyyr', minDur=-1, maxDur=-1, next=()), 
                6: Phase(duration=3, state='rrrrrryyyyrrrrryyyr', minDur=-1, maxDur=-1, next=()), 
                7: Phase(duration=3, state='rrrrrrrrrryrrrrrrry', minDur=-1, maxDur=-1, next=()), 
                8: Phase(duration=3, state='rrrrrrrrrryrrrrrrry', minDur=-1, maxDur=-1, next=()), 
                9: Phase(duration=3, state='rrrrrrrrrryrrrrrrry', minDur=-1, maxDur=-1, next=()), 
                10: Phase(duration=3, state='yyyyrrrrrrryyyrrrrr', minDur=-1, maxDur=-1, next=()), 
                11: Phase(duration=3, state='yyyyrrrrrrryyyrrrrr', minDur=-1, maxDur=-1, next=()), 
                12: Phase(duration=3, state='yyyyrrrrrrryyyrrrrr', minDur=-1, maxDur=-1, next=()), 
                13: Phase(duration=3, state='rrrryyrrrrrrrryrrrr', minDur=-1, maxDur=-1, next=()),
                14: Phase(duration=3, state='rrrryyrrrrrrrryrrrr', minDur=-1, maxDur=-1, next=()),
                15: Phase(duration=3, state='rrrryyrrrrrrrryrrrr', minDur=-1, maxDur=-1, next=())
            }
            同时会输出 p_i -> p_j 对应的黄灯相位
            self.yellow_dict = {
                (0, 1): 4, (0, 2): 5, (0, 3): 6, (1, 0): 7, 
                (1, 2): 8, (1, 3): 9, (2, 0): 10, (2, 1): 11, 
                (2, 3): 12, (3, 0): 13, (3, 1): 14, (3, 2): 15
            }
        """
        phases = self.sumo.trafficlight.getAllProgramLogics(self.id)[0].phases

        self.green_phases = []
        self.yellow_dict = {} # 储存从 phase-i --> phase-j 需要的中间过渡相位的 phase_id
        for phase in phases:
            state = phase.state
            if 'G' in state: # 绿灯相位
                # 找到所有的绿灯相位, 并将持续时间修改为 1h
                self.green_phases.append(self.sumo.trafficlight.Phase(3600, state))

        self.num_green_phases = len(self.green_phases) # 绿灯相位的个数
        self.all_phases = self.green_phases.copy()

        # 从 A 相位 --> B 相位 中间需要添加的临时相位
        for i, p1 in enumerate(self.green_phases):
            for j, p2 in enumerate(self.green_phases):
                if i == j: continue
                yellow_state = ''
                for s in range(len(p1.state)):
                    if (p1.state[s] == 'G') and (p2.state[s] == 'r' or p2.state[s] == 's' or p2.state[s] == 'R'): # g -> r 需要增加 y
                        yellow_state += 'y'
                    else:
                        yellow_state += p1.state[s]
                self.yellow_dict[(i,j)] = len(self.all_phases) # 从 phase_1 -> phase_2 中间的过渡时间
                self.all_phases.append(self.sumo.trafficlight.Phase(self.yellow_time, yellow_state))

        programs = self.sumo.trafficlight.getAllProgramLogics(self.id)
        logic = programs[0]
        logic.type = 0
        logic.phases = self.all_phases
        self.sumo.trafficlight.setProgramLogic(self.id, logic) # 设置信号灯
    
    # #################
    # 信号灯信息（工具函数）
    # #################
    def get_green_durations(self):
        """获得信号灯的所有绿灯相位的时间长度, 只有 G 就是绿灯相位, 作为 obs 的一部分
        只有 g 不算是绿灯相位(右转可以一直是绿灯)

        Returns:
            (list): 一个信号灯的所有绿灯相位, 例如 [20, 20, 20, 20]
        """
        logics = self.sumo.trafficlight.getAllProgramLogics(self.id) # 获得当前信号灯的情况
        logic_index = [logic.programID for logic in logics].index(self.program_id)
        logic = logics[logic_index]
        
        green_durations = [phase.duration for phase in logic.phases if 'G' in phase.state] # 绿灯相位的时长
        return green_durations

    def get_complete_durations(self):
        """获得完整的信号灯时长 (包括红灯)

        Returns:
            (list): 一个信号灯的所有相位, 例如 [20, 3, 20, 3, 20, 3, 20]
        """
        logics = self.sumo.trafficlight.getAllProgramLogics(self.id) # 获得当前信号灯的情况
        logic_index = [logic.programID for logic in logics].index(self.program_id)
        logic = logics[logic_index]

        complete_durations = [phase.duration for phase in logic.phases] # 所有相位的时长
        return complete_durations
    
    def get_controled_phase(self):
        """返回每个相位是否可以被控制（是否包含 G）

        Returns:
            (dict): 返回每个相位是否可以被控制, 每个相位返回 True 或是 False
                {
                    0: True,
                    1: False,
                    2: True,
                    ...
                }
        """
        logics = self.sumo.trafficlight.getAllProgramLogics(self.id) # 获得当前信号灯的情况
        logic_index = [logic.programID for logic in logics].index(self.program_id) # 找到对应 program_id 的 logic
        logic = logics[logic_index]

        controled_phase = dict()
        for phase_index, phase in enumerate(logic.phases):
            controled_phase[phase_index] = (True if 'G' in phase.state else False)
        return controled_phase

    def collect_movements_infos(self):
        """统计 movmenet 的信息
        """
        for item in self.tls_connections:
            if None in item:
                continue
            from_edge, toEdge, from_lane, to_lane, _, direction, _ = item
            movement_id = f"{from_edge}--{direction}" # edge+direction 组成 movement id
            self.movement_ids.add(movement_id)
            self.movement_directions[movement_id] = direction # 记录 movement 的方向
            self.movement_lane_ids.setdefault(movement_id, []).append(from_lane) # 记录 movement 包含的 lane ids
        
        # lane ids 去重 & 统计 lane 的数量
        for movement_id, lane_ids in self.movement_lane_ids.items():
            self.movement_lane_ids[movement_id] = list(set(lane_ids))
            self.movement_lane_numbers[movement_id] = len(self.movement_lane_ids[movement_id]) # 记录 movement 的车道数

        self.movement_ids = sorted(self.movement_ids)

    def collect_controled_phase_movements(self):
        """得到每个 phase 由哪些 movement 组成, 返回的数据如下所示：

            {
                0: ['None__None', 'gsndj_s4__s', 'gsndj_n7__s', 'gsndj_n7__r', 'gsndj_s4__r'], 
                1: ['gsndj_s4__l', 'gsndj_n7__l'], 
                2: ['29257863#2__r', '161701303#7.248__r', '161701303#7.248__s', '29257863#2__s'], 
                3: ['29257863#2__l', '161701303#7.248__l']
            }

        其中包含 'None__None'（也就是 movement 为空）和「右转」，之后可以去除这些值。
        """
        logics = self.sumo.trafficlight.getAllProgramLogics(self.id) # 获得当前信号灯的情况
        logic_index = [logic.programID for logic in logics].index(self.program_id) # 找到对应 program_id 的 logic
        logic = logics[logic_index]

        phase_id = 0
        for phase in logic.phases: # 每个 phase 的组成, 例如 rrrrrrGGGGrrrrrGGGr
            _movement_list = list() # 每个 phase 由哪些 movement 组成
            if 'G' in phase.state: # 判断是否是绿灯相位
                for _conn_info, _phase_color in zip(self.tls_connections, phase.state):
                    if _phase_color == 'G':
                        fromEdge = _conn_info[0] # 获得 fronEdge
                        direction = _conn_info[5] # 获得 direction
                        _movement_list.append(f'{fromEdge}--{direction}')
                _filtered_movement_list = [item for item in _movement_list if item != 'None--None']
                self.phase2movements[phase_id] = list(set(_filtered_movement_list))
                phase_id += 1
    
    def generate_fromEdge_toEdge_dict(self):
        """这个函数将 tls connection 处理为方向对应出口的信息，输入的格式如下所示：
            [
                [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length], 
                ...
            ]
        最后输出的格式如下：
            {
                f"{fromEdge}--{direction}": [fromEdge, toEdge, fromLane, toLane]
            }
        """

        output_dict = {}  # Initialize an empty dictionary to store the output

        # Iterate over each inner list in the input list
        for inner_list in self.tls_connections:
            fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length = inner_list  # Unpack the inner list

            # Create a key using 'fromEdge' and 'direction'
            key = f"{fromEdge}--{direction}"

            # Create a value list using 'fromEdge', 'toEdge', 'fromLane', and 'toLane'
            value = [fromEdge, toEdge, fromLane, toLane]

            # Add the key-value pair to the output dictionary
            if key != 'None--None':
                output_dict[key] = value

        return output_dict
    
    def lanes_to_edges(self, lanes):
        """将车道 ID 转换为 Edge IDs, 需要进行去重

        Args:
            lanes (List[str]): 车道 ID 组成的 List
        """
        road_ids = set()
        for lane_id in lanes:
            _road_id = self.sumo.lane.getEdgeID(lane_id)
            road_ids.add(_road_id)
        return sorted(list(road_ids)) # 确保环境里面的 road_ids 顺序是一样的

    def extract_from_lanes(self):
        """根据下面的嵌套列表，提取出每个 edge 包含的 lane
        [
            [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length], 
            [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length],
            ...
        ]
        """
        # Step 1: Filter out any sublists containing None
        filtered_list = [item for item in self.tls_connections if None not in item]
        
        # Step 2: Initialize a dictionary to hold lanes for each edge
        edge_lanes = {}
        
        # Step 3: Process each item in the filtered list
        for item in filtered_list:
            from_edge, to_edge, from_lane, to_lane = item[0], item[1], item[2], item[3]
            
            # Add fromLane to fromEdge
            if from_edge not in edge_lanes:
                edge_lanes[from_edge] = set()
            edge_lanes[from_edge].add(from_lane)
            
            # Add toLane to toEdge
            if to_edge not in edge_lanes:
                edge_lanes[to_edge] = set()
            edge_lanes[to_edge].add(to_lane)
        
        # Step 4: Convert sets to sorted lists
        result = {edge: sorted(lanes) for edge, lanes in edge_lanes.items()}
        
        return result