'''
@Author: WANG Maonan
@Date: 2023-12-16 22:36:27
@Description: Utils for veh env wrapper
@LastEditTime: 2023-12-18 01:40:36
'''
import numpy as np

from typing import List, Dict, Tuple, Union

def analyze_traffic(state, lane_ids):
    # Initialize the dictionaries to store the results
    lane_statistics = {
        lane_id: {
            'vehicle_count': 0, 
            'speeds': [], 
            'waiting_times': [], 
            'accumulated_waiting_times': []
        } for lane_id in lane_ids
    }
    ego_statistics = {}

    # Process the state data
    for vehicle in state.values():
        lane_id = vehicle['lane_id']
        if lane_id in lane_statistics:
            stats = lane_statistics[lane_id]
            stats['vehicle_count'] += 1
            stats['speeds'].append(vehicle['speed'])
            stats['waiting_times'].append(vehicle['waiting_time'])
            stats['accumulated_waiting_times'].append(vehicle['accumulated_waiting_time'])

        # Check for 'ego' vehicle type and store the required information
        if vehicle['vehicle_type'] == 'ego':
            ego_statistics[vehicle['id']] = [
                vehicle['speed'], 
                vehicle['position'], 
                vehicle['road_id'], 
                vehicle['lane_index']
            ]

    # Calculate statistics for each lane using numpy for efficiency
    for lane_id, stats in lane_statistics.items():
        speeds = np.array(stats['speeds'])
        waiting_times = np.array(stats['waiting_times'])
        accumulated_waiting_times = np.array(stats['accumulated_waiting_times'])
        vehicle_count = stats['vehicle_count']

        # Calculate statistics if there are vehicles; otherwise, use zeros
        if vehicle_count > 0:
            lane_statistics[lane_id] = [
                vehicle_count,
                np.mean(speeds), np.max(speeds), np.min(speeds),
                np.mean(waiting_times), np.max(waiting_times), np.min(waiting_times),
                np.mean(accumulated_waiting_times), np.max(accumulated_waiting_times), np.min(accumulated_waiting_times)
            ]
        else:
            lane_statistics[lane_id] = [0] * 10

    # Convert the lane statistics to the desired output format
    lane_statistics = {lane_id: stats for lane_id, stats in lane_statistics.items()}

    return lane_statistics, ego_statistics


def check_prefix(a:str, B:List[str]) -> bool:
    """检查 B 中元素是否有以 a 开头的

    Args:
        a (str): lane_id
        B (List[str]): bottle_neck ids

    Returns:
        bool: 返回 lane_id 是否是 bottleneck
    """
    return any(a.startswith(prefix) for prefix in B)


def count_bottleneck_vehicles(lane_statistics, bottle_necks) -> int:
    """统计 bottleneck 处车辆的个数
    """
    veh_num = 0
    for lane_id, lane_info in lane_statistics.items():
        if check_prefix(lane_id, bottle_necks):
            veh_num += lane_info[0]
    return veh_num


def calculate_congestion(vehicles:int, length:float, num_lane:int) -> float:
    """计算 bottle neck 的占有率, 我们假设一辆车算上车间距是 10m, 那么一段路的。占有率是
        占有率 = 车辆数/(车道长度*车道数/10)
    于是可以根据占有率计算拥堵系数为:
        拥堵程度 = min(占有率, 1)

    Args:
        vehicles (int): 在 bottle neck 处车辆的数量
        length (float): bottle neck 的长度, 单位是 m
        num_lane (int): bottle neck 的车道数

    Returns:
        float: 拥堵系数 in (0,1)
    """
    capacity_used = vehicles/(length*num_lane/10) # 占有率
    congestion_level = min(capacity_used, 1)  # Ensuring congestion level does not exceed 100%
    return congestion_level


def calculate_speed(congestion_level: float, speed:int) -> float:
    """根据拥堵程度来计算车辆的速度

    Args:
        congestion_level (float): 拥堵的程度, 通过 calculate_congestion 计算得到
        speed (int): 车辆当前的速度

    Returns:
        float: 车辆新的速度
    """
    if congestion_level>0.2:
        speed = speed * (1 - congestion_level)
        speed = max(speed, 1)
    else:
        speed = -1 # 不控制速度
    return speed


def one_hot_encode(value, unique_values):
    """Create an array with zeros and set the corresponding index to 1
    """
    one_hot = np.zeros(len(unique_values))
    index = unique_values.index(value)
    one_hot[index] = 1
    return one_hot.tolist()


def euclidean_distance(point1, point2):
    # Convert points to numpy arrays
    point1 = np.array(point1)
    point2 = np.array(point2)
    
    # Calculate the Euclidean distance
    distance = np.linalg.norm(point1 - point2)
    return distance


def compute_ego_vehicle_features(
        ego_statistics:Dict[str, List[Union[float, str, Tuple[int]]]], 
        lane_statistics:Dict[str, List[float]], 
        unique_edges:List[str],
        edge_lane_num:Dict[str, int],
        bottle_neck_positions:Tuple[float]
    ) -> Dict[str, List[float]]:
    """计算每一个 ego vehicle 的特征

    Args:
        ego_statistics (Dict[str, List[Union[float, str, Tuple[int]]]]): ego vehicle 的信息
        lane_statistics (Dict[str, List[float]]): 路网的信息
        unique_edges (List[str]): 所有考虑的 edge
        edge_lane_num (Dict[str, int]): 每一个 edge 对应的车道
        bottle_neck_positions (Tuple[float]): bottle neck 的坐标
    """
    feature_vectors = {}

    for ego_id, ego_info in ego_statistics.items():
        # Extract ego vehicle information
        speed, position, edge_id, lane_index = ego_info

        # Note: 只有 ego vehicle 在 unique_edges 才会得到他的 state 并对其进行控制
        if edge_id in unique_edges:
            # Normalize speed by dividing by 15
            normalized_speed = speed / 15.0

            # One-hot encode edge_id and lane_index
            edge_id_one_hot = one_hot_encode(edge_id, unique_edges)
            lane_index_one_hot = one_hot_encode(lane_index, list(range(edge_lane_num.get(edge_id,0))))

            # Initialize a list to hold all lane statistics
            all_lane_stats = []

            # Iterate over all possible lanes to get their statistics
            for _, lane_info in lane_statistics.items():
                # Get the lane statistics and append only the first 4 values
                all_lane_stats += [_i/15 for _i in lane_info[:4]]
            
            # Calculate the distance between ego vehicle and bottle neck
            distance = euclidean_distance(position, bottle_neck_positions)
            normalized_distance = distance/1000 # Normalize distance
            
            # Combine the features into a single vector
            feature_vector = [normalized_speed, normalized_distance] \
                + edge_id_one_hot + lane_index_one_hot \
                + all_lane_stats
            
            # Assign the feature vector to the corresponding ego vehicle
            feature_vectors[ego_id] = feature_vector

    return feature_vectors