'''
@Author: WANG Maonan
@Date: 2023-09-25 15:01:48
@Description: convert osm to *.net.xml and *.poly.xml
+ netconvert,
    - https://sumo.dlr.de/docs/Networks/Import/OpenStreetMap.html
    - https://sumo.dlr.de/docs/netconvert.html
    - https://sumo.dlr.de/docs/netgenerate.html
+ polyconvert, https://sumo.dlr.de/docs/polyconvert.html

============================================================================
typemap 是什么
============================================================================
typemap 是一张"翻译对照表": 把 OSM 里的标签翻译成 SUMO 里的类型. 它分成互不相干的两条线:
    + net  线 -> 路网 (道路/车道/路口/信号灯). 由 netconvert + netconvert_typemap 处理.
    + poly 线 -> 地物 (建筑物/绿地/水域...). 由 polyconvert + poly_typemap 处理.
注意: 建筑物 (含警局) 属于 poly 线, 跟 net 线无关 —— 给 net 加东西不会冒出建筑物.

============================================================================
osm_build_type/ 目录约定 (两层): base 完整表  +  layers/ 叠加补丁
============================================================================
+ 外层 net.typ.xml / poly.typ.xml = "完整基础表 (base)"
    一张齐全、能单独使用的对照表: net.typ.xml 列出了 motorway/primary/residential...
    所有道路类型, poly.typ.xml 列出了 building/amenity/landuse/water... 所有地物类型.
    不传参时默认就用它们. (对应 SUMO 自带 osmNetconvert / osmPolyconvert 完整版.)

+ 内层 layers/*.typ.xml = "叠加补丁 (overlay)"
    内容残缺, 不能单独使用, 只定义"在 base 之上要改/丢哪些 type", 必须叠加在 base 之后.
    叠加补丁可以是"减法"也可以是"改属性":
      - net_ground_only : 减法. 全文只把 motorway/trunk 标 discard="true" (=丢掉这些路).
                          "ground_only" 指只留地面道路, 删掉高架/快速路, 与建筑物无关.
      - poly_buildings_only : 减法. 把 water/forest/landuse 等标 discard (=只留建筑/设施).
      - net_pedestrian  : 改属性. 给主要道路追加 sidewalkWidth (人行道).
    新增过滤器/叠加层请放到 layers/, 保持外层只放完整基础表.

============================================================================
组合用法 (传列表即按顺序叠加, 后者覆盖前者同名 type 的同名属性)
============================================================================
列表项可以是文件路径, 也可以是内置短名 (osm_build_type/ 下的 *.typ.xml, 不含后缀):

    netconvert_typemap=["net"]                     # 完整路网: 高架+快速路+地面道路 全都有
    netconvert_typemap=["net", "net_ground_only"]  # 在完整路网上删掉高架/快速路, 只留地面
    poly_typemap=["poly"]                          # 完整地物: 建筑+绿地+水域 全都有 (默认)
    poly_typemap=["poly", "poly_buildings_only"]   # 在完整地物上删掉绿地/水域, 只留建筑/设施

合并示例 ["net", "net_ground_only"] 发生了什么:
    1) 先拿完整的 net 表 (motorway/trunk/primary/residential... 都在, 都会被转出来)
    2) 再用 net_ground_only 打补丁: motorway/trunk 那几条被改成 discard="true"
    3) 结果: primary 及以下地面道路照常转出, motorway/trunk 被丢弃
    (属性级覆盖: motorway 仍保留 base 里的 numLanes/speed, 只是多了 discard="true".)

实现说明: polyconvert 的 --type-file 只接受单个文件 (仅 netconvert -t 支持逗号多文件),
因此当传入多个 typemap 时, 这里在进程内按上述语义自行合并成单个 *.merged.*.typ.xml
再交给工具 (见 _resolve_typemap_paths / _merge_typemaps); 单文件时直接透传, 不产生额外文件.
@LastEditTime: 2024-05-28 20:59:56
'''
import sumolib
import subprocess
import xml.etree.ElementTree as ET
from typing import List, Literal, Union
from pathlib import Path
from loguru import logger
from ..utils.get_abs_path import get_abs_path

current_file_path = get_abs_path(__file__)

DRIVING_SIDE = Literal['left', 'right']


def _is_left_hand_traffic(driving_side: DRIVING_SIDE) -> bool:
    """把行驶侧参数转换为 SUMO netconvert 的 --lefthand 参数值."""
    if driving_side not in ('left', 'right'):
        raise ValueError("SIM: driving_side 只能是 'left' 或 'right'.")
    return driving_side == 'left'


def _resolve_typemap_paths(value: Union[str, List[str], None], default_name: str) -> List[str]:
    """把 typemap 参数解析成一组绝对文件路径.

    Args:
        value: None / 单个 (路径或内置短名) / 列表. None 时使用 default_name.
        default_name: 缺省使用的内置短名 ("net" 或 "poly").

    Returns:
        List[str]: 解析后的 typemap 绝对路径列表 (保持传入顺序).
    """
    if value is None:
        value = [default_name]
    elif isinstance(value, str):
        value = [value]

    resolved = []
    for item in value:
        item = str(item)
        # 已存在的文件路径 -> 原样使用 (用户自备的 typemap)
        # 转成绝对路径, 因为命令最终以 cwd=output_directory 执行, 相对路径会失效
        if Path(item).is_file():
            resolved.append(str(Path(item).resolve()))
            continue
        # 否则当作内置短名, 依次在 osm_build_type/ 和 osm_build_type/layers/ 下查找
        for candidate in (
            f'./osm_build_type/{item}.typ.xml',
            f'./osm_build_type/layers/{item}.typ.xml',
        ):
            candidate_path = current_file_path(candidate)
            if Path(candidate_path).is_file():
                resolved.append(candidate_path)
                break
        else:
            raise FileNotFoundError(
                f"SIM: 无法解析 typemap '{item}': 既不是已存在的文件, "
                f"也不是 osm_build_type/ 或 osm_build_type/layers/ 下的内置短名."
            )
    return resolved


def _merge_typemaps(paths: List[str], merged_path) -> str:
    """把多个 typemap 文件合并成单个文件, 返回最终使用的文件路径.

    polyconvert 的 --type-file 只接受单个文件 (netconvert -t 虽支持逗号, 这里统一处理),
    因此当传入多个 typemap 时, 在这里按 SUMO 的叠加语义合并: 以 id 为键, 后面的文件
    覆盖前面同名 type 的同名属性 (其余属性保留), 新 id 追加在末尾.

    单个文件时直接返回原路径, 不产生额外文件 (保持默认行为不变).

    Args:
        paths: _resolve_typemap_paths 返回的有序路径列表.
        merged_path: 多文件合并时的输出路径.

    Returns:
        str: 最终交给 netconvert / polyconvert 的单个 typemap 路径.
    """
    if len(paths) == 1:
        return paths[0]

    base_tree = ET.parse(paths[0])
    root = base_tree.getroot()
    index = {child.get('id'): child for child in root if child.get('id') is not None}
    for path in paths[1:]:
        for child in ET.parse(path).getroot():
            child_id = child.get('id')
            if child_id is None:
                continue
            if child_id in index:
                index[child_id].attrib.update(child.attrib) # 属性级覆盖, 保留其余属性
            else:
                root.append(child)
                index[child_id] = child
    base_tree.write(merged_path, encoding='utf-8', xml_declaration=True)
    return str(merged_path)

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


def scenario_build(
    osm_file:str,
    output_directory:str,
    netconvert_typemap:Union[str, List[str]]=None,
    poly_typemap:Union[str, List[str]]=None,
    driving_side:DRIVING_SIDE='right',
):
    """根据 OSM 文件生成 *.poly.xml 和 *.net.xml 文件

    Args:
        osm_file (str): 原始的 OSM 文件
        output_directory (str): *.net.xml 和 *.poly.xml 输出的文件夹
        netconvert_typemap (str | List[str], optional): netconvert 使用的 typemap.
            可以是单个文件路径/内置短名, 也可以是列表 (按顺序叠加, 后者覆盖前者同名 type).
            None 时使用内置完整版 "net". 内置短名见 osm_build_type/layers/.
        poly_typemap (str | List[str], optional): polyconvert 使用的 typemap, 含义同上.
            None 时使用内置完整版 "poly".
        driving_side ("left" | "right", optional): 道路通行方向. "left" 表示靠左行驶,
            "right" 表示靠右行驶. 默认 "right".

    Raises:
        FileNotFoundError: typemap 短名无法解析时抛出.
        subprocess.CalledProcessError: _description_
        Exception: _description_
    """
    osm_file = Path(osm_file)
    output_directory = Path(output_directory)
    file_name = osm_file.stem # osm 文件的名字
    lefthand = _is_left_hand_traffic(driving_side)

    netconvert = sumolib.checkBinary('netconvert')
    polyconvert = sumolib.checkBinary('polyconvert')

    net_file = output_directory/f"{file_name}.net.xml"
    poly_file = output_directory/f"{file_name}.poly.xml"

    # ##################
    # netconvert config
    # ##################
    logger.info(f'SIM: 开始设置 netconvert 的参数.')
    net_cfg = output_directory/f'{file_name}.netecfg' # 配置文件
    # 解析 + (多文件时) 合并 typemap; 支持单个/列表/内置短名
    netconvert_typemap = _merge_typemaps(
        _resolve_typemap_paths(netconvert_typemap, 'net'),
        output_directory/f'{file_name}.merged.net.typ.xml',
    )
    netconvert_opts = [netconvert]
    netconvert_opts += ["-t", netconvert_typemap]
    netconvert_opts += DEFAULT_NETCONVERT_OPTS.strip().split(',')
    netconvert_opts += ['--lefthand', str(lefthand).lower()] # 是否靠左行驶
    netconvert_opts += ["--keep-edges.by-vclass", "passenger"] # 保留行人的道路
    netconvert_opts += ['--osm-files', osm_file] # 输入的 osm 文件
    netconvert_opts += ['-o', net_file] # 输出的 net file 文件        
    netconvert_opts += ['--save-configuration', net_cfg]
    
    # ###################
    # polyconvert config
    # ###################
    logger.info(f'SIM: 开始设置 polyconvert 的参数.')
    # 解析 + (多文件时) 合并 typemap; 支持单个/列表/内置短名
    poly_typemap = _merge_typemaps(
        _resolve_typemap_paths(poly_typemap, 'poly'),
        output_directory/f'{file_name}.merged.poly.typ.xml',
    )
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
