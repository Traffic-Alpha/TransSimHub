'''
@Author: WANG Maonan
@Date: 2023-09-22 14:38:20
@Description: 获得地图中所有的 Polygon 的信息
@LastEditTime: 2023-09-25 20:53:02
'''
from loguru import logger

from tshub.map.map_builder import MapBuilder
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.utils.format_dict import dict_to_str

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

poly_file = path_convert("../sumo_env/osm_berlin/env/berlin.poly.xml")
osm_file = path_convert("../sumo_env/osm_berlin/berlin.osm")

map_builder = MapBuilder(
    poly_file=poly_file,
    osm_file=osm_file
)
map_infos = map_builder.get_objects_infos()
logger.info(f'SIM: \n{dict_to_str(map_infos)}')