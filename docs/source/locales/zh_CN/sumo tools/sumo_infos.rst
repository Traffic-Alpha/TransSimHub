信息获取
===========================
该工具主要是为了快速获取 sumo 仿真中的一些信息

功能介绍
------------------

- **边信息获取 get_in_outgoing** ： 用于获取某个 edge 的 in 和 out 的车道的信息，参数信息如下：

  .. list-table::
    :header-rows: 1

    * - 参数
      - 描述
    * - net (sumolib.net.Net)
      - 路网对象
    * - edge_id (str)
      - 查询的 edge_id


返回的格式如下：

.. code-block:: python

        {
        'In': {
            '161701303#10': [
                {'fromLane': 'gsndj_n7_0', 'toLane': '161701303#10_0', 'direction': 'r'},
                {'fromLane': 'gsndj_n7_1', 'toLane': '161701303#10_1', 'direction': 'r'}
            ],
            'gsndj_n6': [
                {'fromLane': 'gsndj_n7_1', 'toLane': 'gsndj_n6_1', 'direction': 's'},
                {'fromLane': 'gsndj_n7_2', 'toLane': 'gsndj_n6_2', 'direction': 's'}
            ],
            '29257863#5': [
                {'fromLane': 'gsndj_n7_3', 'toLane': '29257863#5_2', 'direction': 'l'}
            ]
        },
        'Out': {
            ...
                }
        }

- **获得路口连接 get_tls_connections** ： 获得路口(有信号灯控制的)的所有连接, 参数信息如下

  .. list-table::
    :header-rows: 1

    * - 参数
      - 描述
    * - tls_list (List)
      - 信号灯 id, 例如 ['0', '1', '2']

返回的格式如下：

.. code-block:: python

        Returns:
            Dict[List]: 返回每个 tls lane 的情况, 样例数据如下所示:

        {
            'tlsID_1':[
                [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length],
                [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length],
                ...
            ],
            'tlsID_2':[
                [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length],
                [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length],
                ...
            ],
            ...
        }
        """

- **获取交通灯ID get_tlsID_list** ： 获得路网中所有的交通灯的 id

  .. list-table::
    :header-rows: 1

    * - 参数
      - 描述
    * - network_file (str)
      - network 文件所在的路径

返回的格式如下：

.. code-block:: python

    Returns:
        list: tls id 组成的列表


工具使用样例
-----------------------
下面看一个边信息获取的例子（完整代码见 `TransSimHub Get Edge Info <https://github.com/Traffic-Alpha/TransSimHub/blob/main/examples//sumo_tools/sumo_infos/get_edge_info.py>`_）
首先输入路网信息

.. code-block:: python

    sumo_net = current_file_path("../../sumo_env/three_junctions/env/3junctions.net.xml")
    net = sumolib.net.readNet(sumo_net) # 读取 sumo net

获取 edge 信息：

.. code-block:: python

    edge_info = get_in_outgoing(net=net, edge_id='-E9')

获取结果如下所示：

.. code-block:: python
    
    {
    "In": {},
    "Out": {
        "E1": [
            {
                "fromLane": "-E9_0",
                "toLane": "E1_0",
                "direction": "r"
            }
        ],
        "E4": [
            {
                "fromLane": "-E9_0",
                "toLane": "E4_0",
                "direction": "s"
            },
            {
                "fromLane": "-E9_1",
                "toLane": "E4_1",
                "direction": "s"
            },
            {
                "fromLane": "-E9_2",
                "toLane": "E4_2",
                "direction": "s"
            }
        ],
        "-E0": [
            {
                "fromLane": "-E9_2",
                "toLane": "-E0_2",
                "direction": "l"
            }
        ]
      }
    }

