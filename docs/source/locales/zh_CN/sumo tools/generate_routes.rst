路网生成
===========================

路网（ rou 文件 ）是用于SUMO仿真的车流文件，这个工具可以用来批量的生成路网文件。

参数介绍
------------------

- **文件路径 sumo_net** (str): sumo net 路网的文件路径，用于指定生成路网存储的位置
- **时间间隔 interval** (List[float]): 时间的间隔，每段时间的持续时间（分钟），例如两段时间，[20, 30]，表示第一段时间为 20 分钟，第二段时间为 30 分钟
-  **车流密度 edge_flow_per_minute** Dict[str, List[float]]: 每个边 （ edge ） 每个时间段的车辆（ veh/min ）

.. code-block:: python

    {
        'edge_1': [10, 20],
        'edge_2': [20, 30],
    }

- **转向概率 edge_turndef** (Dict[str, List[float]]): 每一个路口，每一个时间间隔机动车转向 （ `connection` ）的概率

.. code-block:: python
    
    {
        'fromEdge1__toEdge1': [0.5, 0.5, 0.2],
        'fromEdge2__toEdge2': [0.2, 0.3, 0.4],
        'fromEdge3__toEdge3': [0.6, 0.1, 0.3],
    }

- **车辆类型 veh_type** (Dict[str, Dict[str, float]]): 定义不同的车辆类型

.. code-block:: python
    
    {
        'car_1': {'length':7, 'tau':1, 'color':'26, 188, 156', 'probability':0.7},
        'car_2': {'length':5, 'tau':1, 'color':'155, 89, 182', 'probability':0.3},
    }

- **trip 文件路径  output_trip** (str, optional):  生成的 .trip.xml 文件的路径， 默认是 'testflow.trip.xml'
- **turndef 文件路径  output_turndef** (str, optional): 生成的 .turndef.xml 文件的路径， 默认是 'testflow.turndefs.xml'
- **rou 文件路径 output_route** (str, optional): 生成的 .rou.xml 文件的路径， 默认是 'testflow.rou.xml'
- **车流平滑 interpolate_flow** (bool, optional): 是否对车流 （ flow ） 进行平滑， 默认是 `False`
- **转向平滑 interpolate_turndef** (bool, optional): 是否对转向概率 （ turndef ） 进行平滑, 默认是 `False`
- **车流随机 random_flow** (bool, optional): 控制车流出现的时间是否随机， 默认是 `True`
- **随机数种子 seed** (int, optional): 随机数种子, 控制使用 JTRROUTER 生成的 route 是一样的, 默认是 777


.. note::
    
 专向（ `connection` ）

 .. code-block:: python


       """
       For example, assume we  have a junction with one incoming road In1
       with 3 incoming lanes and 2 outgoing roads Out1 and Out2,
       having 2 and 3 outgoing lanes, respectively.

                   ___________________
            lane 0 _______     _______ lane 0
       Out2 lane 1 _______     _______ lane 1  In1
            lane 2 _______     _______ lane 2
                          | | |
                          | | |
                          | | |
                      lane 0 1
                           Out1

      Assume that lanes are connected as follows:
      - In1, lane 0 is connected to Out2, lane 0
      - In1, lane 1 is connected to Out2, lane 1
      - In1, lane 2 is connected to Out2, lane 2

      - In1, lane 1 is connected to Out1, lane 0
      - In1, lane 2 is connected to Out1, lane 1
      """