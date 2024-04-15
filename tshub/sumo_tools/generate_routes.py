'''
@Author: WANG Maonan
@Date: 2023-08-30 19:26:40
@Description: 批量给环境生成 route 路网
1. 可以设置 ego 车的渗透率, 这里是一个参数可以设置, 车辆类型可以设置车辆的 type
2. 设置车辆的初始速度是 9m/s - 32km/s, 这里是一个参数可以设置
3. 给出的是这个时间段内的来车的速度, vehicle/second
@LastEditTime: 2024-04-15 16:00:13
'''
import os
import sumolib
import subprocess
import numpy as np
from typing import Dict, List
from tempfile import TemporaryFile
from loguru import logger

from ..utils.check_folder import check_folder
from .generate_route.generate_trip import GenerateTrip
from .generate_route.generate_turn_def import GenerateTurnDef
from .generate_route.generate_person import GeneratePersonTrip
from .interpolation.values_interpolation import InterpolationValues
from .interpolation.repeat_values import repeat_values

def interpolate_values(values:Dict[str, List[float]], interval:List[float], interpolate:bool):
    intervals = np.ones(sum(interval)) # 每个间隔持续一分钟
    if interpolate:
        for _id, _value in values.items():
            smooth_values = InterpolationValues(values=_value, intervals=interval)
            smooth_list = smooth_values.get_smooth_values()
            values.update({_id: smooth_list})
    else:
        for _id, _value in values.items():
            smooth_list = repeat_values(values=_value, period=interval)
            values.update({_id: smooth_list})
    return intervals, values


def generate_route(sumo_net:str, 
                    interval:List[float], 
                    edge_flow_per_minute:Dict[str, List[float]],
                    edge_turndef:Dict[str, List[float]],
                    veh_type:Dict[str, Dict[str, float]],
                    walk_flow_per_minute:Dict[str, List[float]]=None,
                    output_trip:str='_testflow.trip.xml',
                    output_turndef:str='_testflow.turndefs.xml',
                    output_route:str='vehicle.rou.xml',
                    person_trip_file:str='_person.trip.xml',
                    output_person_file:str='pedestrian.rou.xml',
                    walkfactor:float=0.7,
                    interpolate_flow:bool=False,
                    interpolate_turndef:bool=False,
                    interpolate_walkflow:bool=False,
                    random_flow:bool=True,
                    seed:int=777
                    ) -> None:
    """根据 turn definition 和 trip 文件, 生成 route 文件

    Args:
        sumo_net (str): sumo net 路网的文件路径
        interval (List[float]): 时间的间隔，每段时间的持续时间（分钟），例如两段时间，[20, 30]，表示第一段时间为 20 分钟，第二段时间为 30 分钟
        edge_flow_per_minute (Dict[str, List[float]]): 每个 edge 每个时间段的车辆 veh/min
            {
                'edge_1': [10, 20],
                'edge_2': [20, 30],
                ...
            }
        edge_turndef (Dict[str, List[float]]): 每一个 connection 每一个时间间隔的概率
            {
                'fromEdge1__toEdge1': [0.5, 0.5, 0.2],
                'fromEdge2__toEdge2': [0.2, 0.3, 0.4],
                'fromEdge3__toEdge3': [0.6, 0.1, 0.3],
                ...
            }
        veh_type (Dict[str, Dict[str, float]]): 定义不同的车辆类型:
            {
                'car_1': {'length':7, 'tau':1, 'color':'26, 188, 156', 'probability':0.7},
                'car_2': {'length':5, 'tau':1, 'color':'155, 89, 182', 'probability':0.3},
                ...
            }
        walk_flow_per_minute (Dict[str, List[float]]): 每分钟 fromEdge-toEdge 的行人数量. 如果是 None 的时候, 就不生成行人的 route 文件
            {
                'E1__E2': [10, 20, 30], 
                'E1__-E3': [40, 50, 60]
            }
        output_trip (str, optional): 生成的 .trip.xml 文件的路径. Defaults to '_testflow.trip.xml'.
        output_turndef (str, optional): 生成的 .turndef.xml 文件的路径. Defaults to '_testflow.turndefs.xml'.
        output_route (str, optional): 生成的 .rou.xml 文件的路径. Defaults to 'vehicle.rou.xml'.
        person_trip_file (str, optional): 为 person 生成的 .trip.xml 文件的路径. Defaults to '_person.trip.xml'.
        output_person_file (str, optional): 为 person 生成的 .rou.xml 文件的路径. Defaults to 'pedestrian.rou.xml'.
        interpolate_flow (bool, optional): 是否对 flow 进行平滑. Defaults to False.
        interpolate_turndef (bool, optional): 是否对 turndef 进行平滑. Defaults to False.
        interpolate_walkflow (bool, optional): 是否对 walk flow 进行平滑. Defaults to False.
        random_flow (bool, optional): 控制车流出现的时间是否随机. Defaults to True.
        walkfactor (float, optional): pedestrian maximum speed during intermodal routing;. Defaults to 0.7.
        seed (int, optional): 随机数种子, 控制使用 JTRROUTER 生成的 route 是一样的. Defaults to 777.

    Raises:
        Exception: Route 文件无法成功生成.
    """
    # 对 flow 或是 turndef 进行平滑
    intervals, flow_info = interpolate_values(edge_flow_per_minute, interval, interpolate_flow)
    intervals, turndefs_info = interpolate_values(edge_turndef, interval, interpolate_turndef)

    # --- 生成 person 文件 ---
    if walk_flow_per_minute is None:
        logger.info('SIM: 不生成行人的 Route 文件.')
    else:
        intervals, walk_flow_info = interpolate_values(walk_flow_per_minute, interval, interpolate_walkflow)
        generate_person_flow = GeneratePersonTrip(
            net_file=sumo_net,
            intervals=intervals,
            walk_flow_per_minute=walk_flow_info,
            seed=seed,
            walkfactor=walkfactor,
            person_trip_file=person_trip_file,
            output_file=output_person_file
        )
        generate_person_flow.generate_person_route()


    # --- 生成 vehicle 文件 ---

    # 生成 .trip.xml 文件
    generate_trip = GenerateTrip(
        intervals=intervals, edge_flow_per_minute=flow_info, 
        veh_type=veh_type, output_file=output_trip
    )
    generate_trip.generate_trip_xml() # 生成 .trip.xml
    generate_trip.edit_trip_xml() # 修改 .trip.xml, 是的 begin time 按照时间排序

    # 生成 .turndefs.xml 文件
    generate_turndef = GenerateTurnDef(
        intervals=intervals, edge_turndef=turndefs_info, 
        sumo_net=sumo_net, output_file=output_turndef
    )
    generate_turndef.generate_turn_definition() # 生成完整的 turndef 文件
    generate_turndef.edit_turn_definition() # 修改 turndef 概率

    # 检查 .rou.xml 文件是否存在
    folder_path, _ = os.path.split(output_route)
    check_folder(folder_path)
    
    # 根据 trip 和 turndef 文件生成 route 文件
    JTRROUTER = sumolib.checkBinary('jtrrouter')  # 返回地址
    temp_file = TemporaryFile()
    prog = subprocess.Popen([JTRROUTER, "-n", sumo_net,
                            "--route-files", output_trip,
                            "--accept-all-destinations", str(True),
                            "--seed", str(seed),  # 随机数种子
                            "--randomize-flows", str(random_flow),  # 车辆出现时间是否随机
                            "--turn-ratio-files", output_turndef,
                            "--departlane", "random",
                            "-o", output_route,
                            "--no-warnings"], 
                            stderr=temp_file,
                            shell=False)  # 生成 route 文件
    prog.wait()
    temp_file.seek(0)
    err = temp_file.read()
    if err == b'':
        logger.info('SIM: 生成 route 文件成功.')
    else:
        logger.error('{}'.format(err))
        raise Exception("route 文件生成失败, 检查 trip 文件和 turn definition 文件")
    temp_file.close()
