'''
@Author: WANG Maonan
@Date: 2023-09-25 15:01:48
@Description: convert osm to *.net.xml and *.poly.xml
+ netconvert, https://sumo.dlr.de/docs/Networks/Import/OpenStreetMap.html
+ polyconvert, https://sumo.dlr.de/docs/polyconvert.html
@LastEditTime: 2023-09-25 16:04:09
'''
import sumolib
import subprocess
from pathlib import Path
from loguru import logger
from ..utils.get_abs_path import get_abs_path

current_file_path = get_abs_path(__file__)

DEFAULT_NETCONVERT_OPTS = ('--geometry.remove,--roundabouts.guess,--ramps.guess,--junctions.join,'
                           '--tls.guess-signals,--tls.discard-simple,--tls.join,--output.original-names,'
                           '--junctions.corner-detail,5,--output.street-names')



def scenario_build(osm_file:str, output_directory:str):
    osm_file = Path(osm_file)
    output_directory = Path(output_directory)
    file_name = osm_file.stem # osm 文件的名字

    netconvert = sumolib.checkBinary('netconvert')
    polyconvert = sumolib.checkBinary('polyconvert')

    net_file = output_directory/f"{file_name}.net.xml"
    poly_file = output_directory/f"{file_name}.poly.xml"

    # ###########
    # netconvert
    # ###########
    logger.info(f'开始将 osm 转换为 *.mnet.xml.')
    cfg = output_directory/f'{file_name}.netcfg' # 配置文件
    netconvert_opts = [netconvert]
    netconvert_opts += DEFAULT_NETCONVERT_OPTS.strip().split(',')
    netconvert_opts += ["--keep-edges.by-vclass", "passenger"]
    netconvert_opts += ['--osm-files', osm_file] # 输入的 osm 文件
    netconvert_opts += ['-o', net_file] # 输出的 net file 文件
    subprocess.call(netconvert_opts + ["--save-configuration", cfg], cwd=output_directory)
    logger.info(f'转换的配置文件为, {cfg}.')
    subprocess.call([netconvert, "-c", cfg], cwd=output_directory)
    logger.info(f'{net_file} 转换成功.')
    
    # ###########
    # polyconvert
    # ###########
    logger.info(f'开始将 osm 转换为 *.poly.xml.')
    poly_typemap = current_file_path("./poly.typ.xml")
    cfg = output_directory/f'{file_name}.polycfg' # 配置文件
    polyconvert_opts = [polyconvert]
    polyconvert_opts += ['--type-file', poly_typemap] # 保留的 poly type 类型
    polyconvert_opts += ['--osm-files', osm_file] # 输入的 osm 文件
    polyconvert_opts += ['--discard', 'true'] # 去掉 unknown 的 polygon
    polyconvert_opts += ["-n", net_file, "-o", poly_file]
    subprocess.call(polyconvert_opts + ["--save-configuration", cfg], cwd=output_directory)
    logger.info(f'转换的配置文件为, {cfg}.')
    subprocess.call([polyconvert, "-c", cfg], cwd=output_directory)
    logger.info(f'{poly_file} 转换成功.')

