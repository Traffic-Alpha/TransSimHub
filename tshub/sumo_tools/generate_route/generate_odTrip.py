'''
Author: Maonan Wang
Date: 2024-09-16 12:15:38
LastEditTime: 2025-04-21 18:47:43
LastEditors: Maonan Wang
Description: 生成符合 OD Matrix 的 trip 文件
FilePath: /TransSimHub/tshub/sumo_tools/generate_route/generate_odTrip.py
'''
import os
import random
import sumolib
from typing import Dict, List, Tuple
from xml.dom import pulldom
from loguru import logger

from ...utils.check_folder import check_folder
from ...utils.normalization_dict import normalize_dict

class GenerateODTrip(object):
    def __init__(self, 
                intervals:List[float], 
                od_flow_per_minute:Dict[Tuple[str], List[float]], 
                veh_type:Dict[str, Dict[str, float]],
                output_file:str='testflow.trip.xml'
                ) -> None:
        """根据「开始结束时间」，「开始地点」，「结束地点」，「车的数量」，「车的类型」 生成 .trip.xml 文件
        生成的 .trip.xml 文件格式如下所示:
            <routes>
                <vType id="type_0" length="5.0" tau="10.0" color="189,195,199"/>
                <vType id="type_1" length="7.0" tau="10.0" color="241,196,15"/>
                
                <flow id="gsndj_n10__0" begin="0" end="60" from="gsndj_n10" number="5" type="type_1"/>
                <flow id="161701303#7__0" begin="0" end="60" from="161701303#7" number="8" type="type_0"/>
                <flow id="gsndj_s3__0" begin="0" end="60" from="gsndj_s3" number="3" type="type_1"/>
                <flow id="hrj_s4__0" begin="0" end="60" from="hrj_s4" number="2" type="type_1"/>
                <flow id="gneE27__0" begin="0" end="60" from="gneE27" number="6" type="type_1"/>
                <flow id="hrj_n8__0" begin="0" end="60" from="hrj_n8" number="2" type="type_0"/>
                ...
            </routes>

        Args:
            intervals (List): 时间的间隔，每段时间的持续时间（分钟）
                例如两段时间，[20, 30]，表示第一段时间为 20 分钟，第二段时间为 30 分钟

            od_flow_per_minute (Dict[str, List]): 每个时间段从 Origin 到 Destination 进入车辆数量，例如
                {
                    ('o_1', 'd_1'): [10, 20],
                    ('o_2', 'd_2'): [10, 20],
                    ...
                }
                上面表示从 o1 到 d1 在第一个时间段内是 10 veh/min, 第二个时间段是 20 veh/min

            veh_type (Dict[str, Dict[str, float]]): 定义不同的车辆类型:
                {
                    'car_1': {'length':7, 'tau':1, 'color':'26, 188, 156', 'probability':0.7},
                    'car_2': {'length':5, 'tau':1, 'color':'155, 89, 182', 'probability':0.3},
                    ...
                }

            output_file (str, optional): 最终输出的 trip.xml 文件. Defaults to 'testflow.trip.xml'.
        """
        self.intervals = intervals # 时间间隔
        self.od_flow_per_minute = od_flow_per_minute # 每个 od 的车辆
        self.veh_type = veh_type # 定义车辆类型
        self.output_file = output_file # 输出文件

        self.od_flow = self.__multiply_od_flow()

        folder_path, _ = os.path.split(self.output_file)
        check_folder(folder_path) # 检查文件夹是否存在

    def __multiply_od_flow(self):
        """
        将输入的 od_flow_per_minute 中的每个元素与 intervals 对应位置的值相乘，
        并返回一个新的字典，其中键与原始字典相同，值为乘积结果的列表。
        作用，由于输入的 od_flow_per_minute 是每一分钟的车辆信息, 通过乘上 interval 计算出一段时间内一共的车辆.

        Args:
            od_flow_per_minute (dict): 包含边缘流量的字典，键为边缘名称，值为流量列表。
            intervals (list): 包含时间间隔的列表。

        Returns:
            dict: 包含乘积结果的字典，键为边缘名称，值为乘积结果的列表。
        """
        output = {}
        for od, flows in self.od_flow_per_minute.items():
            multiplied_flows = [flow * interval for flow, interval in zip(flows, self.intervals)]
            output[od] = multiplied_flows
        return output


    def generate_trip_xml(self) -> None:
        """生成按照时间排序前的 trip 文件
        """
        blank_hours = 0  # 空白时间, 每小时车辆时间的间隔, 这里单位是秒 (暂时不需要空白时间)
        with open('testflow_tmp.trip.xml', 'w') as file:
            file.write("<routes> \n")

            # ########################
            # 在 trip.xml 中添加车辆信息
            # ########################
            KNOWN_ATTRIBUTES = {'color', 'length', 'tau', 'speed'}
            IGNORE_ATTRIBUTES = {'probability'} # 被忽略的特征
            DEFAULTS = {'color': 'red', 'length': 5, 'tau': 1, 'speed': 17}
            DOC_URL = "https://sumo.dlr.de/docs/Definition_of_Vehicles%2C_Vehicle_Types%2C_and_Routes.html#available_vtype_attributes"
            vehID_prob = {} # 每辆车的概率, {'veh_1':0.7, 'veh_2':0.3}

            for vehicle_id, vehicle_info in self.veh_type.items():
                attributes = [] # 添加车辆的属性
                for key, value in vehicle_info.items():
                    if key in KNOWN_ATTRIBUTES:
                        # Format known attributes with their defaults if necessary
                        value = float(value) if key in {'length', 'tau', 'speed'} else value
                        attributes.append('{}="{}"'.format(key, value))
                    elif key in IGNORE_ATTRIBUTES:
                        pass
                    else:
                        # Log a warning for unknown attributes
                        logger.warning(f"SIM: '{key}' is not a known attribute. Check the documentation for valid attributes. {DOC_URL}.")
                        attributes.append('{}="{}"'.format(key, value))

                # Fill in defaults for any missing known attributes
                for attr, default in DEFAULTS.items():
                    if attr not in vehicle_info:
                        default_value = float(default) if attr in {'length', 'tau', 'speed'} else default
                        attributes.append('{}="{}"'.format(attr, default_value))

                file.write('    <vType id="{}" {} />\n'.format(vehicle_id, ' '.join(attributes)))
                vehID_prob[vehicle_id] = vehicle_info.get('probability', 0.1) # 添加每种车辆出现的概率
            vehID_prob = normalize_dict(vehID_prob) # 概率归一化
            
            # ########################
            # 在 trip.xml 中添加车辆信息
            # ########################
            for (start_edge, end_edge), od_flow_list in self.od_flow.items():
                for interval_index, od_flow_interval in enumerate(od_flow_list): # edge_flow_interval 为每段时间的车辆
                    begin_time = 60 * sum(self.intervals[:int(interval_index)]) + int(interval_index) * blank_hours # 秒
                    end_time = begin_time + 60 * self.intervals[int(interval_index)]

                    # 生成每一种 vehicle type 的车辆数
                    vehicle_types = list(vehID_prob.keys()) # 车辆类型
                    vehicle_weights = list(vehID_prob.values()) # 车辆概览
                    vehicle_counts = {vehicle_type: 0 for vehicle_type in vehicle_types} # c车辆数量
                    for _ in range(round(od_flow_interval)): # 车辆数
                        selected_vehicle = random.choices(vehicle_types, weights=vehicle_weights)[0]
                        vehicle_counts[selected_vehicle] += 1

                        
                    # 不同的 vehicle type 生成不同的车辆
                    for _vehicle_type, count in vehicle_counts.items():
                        od_trip_id = f'{start_edge}__{end_edge}__{interval_index}__{_vehicle_type}' # trip id, edgeID+时间段
                        file.write('    <flow id="{}" begin="{}" end="{}" from="{}" to="{}" number="{}" type="{}"/> \n'.format(
                            od_trip_id,
                            int(begin_time), int(end_time),
                            start_edge, end_edge, 
                            count, _vehicle_type
                        ))
            file.write("</routes> \n\n")

            logger.info('SIM: => OD trip 文件生成成功.')

    def edit_trip_xml(self) -> None:
        """对 trip 文件进行排序, 按照 begin time 来进行排序, 保证之后生成的 route 文件是有序的
        """
        outfile = open(self.output_file, 'w')
        # copy header
        for line in open('testflow_tmp.trip.xml'):
            if (line.find('<routes') == 0 or
                    line.find('<additional') == 0):
                break
            else:
                outfile.write(line)
        self._sort_departs('testflow_tmp.trip.xml', outfile)
        outfile.close()
        os.remove('testflow_tmp.trip.xml') # 删除中间的 trip 文件 (按照时间排序前)
        logger.info('SIM: => OD trip 成功进行排序, 修改成功.')


    def _sort_departs(self, routefilename:str, outfile:str) -> None:
        """对 trip 文件中的 flow 按照时间进行排序

        Args:
            routefilename (str): 输入文件的名称
            outfile (str): 输出文件的名称
        """
        DEPART_ATTRS = {'vehicle': 'depart', 'trip': 'depart', 'flow': 'begin', 'person': 'depart'}
        routes_doc = pulldom.parse(routefilename)
        vehicles = []
        root = None
        for event, parsenode in routes_doc:
            if event == pulldom.START_ELEMENT:
                if root is None:
                    root = parsenode.localName
                    outfile.write("<%s>\n" % root)
                    continue
                routes_doc.expandNode(parsenode)
                departAttr = DEPART_ATTRS.get(parsenode.localName)
                if departAttr is not None:
                    startString = parsenode.getAttribute(departAttr)
                    if ':' in startString:
                        start = sumolib.miscutils.parseTime(startString)
                    elif startString == "triggered":
                        start = -1  # before everything else
                    else:
                        start = float(startString)
                    vehicles.append(
                        (start, parsenode.toprettyxml(indent="", newl="")))
                else:
                    # copy to output
                    outfile.write(
                        " " * 4 + parsenode.toprettyxml(indent="", newl="") + "\n")

        logger.info('SIM: Read %s elements.' % len(vehicles))
        vehicles.sort(key=lambda v: v[0])
        for depart, vehiclexml in vehicles:
            outfile.write(" " * 4)
            outfile.write(vehiclexml)
            outfile.write("\n")
        outfile.write("</%s>\n" % root)
        logger.info('SIM: Wrote %s elements.' % len(vehicles))