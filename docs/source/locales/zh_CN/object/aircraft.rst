.. _object:

Aircraft
===========

状态定义
-----------

- 飞行器类型: ID

- 位置: 三维数据，表示飞行器现在所在的位置

- 速度: 一维数据，表示飞行器飞行的速度（水平面）

- heading: 三维数据，表示飞行器的飞行角度

- 通信距离: 一维数据，表示飞行器的通信能力


动作定义
-----------
 1. **Stationary**: 在固定位置保持不动
 2. **HorizontalMovement**: 在固定的高度，只能在水平方向移动
  - Speed: float, 连续控制
  - Heading: int, 这里输入是 heading index, 平面内被分为 8 个 heading 角度
 
 3. **VerticalMovement**: 只能改变高度，水平方向无法移动
   - Speed: float, 连续控制
   - Heading: int, 这里输入是 heading index, 共有三种情况, (1) 向上; (2) 向下; (3) 平稳

 4. **CombinedMovement**: 可以同时改变高度和水平方向移动，但是动作空间是离散的
   - Speed: float, 
   - Heading: int, 水平可移动角度 AZIMUTHS = [0, 45, 90, 135, 180, 225, 270, 315]，俯仰角 ELEVATIONS = [-90, -45, 0, 45, 90]
.. code-block:: py
   :caption: aircraft action
   :emphasize-lines: 0
   :linenos:

    actions = {
            "a1": (1, 1),
            "a2": (10, 2),
             }

- 飞行器ID
- 速度
- heading_index

.. note:: 
  AZIMUTHS
        - 0 度：向右飞行: ->
        - 45 度：右上方飞行: ↗
        - 90 度：向上飞行: ↑
        - 135 度：左上方飞行: ↖
        - 180 度：向左飞行: <-
        - 225 度：左下方飞行: ↙
        - 270 度：向下飞行: ↓
        - 315 度：右下方飞行: ↘