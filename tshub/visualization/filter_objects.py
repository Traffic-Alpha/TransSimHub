'''
@Author: WANG Maonan
@Date: 2023-11-12 21:56:57
@Description: 过滤感兴趣的物体
@LastEditTime: 2023-11-13 23:16:03
'''
import sumolib
from loguru import logger
from typing import List, Tuple, Dict, Any

def calculate_min_distance_polygon2polygon(
        center_object_shape:List[Tuple[float]], 
        other_object_shape:List[Tuple[float]]
    ) -> float:
    """Calculate the minimum distance from center_object_shape to other_object_shape.

    Args:
        center_object_shape (List[Tuple[float]]): Shape of the center object.
        other_object_shape (List[Tuple[float]]): Shape of the object to calculate distance to.
    """
    min_distance = float('inf')
    for center_point in center_object_shape:
        if len(other_object_shape) == 1:
            distance = sumolib.geomhelper.distance(
                        p1=center_point, 
                        p2=other_object_shape[0]
                    )
        else:
            distance = sumolib.geomhelper.distancePointToPolygon(
                        point=center_point, 
                        polygon=other_object_shape
                    )
        min_distance = min(min_distance, distance)
    return min_distance


def calculate_center(points: List[Tuple[float]]) -> tuple[float, float]:
    """计算 shape 的中心点

    Args:
        points (List[Tuple[float]]): 组成 shape 的坐标点，
            例如: [(x1,y1), (x2,y2), ..., (xn,yn)]

    Returns:
        tuple[float, float]: shape 的中心点的坐标
    """
    x_coords = [point[0] for point in points]
    y_coords = [point[1] for point in points]
    center_x = sum(x_coords) / len(x_coords)
    center_y = sum(y_coords) / len(y_coords)
    return (center_x, center_y)


def find_bounds(data):
    # 初始化 x_min, x_max, y_min, y_max 为 None
    x_min, x_max, y_min, y_max = None, None, None, None

    # 遍历字典中的每个键值对
    for key in data:
        # 遍历每个键值对中的 'shape' 列表
        for point in data[key]['shape']:
            # 解包坐标点
            x, y = point
            # 如果 x_min 是 None 或者 x 小于 x_min，更新 x_min
            if x_min is None or x < x_min:
                x_min = x
            # 如果 x_max 是 None 或者 x 大于 x_max，更新 x_max
            if x_max is None or x > x_max:
                x_max = x
            # 如果 y_min 是 None 或者 y 小于 y_min，更新 y_min
            if y_min is None or y < y_min:
                y_min = y
            # 如果 y_max 是 None 或者 y 大于 y_max，更新 y_max
            if y_max is None or y > y_max:
                y_max = y

    # 创建 x_range 和 y_range 列表
    x_range = [x_min, x_max]
    y_range = [y_min, y_max]

    # 返回 x_range 和 y_range
    return x_range, y_range



def filter_object(obs, focus_id:str=None, focus_type:str=None, focus_distance:float=None) -> Dict[str, Dict[str, Any]]:
    """
    Filters objects in the observations based on their distance to a focus object.

    The function calculates the minimum distance from each object in the observations to the focus object.
    It then filters out objects that are further away than a specified focus distance.

    Args:
        obs (dict): The observations containing the objects to filter. 
                    The dictionary is expected to have keys 'vehicle', 'edge', and 'node', 
                    each containing a dictionary of objects of that type, keyed by their id. 
                    Each object is expected to have a 'position' (for 'vehicle') or 'shape' (for 'edge' and 'node') attribute.

        focus_id (str, optional): The id of the focus object. If None, the function will return the original observations.

        focus_type (str, optional): The type of the focus object. 
                                    Can be 'vehicle', 'edge', 'node', or None. 
                                    If None, the function will return the original observations.

        focus_distance (float, optional): The maximum distance an object can be from the focus object to be included in the filtered observations. 
                                          If None, the function will return the original observations.

    Returns:
        dict: The filtered observations. The structure is the same as the input observations, 
              but only includes objects that are within the specified distance of the focus object.
    """
    valid_focus_types = [None, 'edge', 'node', 'vehicle']
    assert focus_type in valid_focus_types, f'focus_type can only be {valid_focus_types}, now is {focus_type}.'

    if (focus_id is None) or (focus_type is None) or (focus_distance is None):
        logger.warning(f'SIM: Since None in {focus_id}, {focus_type}, {focus_distance}, we render the global scenario.')
        x_range, y_range = find_bounds(obs['edge'])
        return obs, x_range, y_range
    
    # 获取坐标, 如果是 vehicle 就是 position, 其他的就是 shape
    if focus_type == 'vehicle':
        center_object_shape = obs[focus_type].get(focus_id, {'position': None})['position']
        if center_object_shape is not None:
            center_object_shape = [center_object_shape]
    else:
        center_object_shape = obs[focus_type].get(focus_id, {'shape': None})['shape']

    new_obs = {focus_type: {} for focus_type in valid_focus_types[1:]}

    if center_object_shape is None:
        x_range, y_range = None, None
    else:
        for object_type in valid_focus_types[1:]:
            for obj_id, obj_info in obs[object_type].items():
                obj_shape = [obj_info['position']] if object_type == 'vehicle' else obj_info['shape']
                min_distance = calculate_min_distance_polygon2polygon(center_object_shape, obj_shape)
                if min_distance < focus_distance:
                    new_obs[object_type][obj_id] =  obj_info
        
        # 计算 center_object_shape 的中心点
        center_point = calculate_center(center_object_shape)
        x_range = [center_point[0]-focus_distance/2, center_point[0]+focus_distance/2]
        y_range = [center_point[1]-focus_distance/2, center_point[1]+focus_distance/2]
    return new_obs, x_range, y_range