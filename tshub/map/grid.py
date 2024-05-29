'''
@Author: WANG Maonan
@Date: 2024-05-29 15:23:55
@Description: 将 Map 划分为 Grid, 从而获得 Grid 内部的信息
@LastEditTime: 2024-05-29 16:18:27
'''
import numpy as np
from typing import Tuple, List
from dataclasses import dataclass, field
from scipy.interpolate import griddata as scipy_griddata

@dataclass
class GridInfo:
    lower_left: Tuple[float, float] = field(default_factory=tuple)
    upper_right: Tuple[float, float] = field(default_factory=tuple)
    resolution: float = 10.0
    x_min: float = None
    y_min: float = None
    x_max: float = None
    y_max: float = None
    data: List[Tuple[float, float, float]] = field(default_factory=list)
    grid_z: np.ndarray = field(default_factory=lambda: np.array([]))

    @classmethod
    def from_radio_map_txt(cls, file_path: str):
        """从 radio map 文件中读取数据

        Args:
            file_path (str): txt 文件的路径, 这里是 radio map 的数据
        """
        instance = cls()
        data = list()
        with open(file_path, 'r') as file:
            for line in file:
                if line.startswith('LOWER_LEFT'):
                    instance.lower_left = tuple(map(float, line.split()[1:]))
                elif line.startswith('UPPER_RIGHT'):
                    instance.upper_right = tuple(map(float, line.split()[1:]))
                elif line.startswith('RESOLUTION'):
                    instance.resolution = float(line.split()[1])
                elif line.startswith('BEGIN_DATA'):
                    break

            for line in file:
                if "END_DATA" in line:
                    break
                parts = line.split()
                coord = (float(parts[0]), float(parts[1]))
                value = np.nan if parts[2] == "N.C." else float(parts[2])
                data.append((*coord, value))

            instance.data = data.copy()

        # Create grid
        instance.create_grid()
        
        return instance
    
    def __repr__(self) -> str:
        return f'SNIR_{self.resolution}'

    def create_grid(self):
        """Organize data into a structured grid.
        """
        data_array = np.array(self.data)

        # Get the min and max coordinates for the grid
        self.x_min, self.y_min = np.min(data_array[:, :2], axis=0)
        self.x_max, self.y_max = np.max(data_array[:, :2], axis=0)

        # Calculate grid dimensions
        x_size = int((self.x_max - self.x_min) / self.resolution) + 1
        y_size = int((self.y_max - self.y_min) / self.resolution) + 1

        # Initialize the grid array with NaNs
        self.grid_z = np.full((y_size, x_size), np.nan)

        # Populate the grid with values
        for x, y, value in self.data:
            x_idx = int((x - self.x_min) / self.resolution)
            y_idx = int((y - self.y_min) / self.resolution)
            self.grid_z[y_idx, x_idx] = value

    def get_value_at_coordinate(self, x: float, y: float) -> float:
        """Get the value at the given coordinates.
        """
        # Calculate the indices
        x_idx = int((x - self.x_min) / self.resolution)
        y_idx = int((y - self.y_min) / self.resolution)

        # Check if the indices are within the grid bounds
        if 0 <= x_idx < self.grid_z.shape[1] and 0 <= y_idx < self.grid_z.shape[0]:
            return self.grid_z[y_idx, x_idx]
        else:
            return np.nan  # or some other value indicating out-of-bounds
    
    def get_features(self):
        return self