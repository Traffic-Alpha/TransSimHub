'''
@Author: WANG Maonan
@Date: 2024-03-24 15:07:49
@Description: 分析 route 文件, 并进行可视化
@LastEditTime: 2024-03-24 15:35:32
'''
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET

def count_vehicles(root, edges, interval):
    """
    Count the number of vehicles within given time intervals that are on the specified edges.

    Parameters:
    root (Element): The root of the XML tree containing vehicle routes.
    edges (list): A list of edges to check against the vehicle routes.
    interval (int): The time interval for counting vehicles.

    Returns:
    dict: A dictionary with interval indices as keys and vehicle counts as values.
    """
    # Convert edges to a set for faster 'in' operation
    interval_counts = {}

    for vehicle in root.findall('vehicle'):
        route = vehicle.find('route')
        if (route is not None) and (edges in route.get('edges')):
            depart = float(vehicle.get('depart'))
            interval_index = int(depart // interval)
            if interval_index not in interval_counts:
                interval_counts[interval_index] = 0
            interval_counts[interval_index] += 1

    return interval_counts


def count_vehicles_for_multiple_edges(xml_path, edges_list, interval):
    """
    Count the number of vehicles for multiple sets of edges within given time intervals.

    Parameters:
    xml_path (str): The path to the XML file containing vehicle routes.
    edges_list (list): A list of lists, each containing edges to check against the vehicle routes.
    interval (int): The time interval for counting vehicles.

    Returns:
    dict: A dictionary with edges as keys and dictionaries of interval counts as values.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Use dictionary comprehension for cleaner code
    return {edges: count_vehicles(root, edges, interval) for edges in edges_list}


def plot_vehicle_counts(data, file_path):
    """
    Plot a line graph of vehicle counts over intervals for different sets of edges and save the plot.

    Parameters:
    data (dict): A dictionary with edges as keys and dictionaries of interval counts as values.
    file_path (str): The path to save the line graph image.
    """
    plt.figure(figsize=(10, 6))

    for edges, counts in data.items():
        # Sort the intervals and get corresponding counts
        intervals = sorted(counts.keys())
        counts = [counts[interval] for interval in intervals]
        plt.plot(intervals, counts, marker='o', label=edges)

    plt.xlabel('Interval')
    plt.ylabel('Vehicle Count')
    plt.title('Vehicle Counts Over Intervals')
    plt.legend()
    plt.grid(True)
    plt.savefig(file_path)
    plt.close()