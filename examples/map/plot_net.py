'''
@Author: WANG Maonan
@Date: 2023-11-12 12:51:49
@Description: 绘制 net 路网
@LastEditTime: 2023-11-12 14:03:00
'''
import sumolib
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

from tshub.utils.get_abs_path import get_abs_path
path_convert = get_abs_path(__file__)


def plotNet(net):
    net = sumolib.net.readNet(net)
    shapes = [] # shape 的坐标
    c = [] # 每一个 shape 的颜色
    w = 1 # 每一个 shape 的宽度
    ls = [] # shape 的样式

    # 绘制 lane
    for e in net._edges: # 获得所有的 edge
        for _lane in e._lanes: # 获取每一个 edge 所有的 lane
            shapes.append(sumolib.geomhelper.line2boundary(_lane.getShape(), _lane.getWidth())) # 获得每一个 lane 的 shape
            c.append('gray')
            ls.append('-')
            # sumolib.geomhelper.line2boundary(_lane.getShape(), _lane.getWidth())

    # 绘制 node
    for _node in net.getNodes():
        print(_node.getType())
        if _node.getType() != 'dead_end': # 这里看一下还有哪些 type
            _shape = _node.getShape()
            shapes.append(_shape+[_shape[0]]) # 确保首尾相连
            c.append('b')
            ls.append('--')

    line_segments = LineCollection(shapes, linewidths=w, colors=c, linestyles=ls)
    ax = plt.gca()
    ax.add_collection(line_segments)
    ax.set_xmargin(0.1)
    ax.set_ymargin(0.1)
    ax.autoscale_view(True, True, True)
    plt.show()

if __name__ == '__main__':
    net_file = path_convert("../sumo_env/osm_berlin/env/berlin.net.xml")
    plotNet(net=net_file)