'''
@Author: WANG Maonan
@Date: 2024-05-29 15:01:25
@Description: 将地图划分为 grid, 获得每个 grid 每个座标点的信息, 例如 SNR
LastEditTime: 2026-02-13 15:06:46
'''
from loguru import logger

from tshub.map.map_builder import MapBuilder
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.utils.format_dict import dict_to_str

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

net_file = path_convert("../sumo_env/berlin_UAM/berlin_UAM.net.xml")
snir_file = path_convert("../sumo_env/berlin_UAM/berlin_UAM_SNIR_100.txt")

map_builder = MapBuilder(
    net_file=net_file,
    radio_map_files={'SNIR_100': snir_file}
)
map_infos = map_builder.get_objects_infos()

# Get Lane infos in the Map
logger.info(f'SIM: \n{dict_to_str(map_infos['lane'])}')

# Get Node Infos in the Map
logger.info(f'SIM: \n{dict_to_str(map_infos['node'])}')

# Get Building Infos in the Map
logger.info(f'SIM: \n{dict_to_str(map_infos['building'])}')

# Get Grid Infos in the Map
logger.info(f'SIM: \n{map_infos['grid']['SNIR_100'].get_value_at_coordinate(500, 1000)}') # 获得每一个点的信息
logger.info(f'SIM: \n{map_infos['grid']['SNIR_100'].grid_z}') # 获得地图的信息