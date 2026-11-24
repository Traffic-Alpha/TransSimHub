<!--
 * @Author: WANG Maonan
 * @Date: 2023-08-23 11:03:31
 * @Description: ROADMAP 未来添加的功能, CHANGELOG 记录变动
 * @LastEditTime: 2026-11-24 14:40:26
-->
1. TranSimHub 核心代码优化
2. 单路口场景的搭建
   1. sumocfg 全部运行一遍，查看信号灯设计，道路 connection 是否有问题
   2. 单路口每个场景都渲染一遍，渲染不同的视角，测试渲染时间，然后保存图像（单帧+多帧GIF）
3. 多路口场景的搭建
   1. 首先确定下来多路口场景有哪些（carla，cityflow，osm，真实扫描的模型）
   2. 接着将多路口场景的卫星图片下载；
   3. 把选择到的多路口场景放在世界地图上面；
   4. 简化多路口场景里面的道路连接
   5. 看一下场景是否存在大量空的建筑物，没有道路连接（用最小矩形包裹起来）
   6. 测试一下多路口场景的速度，然后保存图像
4. 将上面所有的场景进行汇总，制作一个世界地图
   1. 保存每个场景的渲染图和卫星图像
   2. 每个场景的数据大小，渲染时间等总结为一个表格
5. 在 tls 中加入 connection, 需要指导每个 movement: (in_edge, out_edge)
6.  需要在仿真里面加入 person 的信息
   1. https://sumo.dlr.de/docs/TraCI/Person_Value_Retrieval.html
   2. https://sumo.dlr.de/docs/Simulation/Pedestrians.html
   3. https://sumo.dlr.de/docs/Netedit/editModesNetwork.html#crossings, 设置 crossing 的方式
7.  generate route 生成带有 person 的 route
   1. 写一下行人模块，可以获得环境中行人的相关信息
   2. 在有行人的环境下，训练一个强化学习，查看是否可以收敛
8.  map 里面加入 edge 和 node 等的信息, 有前后节点的信息, node 的坐标，可以使用 GNN 网络来处理
9.  创建一个 test 文件，在安装之后可以测试 package 是否安装正确
10. vehicle 加一个只有速度，但是没有换道的动作
11. 生成路网的时候，有以下要注意的（1）不可以有多功能车道；（2）要提取信息的道路不可以有行人
12. 关于 3D 可视化的部分
    1.  加入一些彩蛋的车辆,车的上面有名字(加一个自己名字, 再加一个对象的)
    2.  代码添加 __slot__