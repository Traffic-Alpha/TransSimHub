<!--
 * @Author: WANG Maonan
 * @Date: 2024-08-10 21:34:15
 * @Description: Control Ego Vehicles and Traffic Signal Lights
 * @LastEditTime: 2024-08-11 18:38:26
-->
混合车流的环境，且可以同时控制信号灯和自动驾驶车辆

- 动作设计
  - 车辆: 控制加速和减速 (-3, 0, +3)
  - 信号灯: Choose Next Phase, 可以在所有可行的相位里面进行选择