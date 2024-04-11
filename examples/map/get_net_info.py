'''
@Author: WANG Maonan
@Date: 2023-11-12 14:48:21
@Description: 只获取 net 的信息, 包含 edge 和 node 的 shape
@LastEditTime: 2024-04-09 22:52:44
'''
from loguru import logger

from tshub.map.map_builder import MapBuilder
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.utils.format_dict import dict_to_str

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

net_file = path_convert("../sumo_env/osm_berlin/env/berlin.net.xml")

map_builder = MapBuilder(
    net_file=net_file,
)
map_infos = map_builder.get_objects_infos()
logger.info(f'SIM: \n{dict_to_str(map_infos)}')