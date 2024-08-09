'''
@Author: WANG Maonan
@Date: 2024-08-09 11:40:50
@Description: V2V Channel Model
@LastEditTime: 2024-08-09 23:06:42
'''
import math
import numpy as np
from loguru import logger
from typing import List, Tuple

from .v2x_channel import V2XChannel

class V2VChannel(V2XChannel):
    """
    V2V (Vehicle-to-Vehicle) channel model.
    """
    def __init__(self, **kwargs) -> None:
        super().__init__(
            h_bs=1.5, h_ms=1.5,
            decorrelation_distance=10, shadow_std=3, **kwargs
        )
        self.v2v_shadowing = np.random.normal(0, self.shadow_std)
        self.distance = None

    def get_channels_with_fastfading(
            self, 
            # 车辆 A 的位置
            previous_position_obj_A: List[float], 
            current_position_obj_A: List[float],
            # 车辆 B 的位置
            previous_position_obj_B: List[float], 
            current_position_obj_B: List[float],
        )->float:
        free_path_loss = self._get_path_loss(current_position_obj_A, current_position_obj_B)

        shadowing = self._get_shadowing(
            previous_position_obj_A, current_position_obj_A,
            previous_position_obj_B, current_position_obj_B
        )
        noise = np.random.normal(0, 1)
        return (free_path_loss + shadowing + noise)
    
    def get_received_power(
            self, 
            # 车辆 A 的位置
            previous_position_obj_A: List[float], 
            current_position_obj_A: List[float],
            # 车辆 B 的位置
            previous_position_obj_B: List[float], 
            current_position_obj_B: List[float],
            is_ms_transmit:bool = True, # 是否是 ms 作为发送, V2X
            is_ms_received:bool = True # 是否是 ms 作为接收, X2V
        )->float:
        channels_with_fastfading = self.get_channels_with_fastfading(
            previous_position_obj_A, current_position_obj_A,
            previous_position_obj_B, current_position_obj_B
        )

        noise_figure = self.noise_figure_ms if is_ms_received else self.noise_figure_bs
        if is_ms_transmit: # ms->bs/ms, 所以使用 power_ms
            received_power = self.power_ms - channels_with_fastfading - noise_figure
        else: # bs -> ms
            received_power = self.power_bs - channels_with_fastfading - noise_figure
            
        return received_power
    
    def get_snr(
            self, 
            # 车辆 A 的位置
            previous_position_obj_A: List[float], 
            current_position_obj_A: List[float],
            # 车辆 B 的位置
            previous_position_obj_B: List[float], 
            current_position_obj_B: List[float],
            is_ms_transmit:bool = True, # 是否是 ms 作为发送, V2X
            is_ms_received:bool = True # 是否是 ms 作为接收, X2V
        )->float:
        if is_ms_transmit and is_ms_received:
            logger.info('SIM: Calculate **V2V** SNR')
        elif is_ms_transmit and not is_ms_received:
            logger.info('SIM: Calculate **V2I** SNR')
        elif not is_ms_transmit and is_ms_received:
            logger.info('SIM: Calculate **I2V** SNR')
        else:
            raise ValueError("Invalid combination of transmission and reception for SNR calculation.")

        received_power = self.get_received_power(
            previous_position_obj_A, current_position_obj_A,
            previous_position_obj_B, current_position_obj_B,
            is_ms_transmit=is_ms_transmit,
            is_ms_received=is_ms_received,
        )

        noise_power_dbm = self.sig2_dB_ms if is_ms_transmit else self.sig2_dB_bs
        return 10*np.log10(V2XChannel.dbm2w(received_power)/V2XChannel.dbm2w(noise_power_dbm))
    
    def _get_path_loss(self, position_A:List[float], position_B:List[float]):
        """
        Calculate the path loss between two positions.

        The path loss PL(d) in dB is calculated based on the distance d between the transmitter and receiver:
        For LOS (Line of Sight):
            1. PL(d) = 22.7 * log10(d) + 41 + 20 * log10(fc/5) for d > 3m
            2. PL(d) = 22.7 * log10(3) + 41 + 20 * log10(fc/5) for d <= 3m, 小于 3 的时候距离就是 3

        For NLOS (Non-Line of Sight):
            - PL(d) = PL_Los(d_a) + 20 - 12.5 * n_j + 10 * n_j * log10(d_b) + 3 * log10(fc/5)
            - where n_j is the environment factor, d_a and d_b are the distances.
        """
        # Calculate Euclidean distance
        self.distance = math.hypot(
            position_A[0] - position_B[0], 
            position_A[1] - position_B[1]
        ) + 0.001 # 计算两个点的距离
        
        # breakpoint distance, which defines a boundary between different propagation loss behaviors.
        d_bp = 4 * (self.h_bs - 1) * (self.h_ms - 1) * self.fc * (10 ** 9) / (3 * 10 ** 8)

        def PL_Los(d):
            # Path loss for LOS
            if d <= 3:
                return 22.7 * np.log10(3) + 41 + 20 * np.log10(self.fc / 5)
            else:
                if d < d_bp:
                    return 22.7 * np.log10(d) + 41 + 20 * np.log10(self.fc / 5)
                else:
                    return (40.0 * np.log10(d) + 9.45 - 17.3 * np.log10(self.h_bs) -
                            17.3 * np.log10(self.h_ms) + 2.7 * np.log10(self.fc / 5))

        def PL_NLos(d_a, d_b):
            # Path loss for NLOS
            n_j = max(2.8 - 0.0024 * d_b, 1.84)
            return PL_Los(d_a) + 20 - 12.5 * n_j + 10 * n_j * np.log10(d_b) + 3 * np.log10(self.fc / 5)

        # Determine if the path is LOS or NLOS
        if min(position_A[0] - position_B[0], position_A[1] - position_B[1]) < 7:
            PL = PL_Los(self.distance)
        else:
            PL = min(PL_NLos(position_A[0], position_B[1]), PL_NLos(position_A[1], position_B[0]))
        return PL

    def _get_shadowing(
            self, 
            previous_position_obj_A: Tuple[float, float], 
            current_position_obj_A: Tuple[float, float],
            previous_position_obj_B: Tuple[float, float], 
            current_position_obj_B: Tuple[float, float],
        ) -> float:
        """Calculate the shadowing effect for multiple vehicles based on the change in distance.
        """
        # delta_distance 是两个时刻之间的距离, \Delta d = | d(P_VehA, P_VehB) - d(P_VehA, P_P_VehB)|
        delta_distance = abs(
            V2XChannel.calculate_distance(previous_position_obj_A, previous_position_obj_B) - \
            V2XChannel.calculate_distance(current_position_obj_A, current_position_obj_B)
        )

        shadowing_rho = np.exp(-1*(delta_distance / self.decorrelation_distance))
        shadowing = shadowing_rho*self.v2v_shadowing + \
            np.sqrt(1 - shadowing_rho**2)*np.random.normal(0, self.shadow_std)
        
        return shadowing