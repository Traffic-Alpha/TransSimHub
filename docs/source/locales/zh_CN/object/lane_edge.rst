车道与路段（中观交通状态）
==============================

Lane（车道）与 Edge（路段）模块提供 **全路网** 的交通状态，是中观视图的数据来源。
它们回答的是「哪里在堵」，而不是「每一辆车在做什么」，因此不需要精确到车辆。
关于使用的例子详细见
`TransSimHub Lane Example <https://github.com/Traffic-Alpha/TransSimHub/tree/main/examples/lane>`_
与 `TransSimHub Edge Example <https://github.com/Traffic-Alpha/TransSimHub/tree/main/examples/edge>`_。

.. note::

   注意区分两个都叫 lane 的东西：

   - ``obs['lane_shape']`` 是车道的 **静态几何**\ （多边形形状），来自 :doc:`../object/index` 中的 map；
   - ``obs['lane_state']`` 是车道的 **动态交通状态**\ （速度、占有率、排队），来自这里。

   两者用 ``lane_id`` 关联。中观大屏就是把后者的拥堵指数涂到前者的多边形上。


状态定义
~~~~~~~~~~~~~

车道（ ``obs['lane_state']`` ）与路段（ ``obs['edge_state']`` ）的字段基本一致：

- **id** (str): 车道 / 路段的唯一 ID
- **edge_id** (str, 仅车道): 车道所属路段的 ID
- **lane_ids** (List[str], 仅路段): 路段包含的车道 ID，用于向车道级下钻
- **length** (float): 长度，单位是米（m）
- **max_speed** (float): 限速，单位是 m/s。路段的限速由其车道推出（ ``traci.edge`` 没有 ``getMaxSpeed`` ）
- **street_name** (str, 仅路段): 街道名，只有 OSM 路网才有
- **mean_speed** (float): 最近一步的平均速度（m/s）。空车道时 SUMO 返回的就是限速本身
- **occupancy** (float): 最近一步的占有率（0~1）
- **halting_number** (int): 最近一步的停车数（速度小于 0.1 m/s 的车辆数）
- **vehicle_count** (int): 最近一步的车辆数
- **speed_relative** (float): **拥堵指数**，等于 ``mean_speed / max_speed``，截断到 [0, 1]。
  1 表示自由流，0 表示完全停死。与 SUMO ``meandata`` 输出的 ``speedRelative`` 是同一个量


两个粒度的分工
~~~~~~~~~~~~~~~~~~~

- **路段级**\ （ ``edge_state`` ）由 SUMO 自己聚合，数量少（一个三路口场景是 20 个路段
  对 60 条车道），用来驱动路网着色；
- **车道级**\ （ ``lane_state`` ）数量大，在点开某个路段看明细时才需要。它能看到路段级
  看不到的差异 —— 例如某个路段整体拥堵指数是 0.16，下钻后是 ``1.00 | 0.00 | 0.03``，
  即一条车道完全畅通、另两条堵死。

这与 SUMO ``meandata`` 里 ``edgeData`` / ``laneData`` 的分工是一致的。


开销
~~~~~~~~~~~~~

车道与路段的集合在仿真过程中是不变的，因此两个 builder 都在创建时一次性完成订阅，
之后每一步只需要一次 ``getAllSubscriptionResults`` 就能拿到全网数据。
开销是 O(车道数)，**与车辆数无关** —— 这正是中观视图能在大路网上跑得动的原因。

默认跳过路口内部（以 ``:`` 开头）的车道与路段，需要时传 ``with_internal=True``。


使用例子
~~~~~~~~~~~~~

在 ``TshubEnvironment`` 中打开对应的开关即可：

.. code-block:: python

    from tshub.tshub_env.tshub_env import TshubEnvironment

    tshub_env = TshubEnvironment(
        sumo_cfg=sumo_cfg,
        net_file=net_file,
        is_map_builder_initialized=True,   # obs['lane_shape'], 路网几何
        is_lane_builder_initialized=True,  # obs['lane_state'], 车道级交通状态
        is_edge_builder_initialized=True,  # obs['edge_state'], 路段级交通状态
    )

    obs = tshub_env.reset()
    while not done:
        obs, _, _, done = tshub_env.step(actions={})
        # 最堵的三个路段
        worst = sorted(obs['edge_state'].items(), key=lambda kv: kv[1]['speed_relative'])[:3]

把这些数据推给 :doc:`../dashboard/index` 就得到实时的中观交通大屏。
