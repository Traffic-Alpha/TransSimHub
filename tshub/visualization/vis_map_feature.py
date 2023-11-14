'''
@Author: WANG Maonan
@Date: 2023-11-12 16:20:15
@Description: 对地图元素的可视化
@LastEditTime: 2023-11-12 22:50:08
'''
from matplotlib.lines import Line2D

def plot_map_feature(ax, map_edges, map_nodes) -> None:
    # Draw edges
    for _, edge_info in map_edges.items():
        edge_shape = edge_info.get('shape')
        for i in range(len(edge_shape)):
            x_values = [edge_shape[i - 1][0], edge_shape[i][0]]
            y_values = [edge_shape[i - 1][1], edge_shape[i][1]]
            line = Line2D(x_values, y_values, linewidth=1, color='grey', linestyle='-')
            ax.add_line(line)
    
    # Draw nodes
    for _, node_info in map_nodes.items():
        node_shape = node_info.get('shape')
        for i in range(len(node_shape)):
            x_values = [node_shape[i - 1][0], node_shape[i][0]]
            y_values = [node_shape[i - 1][1], node_shape[i][1]]
            line = Line2D(x_values, y_values, linewidth=3, color='grey', linestyle='--')
            ax.add_line(line)

