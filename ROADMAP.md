<!--
 * @Author: WANG Maonan
 * @Date: 2023-08-23 11:03:31
 * @Description: ROADMAP, 记录开发路线图
 * @LastEditTime: 2024-07-21 04:10:34
-->
1. 总结 Project 各个模块之间的关系
2. gitpage 部署一个静态的页面进行展示, https://cityflow-project.github.io/index.html
3. 加入地图信息的 builder
   1. https://sumo.dlr.de/docs/Networks/Import/OpenStreetMap.html
4. 在 tls 中加入 connection, 需要指导每个 movement: (in_edge, out_edge)
5. 需要在仿真里面加入 person 的信息
   1. https://sumo.dlr.de/docs/TraCI/Person_Value_Retrieval.html
   2. https://sumo.dlr.de/docs/Simulation/Pedestrians.html
   3. https://www.youtube.com/watch?v=Mh4WnY4KY4Y
   4. https://sumo.dlr.de/docs/Netedit/editModesNetwork.html#crossings, 设置 crossing 的方式
   5. https://sumo.dlr.de/docs/IntermodalRouting.html, 联乘
6. vehicle 一种新的 action，根据给定的路径进行行驶
7. 联运和出租车文档，
   1. https://sumo.dlr.de/docs/IntermodalRouting.html
   2. https://sumo.dlr.de/docs/Simulation/Taxi.html
8.  generate route 生成带有 person 的 route
   1. 写一下行人模块，可以获得环境中行人的相关信息
   2. 在有行人的环境下，训练一个强化学习，查看是否可以收敛
9.  map 里面加入 edge 和 node 等的信息, 有前后节点的信息, node 的坐标，可以使用 GNN 网络来处理
10. 创建一个 test 文件，在安装之后可以测试 package 是否安装正确
11. 加一个基站的仿真, 可以获得基站范围内所有内容的信息（可以添加一个关于 wrapper 的内容，包含一些信道的 wrapper）
12. vehicle 加一个只有速度，但是没有换道的动作
14. 生成路网的时候，有以下要注意的（1）不可以有多功能车道；（2）要提取信息的道路不可以有行人
15. 关于 3D 可视化的部分
    1.  对照 metadrive 里面的内容，将 render pipline 上面的代码上传
    2.  把 camera type 可以通过参数传入
    3.  scene_sync.py 中 _sync 的代码需要重新好好写一下，现在代码长度有一些长
    4.  scene_sync.py 中 reset 部分也是需要重新来写一下
    5.  重写所有的 camera 和 sensor，对代码进行整理
    6.  检查 reset 的时候场景的 camera 是否都清理干净了
    7.  可以将 sensor 的图像分别保存下来，后面可以转换为 gif
    8.  写一个文档，描述所有的图像，目前有，车辆的摄像头（6 * 2，6 个方向，每个方向有无 mask），路口的摄像头（4 * 2 * 2，四个角度，每个角度前后，前后里面有无 mask），飞行器（3 * 2, 跟随车辆，绕行，上下，每一个都有无 mask），共有 34 个 gif。
    9.  录制对应的 tshub3d 和 sumo 的画面，一共有 2 个，所以就是 34+2=36 个 gif 需要制作
    10. 加入一些彩蛋的车辆,车的上面有名字(加一个自己名字, 再加一个对象的)
    11. 把 smarts 里面的 sensors 全部过一遍，有图像的全部添加进去
    12. 加入测试的模式（此时开启可视化），其他时候不需要进行可视化
    13. tshub_render.py 部分一些工具函数可以写到 base_render 部分，简化一个文件的行数
    14. tshub_env3d.py 部分有 TODO 需要修改，然后加入 logger 对一些步骤进行说明
    15. 完整过一遍 3D 的代码，确认没有多余的，代码顺便进行结构的整理
    16. setup 的时候加入素材文件，加入 all 可以一次性安装(单独有一个 3d 的安装)
    17. 关于是否可以开启 3D 可视化，可以在 showbase_instace 的 init 的里面进行修改
    18. 代码添加 __slot__
   
---