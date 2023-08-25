'''
@Author: WANG Maonan
@Date: 2023-08-25 17:11:46
@Description: 基础 TLS 的信息
@LastEditTime: 2023-08-25 20:01:55
'''
from abc import ABC, abstractmethod
from ...sumo_tools.sumo_infos.tls_connections import tls_connection

class BaseTLS(ABC):
    """
    This class represents a Traffic Signal of an intersection
    It is responsible for retrieving information and changing the traffic phase using Traci API
    """
    def __init__(self, ts_id, sumo):
        self.id = ts_id # 信号灯的 id
        self.sumo = sumo

        self.lanes = list(dict.fromkeys(self.sumo.trafficlight.getControlledLanes(self.id)))  # Remove duplicates and keep order
        self.out_lanes = [link[0][1] for link in self.sumo.trafficlight.getControlledLinks(self.id) if link]
        self.out_lanes = list(set(self.out_lanes))
        self.lanes_lenght = {lane: self.sumo.lane.getLength(lane) for lane in self.lanes}

        self.program_id = self.sumo.trafficlight.getProgram(self.id) # 获得这个信号的当前的 program id

    @abstractmethod
    def set_next_phases(self):
        """实现控制信号灯不同的动作
        """
        pass


    def build_phases(self):
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
    
    # ##########
    # 信号灯信息
    # ##########
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

    def get_movements_infos(self):
        # movement 的 id, 且经过排序
        logics = self.sumo.trafficlight.getAllProgramLogics(self.id) # 获得当前信号灯的情况
        logic_index = [logic.programID for logic in logics].index(self.program_id) # 找到对应 program_id 的 logic
        logic = logics[logic_index]

        tls_info = tls_connection(self.sumo)
        tls_connections = tls_info._get_tls_connection(self.id, keep_connection=True) # 获得当前路口的连接
        print(1)
        return (1,1,1)

    def controled_phase_movements(self):
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

        tls_info = tls_connection(self.sumo)
        tls_connections = tls_info._get_tls_connection(self.id, keep_connection=True) # 获得当前路口的连接

        phase2movements = dict() # 记录每个 phase 由哪些 movement 组成
        phase_id = 0
        for phase in logic.phases: # 每个 phase 的组成, 例如 rrrrrrGGGGrrrrrGGGr
            _movement_list = list() # 每个 phase 由哪些 movement 组成
            if 'G' in phase.state: # 判断是否是绿灯相位
                for _conn_info, _phase_color in zip(tls_connections, phase.state):
                    if _phase_color == 'G':
                        fromEdge = _conn_info[0] # 获得 fronEdge
                        direction = _conn_info[5] # 获得 direction
                        _movement_list.append(f'{fromEdge}--{direction}')
            
                phase2movements[phase_id] = list(set(_movement_list))
                phase_id += 1

        return phase2movements