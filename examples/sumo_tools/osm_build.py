'''
@Author: WANG Maonan
@Date: 2023-09-25 15:15:19
@Description: 测试 osm_build 的功能
@LastEditTime: 2023-09-25 15:36:18
'''
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.sumo_tools.osm_build import scenario_build

current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'))


if __name__ == '__main__':
    osm_file = current_file_path("../sumo_env/test_osm/berlin.osm")
    output_directory = current_file_path("../sumo_env/test_osm/")
    scenario_build(
        osm_file=osm_file,
        output_directory=output_directory
    )