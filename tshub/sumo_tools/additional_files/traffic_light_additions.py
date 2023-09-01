'''
@Author: WANG Maonan
@Date: 2023-09-01 15:24:03
@Description: 基于 tls_id, 自动生成 additionals 文件, 输出格式如下:
<additional xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/additional_file.xsd">
    <timedEvent type="SaveTLSStates" source="htddj_gsndj" dest="tls_state.out.xml"/>
    <timedEvent type="SaveTLSProgram" source="htddj_gsndj" dest="tls_program.out.xml"/>
    <timedEvent type="SaveTLSSwitchStates" source="htddj_gsndj" dest="tls_switch_states.out.xml"/>
    <timedEvent type="SaveTLSSwitchTimes" source="htddj_gsndj" dest="tls_switches.out.xml"/>
</additional>
@LastEditTime: 2023-09-01 15:49:47
'''
import sumolib
from loguru import logger
from ..sumo_infos.traffic_light_ids import get_tlsID_list

def generate_traffic_lights_additions(network_file: str, output_file: str) -> None:
    """
    生成用于Sumo的交通信号灯添加文件。
    
    Args:
        network_file (str): Sumo网络文件路径。
        output_file (str): 输出的Sumo添加文件路径。
    """
    tls_ids = get_tlsID_list(network_file=network_file)
    types = ['SaveTLSStates', 'SaveTLSProgram', 'SaveTLSSwitchStates', 'SaveTLSSwitchTimes']
    tls_add_xml = sumolib.xml.create_document("additional")

    for event_type in types:
        for tls_id in tls_ids:
            time_event_xml = tls_add_xml.addChild("timedEvent")
            time_event_xml.setAttribute("type", event_type)
            time_event_xml.setAttribute("source", tls_id)
            time_event_xml.setAttribute("dest", f'{event_type}_{tls_id}.out.xml')

    with open(output_file, 'w') as tls_add_file:
        tls_add_file.write(tls_add_xml.toXML())

    logger.info(f'SIM: 完成 TLS Additions 文件写入, {output_file}。')
