'''
@Author: WANG Maonan
@Date: 2023-11-13 21:25:42
@Description: 将 fig 转换为 array
@LastEditTime: 2023-11-13 21:29:34
'''
import numpy as np

def plt2arr(fig):
    """
    need to draw if figure is not drawn yet
    """
    fig.canvas.draw()
    rgba_buf = fig.canvas.buffer_rgba()
    (w,h) = fig.canvas.get_width_height()
    rgba_arr = np.frombuffer(rgba_buf, dtype=np.uint8).reshape((h,w,4))
    return rgba_arr