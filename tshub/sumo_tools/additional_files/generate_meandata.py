'''
@Author: WANG Maonan
@Date: 2026-07-31 10:00:00
@Description: 生成 meandata (edgeData/laneData) 的 additional 文件, 用于导出宏观交通状态,
    是「拥堵大屏 replay」的数据来源。输出格式如下:
<additional xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/additional_file.xsd">
    <edgeData id="macro_edge" file="macro_edge.xml" period="60" excludeEmpty="defaults" withInternal="false"/>
    <laneData id="macro_lane" file="macro_lane.xml" period="60" excludeEmpty="defaults" withInternal="false"/>
</additional>

两者的区别 (决定了大屏为什么两个都要):
1. edgeData 直接把指标写在 <edge> 上, 是 SUMO 自己做的路段级聚合, 权威且文件小,
   用来驱动大屏的路网着色;
2. laneData 的 <edge> 只是容器, 指标全部写在内嵌的 <lane> 上, 文件较大,
   仅在点击某条路段查看车道级明细时按需解析。

输出的属性中 speedRelative (实际速度/限速) 可以直接作为拥堵指数; 生成的文件通过
TshubEnvironment(tls_state_add=[...]) 传入, 对应 SUMO 的 -a 参数。
@LastEditTime: 2026-07-31 10:00:00
'''
import sumolib
from loguru import logger
from typing import List


def generate_meandata(
        output_file: str,
        edge_data_file: str = None,
        lane_data_file: str = None,
        period: int = 60,
        meandata_id: str = 'macro',
        exclude_empty: str = 'defaults',
        with_internal: bool = False,
        begin: int = None,
        end: int = None,
        extra_attributes: List[str] = None,
    ) -> None:
    """生成 meandata 的 additional 文件

    Args:
        output_file (str): 生成的 .add.xml 的保存路径。
        edge_data_file (str, optional): SUMO 将写入的 edgeData 输出路径 (路段级聚合)。
            为 None 时不输出 edgeData。Defaults to None.
        lane_data_file (str, optional): SUMO 将写入的 laneData 输出路径 (车道级明细)。
            为 None 时不输出 laneData。Defaults to None.
        period (int, optional): 聚合周期, 单位秒。周期越小时间分辨率越高, 数据量也越大。Defaults to 60.
        meandata_id (str, optional): meandata 的 id 前缀, 实际会生成 {id}_edge 与 {id}_lane。Defaults to 'macro'.
        exclude_empty (str, optional): 空 edge 的处理方式, 可选 'false'/'true'/'defaults'。
            'defaults' 会让没有车辆的 edge 也出现在输出中 (带默认值, sampledSeconds=0 且
            speedRelative=1), 这样每个时间片的 edge 集合保持一致, 前端不必处理缺失,
            因此作为默认值。Defaults to 'defaults'.
        with_internal (bool, optional): 是否统计路口内部 (':' 开头) 的 edge/lane。
            大屏只画普通路段, 因此默认关闭。Defaults to False.
        begin (int, optional): 统计开始时间, None 表示从仿真开始。Defaults to None.
        end (int, optional): 统计结束时间, None 表示到仿真结束。Defaults to None.
        extra_attributes (List[str], optional): 需要输出的属性白名单 (对应 SUMO 的 writeAttributes),
            为 None 时输出全部属性。Defaults to None.

    Raises:
        ValueError: edge_data_file 与 lane_data_file 均为 None, 或 exclude_empty 取值非法。
    """
    if (edge_data_file is None) and (lane_data_file is None):
        raise ValueError('edge_data_file 与 lane_data_file 至少要指定一个。')
    if exclude_empty not in ('false', 'true', 'defaults'):
        raise ValueError(f"exclude_empty 只能是 'false'/'true'/'defaults', 当前是 {exclude_empty}.")

    meandata_add_xml = sumolib.xml.create_document("additional")

    def _add_meandata(element_name: str, data_file: str, element_id: str) -> None:
        """向 additional 文件中添加一个 edgeData/laneData 元素"""
        meandata_xml = meandata_add_xml.addChild(element_name)
        meandata_xml.setAttribute("id", element_id)
        meandata_xml.setAttribute("file", data_file)
        meandata_xml.setAttribute("period", str(period))
        meandata_xml.setAttribute("excludeEmpty", exclude_empty)
        meandata_xml.setAttribute("withInternal", "true" if with_internal else "false")
        if begin is not None:
            meandata_xml.setAttribute("begin", str(begin))
        if end is not None:
            meandata_xml.setAttribute("end", str(end))
        if extra_attributes is not None:
            meandata_xml.setAttribute("writeAttributes", " ".join(extra_attributes))

    if edge_data_file is not None:
        _add_meandata("edgeData", edge_data_file, f'{meandata_id}_edge')
    if lane_data_file is not None:
        _add_meandata("laneData", lane_data_file, f'{meandata_id}_lane')

    with open(output_file, 'w') as meandata_add_file:
        meandata_add_file.write(meandata_add_xml.toXML())

    logger.info(
        f'SIM: 完成 MeanData Additions 文件写入, {output_file} '
        f'(period={period}s, edge={edge_data_file}, lane={lane_data_file}).'
    )
