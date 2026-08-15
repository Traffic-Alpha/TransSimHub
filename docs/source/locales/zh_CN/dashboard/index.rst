中观交通大屏
==================

TransSimHub 的第三条可视化路径。三种视图回答的是不同的问题：

.. list-table::
  :header-rows: 1

  * - 视图
    - 入口
    - 回答的问题
  * - 微观
    - ``TshubEnvironment.render(mode='sumo_gui')`` / ``use_gui=True``
    - 每一辆车在做什么（范围小）
  * - **中观**
    - ``tshub.visualization.meso``
    - **整个路网哪里在堵、怎么扩散**
  * - 空中 3D
    - ``Tshub3DEnvironment`` + ``sensor_config``
    - UAV / 车载 / 路口相机看到了什么

三者可以在同一次仿真里同时开启。


数据来源
~~~~~~~~~~~~~

大屏只吃 ``obs`` 里的三个 key，**不反向依赖环境**，所以任何拿得到这些数据的循环都能推给它：

- ``obs['lane_shape']`` —— 车道的静态几何（ ``is_map_builder_initialized=True`` ），用来画路网；
- ``obs['edge_state']`` —— 路段级动态状态（ ``is_edge_builder_initialized=True`` ），用来着色；
- ``obs['lane_state']`` —— 车道级动态状态（ ``is_lane_builder_initialized=True`` ），切到车道粒度时用。

详见 :doc:`../object/lane_edge`。


使用
~~~~~~~~~~~~~

.. code-block:: python

    from tshub.visualization.meso import DashboardServer, build_static_payload, build_frame_payload

    dashboard = DashboardServer(port=8910)
    url = dashboard.start()          # 后台线程, 不阻塞仿真

    obs = tshub_env.reset()
    static_payload = build_static_payload(obs)
    dashboard.set_static(static_payload)   # 路网几何, 只传一次

    while not done:
        obs, _, infos, done = tshub_env.step(actions={})
        dashboard.push(build_frame_payload(
            sim_time=infos['step_time'], obs=obs, static_payload=static_payload,
        ))

    dashboard.stop()

然后打开 ``url``\ （默认 http://127.0.0.1:8910 ）。
完整示例见
`examples/dashboard <https://github.com/Traffic-Alpha/TransSimHub/tree/main/examples/dashboard>`_。


大屏内容
~~~~~~~~~~~~~

- **路网拥堵图** —— Google Maps 风格。道路按 Google 的画法分三层绘制：
  **灰色路缘 + 白色路面 + 上面一条较窄的拥堵色带**\ （占路宽的 68%），
  所以路网整体读作「浅色底上的白色网络」，全图只有拥堵色带是饱和的；
  色带用 Google 交通图层的四档配色（停滞深红 / 缓行红 / 较慢橙 / 畅通绿）。
  底图按用地类型分层：水系、公园、树林、住宅 / 商业用地、学校医疗、停车场、建筑。
  可拖拽平移、滚轮缩放、悬停查看详情；左上角可在「路段」与「车道」粒度之间切换。

  .. warning::

     底图完全来自 ``poly_file``。不传 poly 文件的话，路网周围就是一片纯色 ——
     没有任何地物数据可画，换什么配色都没用。示例用 kowloon 场景正是因为它带
     完整的 poly（7000+ 个多边形，建筑 / 公园 / 树林 / 水系俱全）。
- **KPI** —— 平均车速（km/h）、全网畅通程度（%）、在网车辆数（含排队数）、拥堵路段占比；
- **Network breakdown** —— 四档路段的构成条（停滞 / 缓行 / 较慢 / 畅通各多少条），
  比单个平均值更能说明全网状况；
- **趋势** —— 畅通程度随时间的变化；
- **最拥堵路段** —— 每行给出路段、街道名、实际车速 / 限速、状态与排队数。
  排序用「延误影响 =（1 - 畅通程度）× 车辆数」，而不是单纯按车速升序 ——
  后者榜首会全是「只有一辆车停在红灯前」的小路段，并非真正的堵点；
- **UAV 回传** —— UAV 位置画在路网上，机载相机图像显示在侧栏，点击可全屏放大
  （放大后仍然实时更新）；同时标注这一帧 UAV 附近有多少车辆与路口
  （由 ``tshub.aircraft.aircraft_nearby.find_objects_near_aircraft`` 计算，
  距离在 XY 平面上算，忽略飞行高度）。

.. important::

   ``speed_relative``\ （拥堵指数）的方向是 **1 = 完全畅通，0 = 完全堵死**，
   很容易读反。因此大屏上不直接显示这个裸数字，而是换算成 km/h、百分比，
   以及 Stopped / Slow / Moderate / Free flow 这样的文字状态。

.. note::

   大屏界面是英文的。UAV 机载相机建议只挂俯拍的 ``aircraft_rgb``（正交俯视，
   看机身正下方的地面），并且用 ``preset='720P'`` 及以上 —— 更低的分辨率放到
   大屏侧栏里看不清路面。


实现说明
~~~~~~~~~~~~~

- 服务端只用标准库（ ``http.server`` + SSE），不引入 flask/fastapi；前端是手写的
  Canvas 渲染器，没有 vendored 任何 JS 库 —— SUMO 的坐标是笛卡尔米制而不是经纬度，
  用不上地图库。
- 每帧的拥堵值量化成 ``uint8`` 再 base64，一个 2000 边的路网每帧只有几 KB。
  量化往返误差不超过半个量化步长（约 0.002），对着色和排序没有影响。
- ``push()`` 永不阻塞仿真：每个浏览器一个有界队列，满了就丢最旧的帧。
  浏览器卡住或关掉都不会拖慢仿真。
