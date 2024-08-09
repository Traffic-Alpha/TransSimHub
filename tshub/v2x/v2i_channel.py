'''
@Author: WANG Maonan
@Date: 2024-08-09 11:30:10
@Description: V2I Channel Model
@LastEditTime: 2024-08-09 20:53:25
'''
import math
import numpy as np
from typing import List, Tuple
from .v2x_channel import V2XChannel

class V2IChannel(V2XChannel):
    """
    V2I (Vehicle-to-Infrastructure) channel model.
    """
    def __init__(self,BS_position: List[float], **kwargs) -> None:
        super().__init__(**kwargs)
        self.BS_position = BS_position # 基站位置 (2D)
        self.v2i_shadowing = np.random.normal(0, self.shadow_std)

    def get_channels_with_fastfading(
            self, 
            previous_position_obj: List[float], 
            current_position_obj: List[float],
        )->float:
        free_path_loss = self._get_path_loss(current_position_obj)
        shadowing = self._get_shadowing(previous_position_obj, current_position_obj)
        noise = np.random.normal(0, 1)
        return (free_path_loss + shadowing + noise)
    
    def get_received_power(
            self, 
            previous_position_obj: List[float], 
            current_position_obj: List[float],
            is_power_ms:bool = True
        )->float:
        channels_with_fastfading = self.get_channels_with_fastfading(
            previous_position_obj, current_position_obj
        )
    
        if is_power_ms: # ms->bs, 所以使用 power_ms 和 noise_figure_bs
            received_power = self.power_ms - channels_with_fastfading - self.noise_figure_bs
        else: # bs -> ms
            received_power = self.power_bs - channels_with_fastfading - self.noise_figure_ms
            
        return received_power
    
    def get_snr(
            self, 
            previous_position_obj: List[float], 
            current_position_obj: List[float],
            is_power_ms:bool = True
        )->float:
        received_power = self.get_received_power(
            previous_position_obj, current_position_obj,
            is_power_ms=is_power_ms,
        )

        noise_power_dbm = self.sig2_dB_ms if is_power_ms else self.sig2_dB_bs
        return 10*np.log10(V2XChannel.dbm2w(received_power)/V2XChannel.dbm2w(noise_power_dbm))
    
    # ---
    
    def _get_path_loss(self, current_position_obj: Tuple[float, float]):
        """
        Calculate the path loss to the base station (自由空间路径损耗).

        The path loss PL(d) in dB is calculated based on the distance d to the base station:
            - PL(d) = 20*log10(d) + 20*log10(f) + 20*log10(4pi/c) - antrenna_gain_ms - antrenna_gain_bs
            - where distance is the 3D distance to the base station.
        """
        distance = math.hypot(
            current_position_obj[0] - self.BS_position[0], 
            current_position_obj[1] - self.BS_position[1],
            self.h_bs - self.h_ms # 基站高度 - 车辆高度
        ) # 距离 m

        # 20*np.log10(4*np.pi/3e8) = -147.5582278139513
        return 20*np.log10(distance) + 20*np.log10(self.fc*1e9) - 147.5582278139513 - self.antrenna_gain_bs - self.antrenna_gain_ms

    def _get_shadowing(self, previous_position_obj: Tuple[float, float], current_position_obj: Tuple[float, float]) -> float:
        """Calculate the shadowing effect for multiple vehicles based on the change in distance.
        """
        # delta_distance 是两个时刻之间的距离, \Delta d = | d(P_RSU, P_Veh) - d(P_RSU, P_P_Veh)|
        delta_distance = abs(
            V2XChannel.calculate_distance(previous_position_obj, self.BS_position) - \
            V2XChannel.calculate_distance(current_position_obj, self.BS_position)
        )

        shadowing_rho = np.exp(-1*(delta_distance / self.decorrelation_distance))
        shadowing = shadowing_rho*self.v2i_shadowing + \
            np.sqrt(1 - shadowing_rho**2)*np.random.normal(0, self.shadow_std)
        
        return shadowing