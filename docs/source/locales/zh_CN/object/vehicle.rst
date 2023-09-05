机动车
=========
Vehicle（机动车）可用于在 `SUMO` 中仿真机动车，例如：自动驾驶汽车、卡车、小轿车等。
关于 Vehicle 的代码例子 `TransSimHub Vehicle Example <https://github.com/Traffic-Alpha/TransSimHub/tree/main/examples/vehicles>`_
下面介绍 Vehicle 的 状态（` state`）， 动作类型（ `action type`）和使用例子:

状态定义
-----------
- **机动车 id** (str):场景中每一个 vehicle 的唯一 ID，用于区分不同的 vehicle
- **动作类型 action_type** (str): vehicle的动作控制类型, 目前支持 `keep_lane`, `slow_down`, `change_lane_left`, `change_lane_right`
- **位置 position** (Tuple[float]):vehicle所在的位置
- **速度 speed** (float): vehicle当前车速
- **路 road_id** (str): vehicle 行驶道路的 ID, 场景中每条道路有唯一 ID
- **车道 lane_id** (str): vehicle 所在车道的 ID, 
- **边 edges** (list[str]): vehicle 已经经过的边
- **下一个相位 next_tls** (List[str]): vehicle 将通过的交通信号灯的 ID
- **等待时间 waiting_time** (float): vehicle 在交通路口的等待时间

动作类型
-----------

1. **lane**：  仅选择车道，vehicle 的速度由规则判断

  .. list-table::
    :header-rows: 1 

    * - 参数
      - 描述
    * - keep_lane（str）
      - vehicle保持当前车道，改变vehicle的速度, 速度增加3，但小于最高限速（15）
    * - slow_down (str)
      - vehicle保持当前车道，改变vehicle的速度, vehicle速度减少3，但要高于最低限速（2）
    * - change_lane_left (str)
      - vehicle向左侧变道，改变vehicle的速度, vehicle速度减少2，但高于最低限速（2）
    * - change_lane_left (str)
      - vehicle向右侧变道，改变vehicle的速度, vehicle速度减少2，但高于最低限速（2）

2. **lane_continuous_speed**: 改变车道，并且可以连续控制速度

  .. list-table::
    :header-rows: 1 

    * - 参数 target_speed (float)
      - 参数 lane_change (int)
      - 描述
    * - 目标车速
      - keep_lane
      - 保持当前车道 
    * - 目标车速
      - change_lane_left
      - 向左侧变道 
    * - 目标车速
      - change_lane_right
      - 向右侧变道


  .. note::
    1. vehicle分为可自动驾驶车（ego 车）和正常车辆，正常车辆只能获得观测信息不可控制，ego车可控。
    2. 在 `lane_continuous_speed` 中虽然给定target_speed，但仿真时控制器可能会给出更高或更低的速度


Vehicle 控制例子
-----------------------
下面具体看一个 Vehicle 的控制的例子（完整代码见 `TransSimHub Vehicle Lane Control <https://github.com/Traffic-Alpha/TransSimHub/blob/main/examples/vehicles/vehicle_action/vehicle_lane.py>`_）。
下面是初始化 vehicle 的参数， 载入的车流文件中包含每一个 vehicle 的动作类型，初始位置，速度等。

 .. code-block:: python

    <vehicle id="gsndj_s4__0.0" type="car_2" depart="9.22" departLane="random">
        <route edges="gsndj_s4 gsndj_s5"/>
    </vehicle>


接着根据参数我们在场景中初始化 vehicle，这个 `conn` 传入 `traci` 的连接：

 .. code-block:: python

    from tshub.vehicle.vehicle_builder import VehicleBuilder
    scene_vehicles = VehicleBuilder(sumo=conn, action_type='lane')  


接着我们通过 `get_objects_infos` 来得到 `vehicle` 的属性：

 .. code-block:: python

    data = scene_vehicles.get_objects_infos()


返回的属性如下所示，可以看到包含每一个 vehicle 的位置，速度等：

 .. code-block:: python

  {
    "gsndj_s4__0.0": {
        "id": "gsndj_s4__0.0",
        "action_type": "lane",
        "position": [
            1217.0713040366447,
            1370.0102791296881
        ],
        "speed": 0,
        "road_id": "gsndj_s4",
        "lane_id": "gsndj_s4_2",
        "lane_index": 2,
        "edges": [],
        "waiting_time": 0,
        "next_tls": []
    }
  }


这里我们设置的动作类型是 `lane` ，也就是只能控制vehicle的换道， 下面是控制的例子：
  
  .. code-block:: python

    gsndj_s4__0.0    Lane Change: 0  Target Speed: None

    scene_vehicles.control_objects(actions)

  
如果我们将 `if_sumo_visualization` 设置为 `True`，可以看到仿真画面：
