'''
@Author: WANG Maonan
@Date: 2024-07-03 16:34:37
@Description: 将 SUMO Net 转换为 3D 的素材
@LastEditTime: 2024-07-16 16:16:41
'''
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path

from tshub.tshub_env3d.vis3d_sumonet_convert.sumonet_to_tshub3d import SumoNet3D

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'), terminal_log_level='INFO')

if __name__ == '__main__':
    netxml = path_convert("../sumo_env/single_junction/env/single_junction.net.xml")
    sumonet_to_3d = SumoNet3D(net_file=netxml)
    sumonet_to_3d.to_glb(glb_dir=path_convert("./map_model"))