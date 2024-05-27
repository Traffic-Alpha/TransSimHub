'''
@Author: WANG Maonan
@Date: 2024-05-27 13:14:57
@Description: Convert OSM to Net 
@LastEditTime: 2024-05-27 16:16:34
'''
import os
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.sumo_tools.osm_build import scenario_build # osm -> net.xml & poly.xml
from tshub.sumo_tools.osm_filter import extract_ids, filter_osm # net.xml & poly.xml -> osm

current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'))


if __name__ == '__main__':
    osm_file = current_file_path("../sumo_env/osm_berlin/berlin.osm")
    output_directory = current_file_path("../sumo_env/osm_berlin/env/")
    scenario_build(
        osm_file=osm_file,
        output_directory=output_directory
    )

    keep_ids = extract_ids(
        poly_xml_path=os.path.join(output_directory, 'berlin.poly.xml'),
        net_xml_path=os.path.join(output_directory, 'berlin.net.xml'),
    )
    filter_osm(
        ways_to_keep=keep_ids,
        input_osm=osm_file,
        output_osm=current_file_path("./berlin_filter.osm")
    )