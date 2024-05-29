'''
@Author: WANG Maonan
@Date: 2023-09-25 15:01:48
@Description: convert osm to *.net.xml and *.poly.xml
+ netconvert, 
    - https://sumo.dlr.de/docs/Networks/Import/OpenStreetMap.html
    - https://sumo.dlr.de/docs/netconvert.html
    - https://sumo.dlr.de/docs/netgenerate.html
+ polyconvert, https://sumo.dlr.de/docs/polyconvert.html
@LastEditTime: 2024-05-28 20:59:56
'''
import sumolib
import subprocess
from pathlib import Path
from loguru import logger
from ..utils.get_abs_path import get_abs_path

current_file_path = get_abs_path(__file__)

DEFAULT_NETCONVERT_OPTS = (
    '--default.lanenumber,3,'
    '--geometry.remove,'
    '--roundabouts.guess,'
    '--ramps.guess,'
    '--junctions.join,'
    '--tls.discard-simple,--tls.join,'
    '--tls.guess,--tls.guess-signals,--tls.guess.threshold,12,--tls.green.time,30,--tls.layout,incoming,'
    '--no-turnarounds,true,'
    '--junctions.corner-detail,5,'
    '--output.street-names,true,'
    '--output.original-names'
)


def scenario_build(osm_file:str, output_directory:str, netconvert_typemap:str=None, poly_typemap:str=None):
    """根据 OSM 文件生成 *.poly.xml 和 *.net.xml 文件

    Args:
        osm_file (str): 原始的 OSM 文件
        output_directory (str): *.net.xml 和 *.poly.xml 输出的文件夹
        netconvert_typemap (str, optional): _description_. Defaults to None.
        poly_typemap (str, optional): _description_. Defaults to None.

    Raises:
        subprocess.CalledProcessError: _description_
        Exception: _description_
    """
    osm_file = Path(osm_file)
    output_directory = Path(output_directory)
    file_name = osm_file.stem # osm 文件的名字

    netconvert = sumolib.checkBinary('netconvert')
    polyconvert = sumolib.checkBinary('polyconvert')

    net_file = output_directory/f"{file_name}.net.xml"
    poly_file = output_directory/f"{file_name}.poly.xml"

    # ##################
    # netconvert config
    # ##################
    logger.info(f'SIM: 开始设置 netconvert 的参数.')
    net_cfg = output_directory/f'{file_name}.netecfg' # 配置文件
    if netconvert_typemap is None:
        netconvert_typemap = current_file_path('./osm_build_type/net.typ.xml')
    netconvert_opts = [netconvert]
    netconvert_opts += ["-t", netconvert_typemap]
    netconvert_opts += DEFAULT_NETCONVERT_OPTS.strip().split(',')
    netconvert_opts += ["--keep-edges.by-vclass", "passenger"] # 保留行人的道路
    netconvert_opts += ['--osm-files', osm_file] # 输入的 osm 文件
    netconvert_opts += ['-o', net_file] # 输出的 net file 文件        
    netconvert_opts += ['--save-configuration', net_cfg]
    
    # ###################
    # polyconvert config
    # ###################
    logger.info(f'SIM: 开始设置 polyconvert 的参数.')
    if poly_typemap is None:
        poly_typemap = current_file_path("./osm_build_type/poly.typ.xml")
    poly_cfg = output_directory/f'{file_name}.polygcfg' # 配置文件
    polyconvert_opts = [polyconvert]
    polyconvert_opts += ['--type-file', poly_typemap] # 保留的 poly type 类型
    polyconvert_opts += ['--osm-files', osm_file] # 输入的 osm 文件
    polyconvert_opts += ['--discard', 'true'] # 去掉 unknown 的 polygon
    polyconvert_opts += ['--osm.merge-relations', '1']
    polyconvert_opts += ["-n", net_file, "-o", poly_file]
    polyconvert_opts += ['--save-configuration', poly_cfg]

    # #########
    # commands
    # #########
    commands = [
        netconvert_opts,
        [netconvert, "-c", net_cfg],
        polyconvert_opts,
        [polyconvert, "-c", poly_cfg]
    ]
    for command in commands:
        try:
            output = subprocess.check_output(command, cwd=output_directory, stderr=subprocess.STDOUT)
            output_str = output.decode()
            if "Error" in output_str:
                raise subprocess.CalledProcessError(returncode=1, cmd=command, output=output)
            logger.info(f'SIM: 命令 {command} 执行成功.')
        except subprocess.CalledProcessError as e:
            logger.info(f'SIM: !!!命令 {command} 执行失败!!!')
            logger.info(f'SIM: 错误信息为: {e.output.decode()}')
            raise Exception("SIM: 调用失败，存在错误返回")