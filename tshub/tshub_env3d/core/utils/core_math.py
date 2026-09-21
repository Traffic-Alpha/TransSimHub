'''
@Author: WANG Maonan
@Date: 2024-07-03 17:41:09
@Description: 渲染器无关的数学工具 (SMARTS 派生, 只保留 tshub3d 实际用到的部分).

谁在用:
- core/state/scene_builder : vec_2d / vec_to_radians / calculate_center_point
- core/utils/coordinates   : fast_quaternion_from_angle / yaw_from_quaternion / radians_to_vec
- scene/road_network       : lerp / sign / signed_dist_to_line / min_angles_difference_signed
                             / fast_quaternion_from_angle / vec_to_radians
@LastEditTime: 2026-08-18
'''
import math
import numpy as np


def yaw_from_quaternion(quaternion) -> float:
    """Converts a quaternion to the yaw value.
    Args:
      quaternion (np.ndarray): np.array([x, y, z, w])
    Returns:
      float: A angle in radians.
    """
    assert len(quaternion) == 4, f"len({quaternion}) != 4"
    siny_cosp = 2 * (quaternion[0] * quaternion[1] + quaternion[3] * quaternion[2])
    cosy_cosp = (
        quaternion[3] ** 2
        + quaternion[0] ** 2
        - quaternion[1] ** 2
        - quaternion[2] ** 2
    )
    yaw = np.arctan2(siny_cosp, cosy_cosp)
    return yaw


def fast_quaternion_from_angle(angle: float) -> np.ndarray:
    """Converts a float to a quaternion.
    Args:
      angle: An angle in radians.
    Returns:
      (np.ndarray): np.array([x, y, z, w])
    """

    half_angle = angle * 0.5
    return np.array([0, 0, math.sin(half_angle), math.cos(half_angle)])


def signed_dist_to_line(point, line_point, line_dir_vec) -> float:
    """Computes the signed distance to a directed line
    The signed of the distance is:

      - negative if point is on the right of the line
      - positive if point is on the left of the line

    ..code-block:: python

        >>> import numpy as np
        >>> signed_dist_to_line(np.array([2, 0]), np.array([0, 0]), np.array([0, 1.]))
        -2.0
        >>> signed_dist_to_line(np.array([-1.5, 0]), np.array([0, 0]), np.array([0, 1.]))
        1.5
    """
    p = vec_2d(point)
    p1 = line_point
    p2 = line_point + line_dir_vec

    u = abs(
        line_dir_vec[1] * p[0] - line_dir_vec[0] * p[1] + p2[0] * p1[1] - p2[1] * p1[0]
    )
    d = u / np.linalg.norm(line_dir_vec)

    line_normal = np.array([-line_dir_vec[1], line_dir_vec[0]])
    _sign = np.sign(np.dot(p - p1, line_normal))
    return d * _sign


def vec_2d(v) -> np.ndarray:
    """Converts a higher order vector to a 2D vector.
    """
    assert len(v) >= 2
    return np.array(v[:2])


def sign(x) -> int:
    """Finds the sign of a numeric type.
    Args:
        x: A signed numeric type
    Returns:
        The sign [-1|1] of the input number
    """

    return 1 - (x < 0) * 2


def lerp(a, b, p):
    """Linear interpolation between a and b with p
    .. math:: a * (1.0 - p) + b * p
    Args:
        a, b: interpolated values
        p: [0..1] float describing the weight of a to b
    """

    assert 0 <= p and p <= 1

    return a * (1.0 - p) + b * p


def radians_to_vec(radians) -> np.ndarray:
    """Convert a radian value to a unit directional vector. 0 rad relates to [0x, 1y] with
    counter-clockwise rotation.
    """
    # +y = 0 rad.
    angle = (radians + math.pi * 0.5) % (2 * math.pi)
    return np.array((math.cos(angle), math.sin(angle)))


def vec_to_radians(v) -> float:
    """Converts a vector to a radian value. [0x,+y] is 0 rad with counter-clockwise rotation.
    """
    # See: https://stackoverflow.com/a/15130471
    assert len(v) == 2, f"Vector must be 2D: {repr(v)}"

    x, y = v
    r = math.atan2(abs(y), abs(x))

    # Adjust angle based on quadrant where +y = 0 rad.
    # Standard quadrants
    #    +y
    #   2 | 1
    # -x - - - +x
    #   3 | 4
    #    -y
    if x < 0:
        if y < 0:
            return (r + 0.5 * math.pi) % (2 * math.pi)  # quad 3
        return (0.5 * math.pi - r) % (2 * math.pi)  # quad 2
    elif y < 0:
        return (1.5 * math.pi - r) % (2 * math.pi)  # quad 4
    return (r - 0.5 * math.pi) % (2 * math.pi)  # quad 1


def min_angles_difference_signed(first, second) -> float:
    """The minimum signed difference between angles(radians)."""
    return ((first - second) + math.pi) % (2 * math.pi) - math.pi


def calculate_center_point(points):
    # 计算所有点的 x 坐标和 y 坐标的平均值
    x_coords = [p[0] for p in points]
    y_coords = [p[1] for p in points]
    center_x = sum(x_coords) / len(points)
    center_y = sum(y_coords) / len(points)
    return center_x, center_y