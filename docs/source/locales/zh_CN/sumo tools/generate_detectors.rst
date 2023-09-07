探测器生成
===========================

探测器 ( `detector` ) 在路口可以用于状态观测

参数介绍
------------------
- **文件路径  result_folder** (str)： 生成的探测器，将要保存到的文件夹
- **路口 tls_list** (List[str])： 包含需要摆放探测器的路口
- **探测器类型 detectors_list** (List, optional): 生成的探测器的类型，目前支持 ['e1', 'e1_internal', 'e2', 'e3'] 

探测器介绍
------------------

目前支持四种探测器类型，分别是 `e1` 、 `e1_internal` 、 `e2` 、 `e3`

- **e1** : 生成 E1 探测器, 每一个路口每一个 lane 都有一个探测器

  .. list-table::
    :header-rows: 1

    * - 参数
      - 描述
    * - tls_connection (Dict[str, List[List]])
      - 包括交通路口的信息
    * - output_file (str. optional)
      - 写入检测器的文件名，默认为 e1.add.xml
    * - results_file (str, optional)
      - 检测器写入的文件名，默认为 e1.output.xml
    * - distance_to_TLS (float, optional)
      - 探测器距离信号灯的位置, 默认 0.1 表示距离信号灯 0.1 m
    * - freq (int, optional)
      - 指定探测器的探测周期长度，默认是 60s 1次


- **e1_internal** : 生成 E1 Internal 探测器, 在交叉路口里面的 lane 设置探测器, 获得转向数据

  .. list-table::
    :header-rows: 1

    * - 参数
      - 描述
    * - tls_connection (Dict[str, List[List]])
      - 包括交通路口的信息
    * - output_file (str. optional)
      - 写入检测器的文件名，默认为 e1_internal.add.xml
    * - results_file (str, optional)
      - 检测器写入的文件名，默认为 e1_internal.output.xml
    * - distance_to_TLS (float, optional)
      - 探测器距离信号灯的位置, 默认 0.1 表示距离信号灯 0.1 m
    * - freq (int, optional)
      - 指定探测器的探测周期长度，默认是 60s 1次

- **e2** : 生成 E2 探测器, 每一个路口每一个 lane 都有一个探测器

  .. list-table::
    :header-rows: 1

    * - 参数
      - 描述
    * - tls_connection (Dict[str, List[List]])
      - 包括交通路口的信息
    * - output_file (str. optional)
      - 写入检测器的文件名，默认为 e2.add.xml
    * - results_file (str, optional)
      - 检测器写入的文件名，默认为 e2.output.xml
    * - detector_length (float, optional)
      - 设置 E2 探测器的覆盖长度
    * - distance_to_TLS (float, optional)
      -  E2 探测器探测的位置 (开始位置) 默认 -0.1m 是在道路的出口处.
    * - freq (int, optional)
      - 指定探测器的探测周期长度，默认是 60s 1次

- **e3** : 生成 E3 探测器, 每一个 connection 会有 E3 探测器

  .. list-table::
    :header-rows: 1

    * - 参数
      - 描述
    * - tls_connection (Dict[str, List[List]])
      - 包括交通路口的信息
    * - output_file (str. optional)
      - 写入检测器的文件名，默认为 e3.add.xml
    * - results_file (str, optional)
      - 检测器写入的文件名，默认为 e3.output.xml
    * - detector_length (float, optional)
      - 设置 E3 探测器的覆盖长度
    * - distance_to_TLS (float, optional)
      -  E3 探测器探测的位置 (开始位置) 默认 -0.1m 是在道路的出口处.
    * - freq (int, optional)
      - 指定探测器的探测周期长度，默认是 60s 1次

探测器生成例子
-----------------------

下面具体看一个探测器生成的例子， （ 完整代码见 `Generate Detectors Example <https://github.com/Traffic-Alpha/TransSimHub/tree/main/examples/sumo_tools/generate_tls_detectors.py>`_）
首先指定需要生成的路网文件

.. code-block:: python

    netfile_path = current_file_path("../sumo_env/three_junctions/env/3junctions.net.xml")


指定要生成的路口 id 和探测器保存的位置

.. code-block:: python

    g_detectors.generate_multiple_detectors(
    tls_list=['J1','J2','J3'], 
    result_folder=current_file_path("../sumo_env/three_junctions/detectors"),
    detectors_dict={'e1':dict(), 'e1_internal':dict(), 'e2':{'detector_length':30}, 'e3':dict()}
    )

生成探测器文件如下

.. code-block:: python
    <e1Detector file="e1_internal.output.xml" freq="60" friendlyPos="x" id="e1det_internal--J1---E4---E4_0---E0_0--r" lane=":J1_0_0" pos="3"/>
    <e1Detector file="e1_internal.output.xml" freq="60" friendlyPos="x" id="e1det_internal--J1---E4---E4_0--E9_0--s" lane=":J1_1_0" pos="3"/>
    ...

    <e1Detector file="e1.output.xml" freq="60" friendlyPos="x" id="e1det--J1---E4---E4_0--rs" lane="-E4_0" pos="71.9"/>
    <e1Detector file="e1.output.xml" freq="60" friendlyPos="x" id="e1det--J1---E4---E4_1--s" lane="-E4_1" pos="71.9"/>
    ...

    <laneAreaDetector file="e2.output.xml" freq="60" friendlyPos="x" id="e2det--J1---E4---E4_0--rs" lane="-E4_0" pos="43.800000000000004" length="30"/>
    <laneAreaDetector file="e2.output.xml" freq="60" friendlyPos="x" id="e2det--J1---E4---E4_1--s" lane="-E4_1" pos="43.800000000000004" length="30"/>
    ...

    <e3Detector id="e3det--J1---E4---E0--r" freq="60" file="e3.output.xml" openEntry="true">
        <detEntry lane="-E4_0" pos="-1"/>
        <detExit lane="-E0_0" pos="1"/>
    </e3Detector>
    <e3Detector id="e3det--J1---E4--E9--s" freq="60" file="e3.output.xml" openEntry="true">
        <detEntry lane="-E4_0" pos="-1"/>
        <detExit lane="E9_0" pos="1"/>
        <detEntry lane="-E4_1" pos="-1"/>
        <detExit lane="E9_1" pos="1"/>
        <detEntry lane="-E4_2" pos="-1"/>
        <detExit lane="E9_2" pos="1"/>
    </e3Detector>
    ...


.. image:: ../../../_static/sumo_tools/detector_add.png
   :alt: detector_sumo_example

