'''
@Author: WANG Maonan
@Date: 2023-09-25 15:15:19
@Description: 测试 osm_build 的功能, 快速从 OSM 中创建场景
@LastEditTime: 2023-11-23 23:27:32
'''
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.sumo_tools.osm_build import scenario_build

current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'))


if __name__ == '__main__':
    osm_file = current_file_path("../sumo_env/osm_berlin/berlin.osm")
    output_directory = current_file_path("../sumo_env/osm_berlin/env/")

    # 默认: 使用内置完整版 typemap (net / poly)
    scenario_build(
        osm_file=osm_file,
        output_directory=output_directory
    )

    # ##############################
    # typemap 组合用法 (按需取消注释)
    # ##############################
    # netconvert_typemap / poly_typemap 支持传列表来叠加多个 typemap,
    # 列表项可以是内置短名 (osm_build_type/ 或 osm_build_type/layers/ 下的文件),
    # 也可以是自备的文件路径. 多个 typemap 按顺序合并, 后者覆盖前者同名 type.
    #
    # scenario_build(
    #     osm_file=osm_file,
    #     output_directory=output_directory,
    #     netconvert_typemap=["net", "net_ground_only"],  # 完整地面路网, 去掉高架/快速路
    #     poly_typemap=["poly", "poly_buildings_only"],   # 只保留建筑/设施 (含警局)
    # )