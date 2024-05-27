'''
@Author: WANG Maonan
@Date: 2024-05-27 15:18:49
@Description: 根据 *.net.xml 和 *.poly.xml 文件过滤原始的 osm 文件
@LastEditTime: 2024-05-27 15:27:04
'''
from loguru import logger
import xml.etree.ElementTree as ET


def extract_ids(poly_xml_path:str, net_xml_path:str):
    # Parse the .poly.xml file and extract way ids
    logger.info(f'SIM: 开始提取 {poly_xml_path} 的 id.')
    poly_tree = ET.parse(poly_xml_path)
    poly_root = poly_tree.getroot()
    poly_ids = {poly.get('id') for poly in poly_root.findall('poly')}
    logger.info(f'SIM: 成功提取 {poly_xml_path} 的 id.')

    # Parse the .net.xml file and extract origId values
    logger.info(f'SIM: 开始提取 {net_xml_path} 的 id.')
    net_tree = ET.parse(net_xml_path)
    net_root = net_tree.getroot()
    net_ids = set()
    for edge in net_root.findall('edge'):
        for lane in edge.findall('lane'):
            param = lane.find('param[@key="origId"]')
            if param is not None:
                net_ids.update(param.get('value').split())
    logger.info(f'SIM: 成功提取 {net_xml_path} 的 id.')

    # Combine ids from both files
    ways_to_keep = poly_ids.union(net_ids)
    return ways_to_keep

def filter_osm(ways_to_keep, input_osm, output_osm):
    # Parse the input OSM file
    tree = ET.parse(input_osm)
    root = tree.getroot()

    # Collect nodes and relations referenced by the ways to keep
    nodes_to_keep = set() # 需要保留的 nodes 节点
    relations_to_keep = set()
    
    # Filter ways
    logger.info(f'SIM: 过滤 OSM Ways ...')
    for way in root.findall('way'):
        way_id = way.get('id')
        if way_id not in ways_to_keep:
            root.remove(way)
        else:
            for nd in way.findall('nd'):
                nodes_to_keep.add(nd.get('ref'))
    
    # Filter nodes
    logger.info(f'SIM: 过滤 OSM Nodes ...')
    for node in root.findall('node'):
        node_id = node.get('id')
        if node_id not in nodes_to_keep:
            root.remove(node)
    
    # Filter and update relations
    logger.info(f'SIM: 过滤 OSM Relations ...')
    for relation in root.findall('relation'):
        keep_relation = False
        for member in relation.findall('member'):
            member_type = member.get('type')
            member_ref = member.get('ref')
            if (member_type == 'way' and member_ref in ways_to_keep) or (member_type == 'node' and member_ref in nodes_to_keep):
                keep_relation = True
            else:
                relation.remove(member)
        if not keep_relation:
            root.remove(relation)
        else:
            relations_to_keep.add(relation.get('id'))

    # Write the output OSM file
    tree.write(output_osm)