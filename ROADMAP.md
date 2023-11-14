<!--
 * @Author: WANG Maonan
 * @Date: 2023-08-23 11:03:31
 * @Description: ROADMAP, 记录开发路线图
 * @LastEditTime: 2023-11-13 18:04:05
-->
1. 总结 Project 各个模块之间的关系
2. gitpage 部署一个静态的页面进行展示, https://cityflow-project.github.io/index.html
3. 加入地图信息的 builder
   1. https://sumo.dlr.de/docs/Networks/Import/OpenStreetMap.html
4. 在 tls 中加入 connection, 需要指导每个 movement: (in_edge, out_edge)
5. 场景的两种 render 模式
6. 需要在仿真厘米加入 person 的信息
   1. https://sumo.dlr.de/docs/TraCI/Person_Value_Retrieval.html
7. vehicle 一种新的 action，根据给定的路径进行行驶