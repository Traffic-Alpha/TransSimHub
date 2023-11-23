'''
@Author: WANG Maonan
@Date: 2023-11-23 20:18:12
@Description: 生成行人走路的路网, 分为下面的两个步骤:
1. 根据 walk_flow_per_minute 生成 personFlow, self.__create_person_flow
2. 使用 duarouter 将 personFlow 转换为 output_file (_person.rou.xml)
@LastEditTime: 2023-11-23 22:49:40
'''
import sumolib
import subprocess

from loguru import logger
from typing import Dict, List
from tempfile import TemporaryFile

DUAROUTER = sumolib.checkBinary('duarouter')

class GeneratePersonTrip(object):
    def __init__(self, 
                net_file:str,
                intervals:List[float], 
                walk_flow_per_minute:Dict[str, List[float]],
                seed:int=777,
                walkfactor:float=0.7,
                person_trip_file:str='_person.trip.xml',
                output_file:str='_person.rou.xml'
        ) -> None:
        """生成行人的 route 文件, 下面是一个生成的文件的例子:
            <routes>
                <person id="E1__-E3_0.39" depart="0.84">
                    <walk edges="E1 -E1 -E3"/>
                </person>
                <person id="E1__-E3_0.38" depart="7.95">
                    <walk edges="E1 -E1 -E3"/>
                </person>
                <person id="E1__-E3_0.37" depart="11.03">
                    <walk edges="E1 -E1 -E3"/>
                </person>
            </routes>

        Args:
            net_file (str): 路网文件, 使用 duarouter 需要输入路网 
            intervals (List[float]): 时间的间隔，每段时间的持续时间（分钟），例如两段时间，[20, 30]，表示第一段时间为 20 分钟，第二段时间为 30 分钟
            walk_flow_per_minute (Dict[str, List[float]]): 每分钟 fromEdge-toEdge 的行人数量
            seed (int, optional): 随机数种子. Defaults to 777.
            walkfactor (float, optional): pedestrian maximum speed during intermodal routing;. Defaults to 0.7.
            person_trip_file (str, optional): person trip 文件, 这是中间文件. Defaults to '_person.trip.xml'.
            output_file (str, optional): 最后输出的带有行人的路程文件. Defaults to '_person.rou.xml'.
        """
        self.net_file = net_file # 路网文件
        self.intervals = intervals # 时间间隔
        self.walk_flow_per_minute = walk_flow_per_minute # 每个阶段, 每个 fromEdge-toEdge 的人数
        self.person_trip_file = person_trip_file # person.trip.xml 文件, 临时文件
        self.output_file = output_file # 输出文件
        self.seed=seed # 随机数种子
        self.walkfactor = walkfactor
    
    def generate_person_route(self):
        self.__create_person_flow() # 步骤一, 根据 person flow 生成 trip 文件
        self.__trip_to_route() # 步骤二, 根据 trip 生成 route 文件

    def __trip_to_route(self):
        """将 trip 文件转换为 route 文件
        """
        temp_file = TemporaryFile()
        prog = subprocess.Popen([DUAROUTER, "-n", self.net_file,
                                "--route-files", self.person_trip_file, # 行人相关的参数
                                "--seed", str(self.seed),  # 随机数种子
                                "--persontrip.walkfactor", str(self.walkfactor),
                                "--randomize-flows",
                                "-o", self.output_file,
                                "--no-warnings"], 
                                stderr=temp_file,
                                shell=False)  # More details about DUAROUTER, https://sumo.dlr.de/docs/duarouter.html
        prog.wait()
        temp_file.seek(0)
        err = temp_file.read()
        if err == b'':
            logger.info('SIM: 生成 person route 文件成功.')
        else:
            logger.warning('{}'.format(err))
            raise Exception(f"person route 文件生成失败, 检查 person trip 文件, {self.person_trip_file}.")
    
    def __create_person_flow(self):
        """根据生成设定的 intervals 和 walk_flow_per_minute 生成 trip 文件. 例如:
            intervals: [2, 3, 4] # 分钟
            walk_flow_per_minute: {
                'E1__E2': [10, 20, 30], 
                'E1__-E3': [40, 50, 60]
            } # fromEdge1__toEdge1: 每分钟的行人
        最后会生成 person.trip.xml 文件, 文件例子如下:
            <routes>
                <personFlow id="E1__E2_0" begin="0" end="120" number="10">
                    <walk from="E1" to="E2"/>
                </personFlow>
                <personFlow id="E1__-E3_0" begin="0" end="120" number="40">
                    <walk from="E1" to="-E3"/>
                </personFlow>
                <personFlow id="E1__E2_1" begin="120" end="300" number="20">
                    <walk from="E1" to="E2"/>
                </personFlow>
                ...
            </routes>
        """
        person_flow_xml = sumolib.xml.create_document("routes")
          
        total_seconds = 0
        for i, interval in enumerate(self.intervals):
            begin_time = total_seconds
            end_time = begin_time + interval * 60  # Convert minutes to seconds
            total_seconds = end_time
            
            # Iterate over each walk flow
            for flow_id, numbers in self.walk_flow_per_minute.items():
                # Create a personFlow element for each walk flow
                pf = person_flow_xml.addChild("personFlow")
                pf.setAttribute("id", f"{flow_id}_{i}")
                pf.setAttribute("begin", str(begin_time))
                pf.setAttribute("end", str(end_time))
                pf.setAttribute("number", str(numbers[i]))
                
                # Split the flow_id to get 'from' and 'to' attributes
                from_edge, to_edge = flow_id.split('__')
                pf_walk = pf.addChild("walk")
                pf_walk.setAttribute("from", from_edge)
                pf_walk.setAttribute("to", to_edge.replace('to', ''))  # Remove 'to' prefix

        with open(self.person_trip_file, 'w') as person_flow_file:
            person_flow_file.write(person_flow_xml.toXML())
        logger.debug(f'SIM: Person Flow Trip File 生成成功, {self.person_trip_file}.')