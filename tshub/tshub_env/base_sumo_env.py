'''
@Author: WANG Maonan
@Date: 2023-08-23 15:30:01
@Description: Base tshub Environment
@LastEditTime: 2024-05-07 15:01:38
'''
import sumolib
from typing import List
from loguru import logger

from abc import ABC, abstractmethod

class BaseSumoEnvironment(ABC):
    """
    Base SUMO Environment for Traffic Signal Control

    :param net_file: (str) SUMO .net.xml file
    :param route_file: (str) SUMO .rou.xml file
    :param out_csv_name: (str) name of the .csv output with simulation results. If None no output is generated
    :param use_gui: (bool) Wheter to run SUMO simulation with GUI visualisation
    :param begin_time: (int) The time step (in seconds) the simulation starts
    :param num_seconds: (int) Number of simulated seconds on SUMO. The time in seconds the simulation must end.
    :param max_depart_delay: (int) Vehicles are discarded if they could not be inserted after max_depart_delay seconds
    :param delta_time: (int) Simulation seconds between actions
    :param min_green: (int) Minimum green time in a phase
    :param max_green: (int) Max green time in a phase
    :single_agent: (bool) If true, it behaves like a regular gym.Env. Else, it behaves like a MultiagentEnv (https://github.com/ray-project/ray/blob/master/python/ray/rllib/env/multi_agent_env.py)
    :sumo_seed: (int/string) Random seed for sumo. If 'random' it uses a randomly chosen seed.
    :fixed_ts: (bool) If true, it will follow the phase configuration in the route_file and ignore the actions. 不调整信号灯

    继承 BaseSumoEnvironment 之后需要重写的:
    - reset, 初始化 feature 和 agent
    - computer_observations_rewards, 重写计算特征
    """
    CONNECTION_LABEL = 1  # For traci multi-client support
    
    def __init__(self, 
                sumo_cfg:str, # sumo config 文件
                net_file:str=None, # sumo network 文件
                route_file:str=None, # sumo route 文件
                trip_info:str=None, # 是否输出 trip_info, 这里为 trip_info 的路径
                statistic_output:str=None, # 输出整个仿真过程的统计信息
                summary:str=None, # 记录每一秒的状态, 这里为文件输出的位置, https://sumo.dlr.de/docs/Simulation/Output/Summary.html, halting 与车辆是否到达终点无关
                queue_output:str=None, # 记录每一秒, 每一个车道的排队长度, 这里为输出文件位置, https://sumo.dlr.de/docs/Simulation/Output/QueueOutput.html
                tls_state_add:List[str]=None, # 是否记录 traffic light
                use_gui:bool=False, # 使用 sumo-gui 或是 sumo
                is_libsumo:bool=False, # 是否使用 libsumo
                begin_time=0, 
                num_seconds=20000, # 最多仿真的时间
                max_depart_delay=100000, 
                time_to_teleport=-1, 
                sumo_seed:str='random', 
                tripinfo_output_unfinished:bool=True,
                collision_action:str=None, # 发生碰撞后的变化 # https://sumo.dlr.de/docs/Simulation/Safety.html
                remote_port:int=None, # 设置端口, 使用 libsumo 不要开启这个
                num_clients:int=1
        ) -> None:
        # sumo basic config file
        self._sumo_cfg = sumo_cfg # sumo 配置文件
        self._net = net_file # net 文件
        self._route = route_file # route 文件

        # sumo additional output
        self.trip_info = trip_info # 输出 trip_info 文件（当堵车的时候会存在问题, 必须车辆达到终点才会别统计）
        self.statistic_output = statistic_output # 记录总体的信息
        self.summary = summary # 记录每一秒的综合信息
        self.queue_output = queue_output # 记录每一个车道的排队长度
        self.tls_state_add = tls_state_add # 记录信号灯信息

        # 多个 traci 连接
        self.remote_port = remote_port # 指定端口
        self.num_clients = num_clients # 连接的数量

        self.use_gui = use_gui # 使用 sumo-gui/sumo
        if self.use_gui:
            self._sumo_binary = sumolib.checkBinary('sumo-gui')
        else:
            self._sumo_binary = sumolib.checkBinary('sumo')

        self.is_libsumo = is_libsumo # 是否使用 libsumo
        if self.is_libsumo:
            self.traci = __import__('libsumo')
        else:
            self.traci = __import__('traci')
        
        assert collision_action in ["teleport", "warn", "none", "remove", None], \
            f"collision_action should be in [teleport, warn, none, remove]. Now is {collision_action}."
        
        self.collision_action = collision_action
        self.begin_time = begin_time
        self.sim_max_time = num_seconds # 最多的仿真时间
        self.max_depart_delay = max_depart_delay  # Max wait time to insert a vehicle
        self.time_to_teleport = time_to_teleport
        self.sumo_seed = sumo_seed # 设置 sumo 的随机数种子
        self.tripinfo_output_unfinished = tripinfo_output_unfinished # 车辆不达到终点也可以写入 tripinfo
        self.sumo = None # self.sumo=traic

        self.label = str(BaseSumoEnvironment.CONNECTION_LABEL)
        BaseSumoEnvironment.CONNECTION_LABEL += 1 # 多次初始化 label 是不同的
        logger.info(f'SIM: Env Label, {self.label}.')
    
    def _start_simulation(self):
        """开始仿真, 有四种情况来开启仿真
        1. 只指定 sumocfg 文件
        2. 指定 sumocfg 和 route 文件, (新的 route 可以覆盖 sumocfg 的设置)
        3. 制定 sumocfg 和 net 文件, (新的 net 可以覆盖 sumocfg 的设置)
        4. 直接指定 net 和 route, 不使用 sumocfg
        """
        if (self._net == None) and (self._route == None):
            # 使用 sumocfg 来启动 (没有指定 route 和 net)
            logger.info('SIM: 使用 sumocfg 来启动 (没有指定 route 和 net)')
            sumo_cmd = [self._sumo_binary,
                        '-c', self._sumo_cfg,
                        '--no-step-log', 'true',
                        '--no-warnings', 'true',
                        '--max-depart-delay', str(self.max_depart_delay), 
                        '--waiting-time-memory', '10000',
                        '--time-to-teleport', str(self.time_to_teleport)]
        elif (self._net == None) and (self._route != None): # 指定了 route 文件
            logger.info(f'SIM: 指定了 route 文件, {self._route}')
            sumo_cmd = [self._sumo_binary,
                        '-c', self._sumo_cfg,
                        '-r', self._route,
                        '--no-step-log', 'true',
                        '--no-warnings', 'true',
                        '--max-depart-delay', str(self.max_depart_delay), 
                        '--waiting-time-memory', '10000',
                        '--time-to-teleport', str(self.time_to_teleport)] 
        elif (self._net != None) and (self._route == None): # 指定了 net 文件
            logger.info(f'SIM: 指定了 net 文件, {self._net}')
            sumo_cmd = [self._sumo_binary,
                        '-c', self._sumo_cfg,
                        '-n', self._net,
                        '--no-step-log', 'true',
                        '--no-warnings', 'true',
                        '--max-depart-delay', str(self.max_depart_delay), 
                        '--waiting-time-memory', '10000',
                        '--time-to-teleport', str(self.time_to_teleport)]            
        else: # 同时指定了 network 和 route
            logger.info(f'SIM: 同时指定了 {self._net} 和 {self._route} 文件')
            sumo_cmd = [self._sumo_binary,
                        '-c', self._sumo_cfg,
                        '-n', self._net,
                        '-r', self._route,
                        '--no-step-log', 'true',
                        '--no-warnings', 'true',
                        '--max-depart-delay', str(self.max_depart_delay), 
                        '--waiting-time-memory', '10000',
                        '--time-to-teleport', str(self.time_to_teleport)]
                     
        if self.begin_time > 0: # 设置开始时间
            sumo_cmd.append('-b {}'.format(self.begin_time))
        if self.sumo_seed == 'random': # 随机数种子
            sumo_cmd.append('--random')
        if self.tripinfo_output_unfinished:
            sumo_cmd.append('--tripinfo-output.write-unfinished')
        else:
            sumo_cmd.extend(['--seed', str(self.sumo_seed)])

        
        if self.num_clients > 1: # 设置 num clients
            logger.debug(f'SIM: Set Num Clients {self.num_clients}.')
            sumo_cmd.extend(['--num-clients', str(self.num_clients)])    

        if self.use_gui: # 是否使用 gui, start->直接开始仿真; quit-on-end->仿真结束关闭 GUI
            sumo_cmd.extend(['--start', '--quit-on-end'])

        if self.collision_action is not None:
            sumo_cmd.extend(['--collision.action', self.collision_action])
        if self.trip_info is not None: # 使得输出 trip_info
            sumo_cmd.extend(['--device.emissions.probability', '1.0']) # 输出 emission
            sumo_cmd.extend(['--tripinfo-output', self.trip_info])
        if self.statistic_output is not None: # 使得输出 statistic_output
            sumo_cmd.extend(['--statistic-output', self.statistic_output])
        if self.summary is not None: # 使其输出 summary
            sumo_cmd.extend(['--summary', self.summary])
        if self.queue_output is not None: # 输出每个车道的排队长度
            sumo_cmd.extend(['--queue-output', self.queue_output])
        if self.tls_state_add is not None: # !, 注意, 需要额外去指定探测器, 不然会没有探测器
            assert isinstance(self.tls_state_add, list), '指定需要的 tls add 文件'
            sumo_cmd.extend(['-a', ','.join(self.tls_state_add)])
        if self.is_libsumo: # 使用 libsumo, 需要在不同 process 才可以多开
            self.traci.start(sumo_cmd)
            self.sumo = self.traci
        else: # 使用 traci
            if self.remote_port is None: # 指定端口
                logger.debug('SIM: Not Set Port.')
                self.traci.start(sumo_cmd, label=self.label)
            else:
                logger.debug(f'SIM: Set Port {self.remote_port}.')
                self.traci.start(sumo_cmd, label=self.label, port=self.remote_port)
                
            self.sumo = self.traci.getConnection(self.label)
            if self.num_clients > 1:
                self.sumo.setOrder(1) # 这里设置为 1

        logger.info(f'SIM: Start Env Label, {self.label}.')

    def _close_simulation(self) -> None:
        """关闭仿真
        """
        if self.sumo is None: # 第一次 reset 就会从这里走
            logger.info(f'SIM: Close Env Label (Reset Mode), {self.label}.')
            return
        if not self.is_libsumo:
            self.traci.switch(self.label)
        self.traci.close()
        self.sumo = None # 关闭仿真之后 self.sumo 设置为 None
        logger.info(f'SIM: Close Env Label, {self.label}.')

    def __del__(self) -> None:
        self._close_simulation()
    
    def _computer_done(self):
        done = self.sim_step > self.sim_max_time
        return done
    
    @property
    def sim_step(self):
        """Return current simulation second on SUMO
        """
        return self.sumo.simulation.getTime()

    @abstractmethod
    def reset(self) -> None:
        """重置环境, 返回初始的 obs, 需要完成 feature 部分的初始化
        """
        pass
    
    @abstractmethod
    def step(self) -> None:
        pass
    
    def render(self, mode=None) -> None:
        raise NotImplementedError
