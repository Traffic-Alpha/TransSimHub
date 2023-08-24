<!--
 * @Author: WANG Maonan
 * @Date: 2023-08-23 11:03:31
 * @Description: ROADMAP, 记录开发路线图
 * @LastEditTime: 2023-08-24 17:19:42
-->
1. setup.py 要区分 env 的安装，带有 rl 训练环境的安装
2. 流量生成的模块，默认是控制所有车，获得所有车的信息，可以在 memory 部分自己加一个模块进行过滤
3. 将 gym 替换为新的库
4. 创建一个多路口的环境
5. 这里 change lane 会影响影响后续车辆行驶，比如强制到左转车道，就无法直行了，且会出现不一定换道成功的情况，不一定换道成功需要后续进行判断, 这里需要在 env 或者 
6. controller 模块里面进行判断
7. 加入信号灯的控制和提取信息的模块
8. 加入 memory 模块，用于对 vehicle, aircraft 和 traffic signal 的信息进行汇总
9. 会只 ULM 图，来总结项目模块之间的关联
10. 可以自动生成多个路口的 add 文件，这样有（1）生成 detector, (2) add (3) route

## 关于整体文件结构

现在我正在使用 Python 写一个联合仿真的库，主要是联合仿真 vehicle, traffic signal light 和 aircraft，他有以下特点：

1. 通过 SUMO 来获得和控制 vehicle, traffic signal light，我们会通过 traci.subscribe 来订阅要获得的信息。
2. aircraft 是自己写程序控制，控制的信息包含「三维的位置 x,y,z」，朝向角 heading，和速度。我们可以给出新的 heading 和速度
3. 代码包含，ENV Module，Control Module 和 Feature Module
4. 我们通过 vehicle_builder, tsc_builder, aircraft_builder，用于分别提取信息和进行控制。
5. 提取的信息会放在 memeory 里面，接着通过消化 memory 的结果转换为想要的数据结构
6. 环境接口要适配强化学习的接口需求，例如包括 step，reset 等

请根据上面的提示，给出这个 Python 库的文件结构，使用树的形式给出。

## 关于 vehcile 的文件结构

现在正在写一个基于 SUMO 的 Python 的项目，用于获取和控制车辆。其中包含一个 vehicle 的部分，里面包含五个文件和作用：

- vehicle.py, 这里定义了每一辆车的 dataclass，例如包含 laneid, position, speed, edges
- vehicles.py，由多个 vehicle 组成，包含场景中所有的 vehicle
- vehicle_data.py，获得场景中所有车辆的信息，可以使用 traci.vehicle.getAllSubscriptionResults() 获得所有定阅车辆的信息
- vehicle_control.py，输入是一个字典，key 是车辆的 ID，value 是每个车辆的动作，使用 traci 中的 slowDown(vehID, speed, duration) 来改变车辆速度，使用 changeLane(vehID, laneIndex, duration) 来改变所在车道
- vehicle_builder.py，整合 vehicle_data 和 vehicle_control，提供方法来获得场景中所有车辆的信息和控制所有车辆。且在每一个 simulationStep，需要订阅新来的车辆，traci.vehicle.subscribe(veh_id)

请给出上面每个文件的详细代码和注释。如果你觉得哪里可以优化，可以按照你的思路。

## 写出关于 aircraft 的代码

现在请写出一个 Python 的项目，是关于 aircraft 的控制和信息获取。这个项目包含下面两个文件：

- aircraft.py: 创建飞行器的属性，是 dataclass 类，飞行器的信息包含 3D position, 3D speed, 3D Heading, communication range
- aircraft_builder.py: 实例化多个 aircraft，包含返回 aircraft 的信息，对 aircraft 进行控制（给出 speed 和 heading，自动计算 position）

## 计算 aircraft 覆盖的范围

现在有一个 Python 代码，用于创建 aircraft：

```python
from dataclasses import dataclass
from typing import Tuple

@dataclass
class AircraftInfo:
    id: str
    position: tuple[float, float, float]
    speed: tuple[float, float, float]
    heading: tuple[float, float, float]
    communication_range: float

    @classmethod
    def create(cls, 
            id:str, 
            position: Tuple[float, float, float], 
            speed: float, 
            heading: Tuple[float, float, float], 
            communication_range: float
        ):
        """
        创建 AircraftInfo 实例。

        Args:
            id (str): aircraft ID。
            position (Tuple[float, float, float]): aircraft 的位置坐标。
            speed (float): aircraft 的速度。
            heading (Tuple[float, float, float]): aircraft 的航向。
            communication_range (float): aircraft 的通信范围。

        Returns:
            AircraftInfo: 创建的 AircraftInfo 实例。
        """
        return cls(id, position, speed, heading, communication_range)
```

这里 aircraft 是在三维，请根据他的高度（position）和 communication_range 计算出他在地面的中心点和覆盖半径。

提示：根据勾股定理计算地面的覆盖半径，由于高度是 position[2]，斜边是 communication_range，那么地面覆盖半径就是 sqrt(communication_range，那么地面覆盖半径就是**2 - position[2]**2)

要求：请一步一步给出你是如何计算的。

- 需要根据通讯范围，计算出到地面的半径
- 地面的车辆，可以根据到中心点的距离，计算是否超出了通讯范围