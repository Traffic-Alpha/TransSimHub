'''
@Author: WANG Maonan
@Date: 2023-09-22 14:47:02
@Description: 使用 matplotlib 绘制 Polygon 的形状
@LastEditTime: 2023-09-26 20:22:11
'''
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

from tshub.map.map_builder import MapBuilder
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

poly_file = path_convert("../sumo_env/osm_berlin/env/berlin.poly.xml")
osm_file = path_convert("../sumo_env/osm_berlin/berlin.osm")

map_builder = MapBuilder(
    poly_file=poly_file,
    osm_file=osm_file
)
map_infos = map_builder.get_objects_infos()


# 绘制图像
building_levels = [int(polygon_data["building_levels"]) for polygon_data in map_infos.values()]
# 创建一个颜色映射对象
cmap = plt.cm.get_cmap("cool")  # 使用"cool"颜色映射，可以根据需求更改
# 根据建筑物高度信息创建归一化对象
normalize = Normalize(vmin=min(building_levels), vmax=max(building_levels))


fig, ax = plt.subplots()
# 遍历每个多边形
for polygon_id, polygon_data in map_infos.items():
    # 提取顶点坐标和高度信息
    vertices = polygon_data["shape"]
    building_levels = int(polygon_data["building_levels"])

    # 创建多边形对象
    polygon = Polygon(vertices, closed=True)

    # 获取建筑物对应的归一化高度值
    normalized_height = normalize(building_levels)

    # 根据归一化高度值获取对应的颜色
    color = cmap(normalized_height)

    # 将多边形添加到图形对象中
    ax.add_patch(polygon)

    # 设置多边形的颜色
    polygon.set_facecolor(color)

# 设置坐标轴范围
ax.autoscale()

# 创建一个颜色映射对象的标注
sm = ScalarMappable(cmap=cmap, norm=normalize)
sm.set_array([])  # 设置一个空数组用于标注

# 添加颜色映射对象的标注到图例
plt.colorbar(sm)

# 显示图形
plt.show()