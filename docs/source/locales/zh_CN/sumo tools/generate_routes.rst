路网生成
===========================

路网（ rou 文件 ）是用于SUMO仿真的车流文件，这个工具可以用来批量的生成路网文件， 路网生成的代码例子 `TransSimHub Generate Route Example <https://github.com/Traffic-Alpha/TransSimHub/tree/main/examples/sumo_tools/generate_route>`_

参数介绍
------------------

- **文件路径 sumo_net** (str): sumo net 路网的文件路径，用于指定生成车流所在路网
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
    
 转向 （ `connection` ）

 .. code-block:: python


       """
       例如，假设我们有一个与一条传入道路的交汇处 In1
       有 3 三条进入路， 2 条出路 Out1 和 Out2，
       分别有 2 条和 3 条出口车道

                   ___________________
            lane 0 _______     _______ lane 0
       Out2 lane 1 _______     _______ lane 1  In1
            lane 2 _______     _______ lane 2
                          | | |
                          | | |
                          | | |
                      lane 0 1
                           Out1

      
        假设车道连接如下：
      - In1，通道 0 连接到 Out2，通道0
      - In1，通道 1 连接到 Out2，通道 1
      - In1，通道 2 连接到 Out2，通道 2

      - In1，通道 1 连接到 Out1，通道 0
      - In1，通道 2 连接到 Out1，通道 1
      """

路网生成例子
-----------------------

下面具体看一个路网生成的例子， （ 完整代码见 `Generate Route Example <https://github.com/Traffic-Alpha/TransSimHub/tree/main/examples/sumo_tools/generate_routes.py>`_）

首先要指定路网 （ `NET` ） 文件

.. code-block:: python

    sumo_net = current_file_path("../sumo_env/three_junctions/env/3junctions.net.xml")

设定时间间隔和每段时间间隔中每分钟的机动车的数量

.. code-block:: python

    interval=[5,10,15], 
    edge_flow_per_minute={
        'E0': [15, 15, 15],
        '-E3': [15, 15, 15],
        '-E9': [7, 7, 7],
        '-E4': [7, 7, 7],
        '-E5': [3, 3, 3],
        '-E8': [3, 3, 3],
        '-E6': [3, 3, 3],
        '-E7': [3, 3, 3]
    }, # 每分钟每个 edge 有多少车

之后要设定转向概率，表示每个时间间隔中，车行驶的不同 connect 的概率

.. code-block:: python

        edge_turndef={
        '-E9__E4': [0.7, 0.7, 0.8],
        '-E9__-E0': [0.1, 0.1, 0.1],
    }

设定车的类型，表示路网中车的种类， `propability` 表示生成的车中，这种类型的车的概率

.. code-block:: python

    veh_type={
        'ego': {'color':'26, 188, 156', 'probability':0.3},
        'background': {'color':'155, 89, 182', 'speed':15, 'probability':0.7},
    },

指定生成的 `trip` 、 `turndef` 、 `route` 文件的路径

.. code-block:: python

    output_trip=current_file_path('./testflow.trip.xml'),
    output_turndef=current_file_path('./testflow.turndefs.xml'),
    output_route=current_file_path('./testflow.rou.xml'),

是否需要平滑车流量

.. code-block:: python

    interpolate_flow=False,
    interpolate_turndef=False,

生成ROU文件如下

.. code-block:: python
 
  <vType id="background" length="7.00" maxSpeed="15.00" color="155,89,182" tau="1.0"/>
    <vehicle id="-E9__0__background.0" type="background" depart="0.84" departLane="random">
        <route edges="-E9 E4"/>
    </vehicle>
    <vehicle id="E0__0__background.0" type="background" depart="3.58" departLane="random">
        <route edges="E0 E4"/>
    </vehicle>
    <vType id="ego" length="7.00" maxSpeed="17.00" color="26,188,156" tau="1.0"/>
    <vehicle id="-E4__0__ego.0" type="ego" depart="4.16" departLane="random">
        <route edges="-E4 -E0"/>
    </vehicle>
    ...