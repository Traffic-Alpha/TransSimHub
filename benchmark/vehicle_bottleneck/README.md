<!--
 * @Author: WANG Maonan
 * @Date: 2023-12-16 22:11:40
 * @Description: 控制 ego vehicle 的速度, 来减缓 bottleneck 处的拥堵程度
 * @LastEditTime: 2023-12-18 19:09:18
-->

veh_wrapper 主要包含以下的内容
- 速度的控制
- writer
- 仿真环境的预热
- 在 PettingZooWrapper 的时候，设置 use_mask=True, 来确保 agent 的数量是可以动态变化的
- self.agents 需要是可以变化的