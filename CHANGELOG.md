<!--
 * @Author: WANG Maonan
 * @Date: 2023-08-23 17:15:09
 * @Description: All notable changes to this project.
 * @LastEditTime: 2023-08-31 11:47:54
-->
# Change Log

All notable changes to this project will be documented in this file. 
All text added must be human-readable. 
Copy and pasting the git commit messages is **NOT** enough. 

## [Unreleased] - XXXX-XX-XX
### Added
### Changed
### Deprecated
### Fixed
### Removed
### Security

<!-- v0.1 -->
## [v0.1] - 2023-08-23

### Added

- Initialized the project.
- Vehicle module:
  - Added `vehicle_builder.py` file: Provides methods to retrieve information and control all vehicles in the scene.
  - Added `vehicle.py` file: Defines the `VehicleInfo` class that represents information about a vehicle.
- Aircraft module:
  - Added `aircraft.py` file: Defines the `AircraftInfo` class that represents information about an aircraft.
  - Added `aircraft_builder.py` file: Provides methods to create and control aircraft.


<!-- v0.2 -->
## [v0.2] - 2023-08-25

### Added

- Added `generate_detectors.py` file in the `sumo_tools` module
  - `base_detectors.py`: Defines the information retrieval from intersections and the `generate_detector` method.
  - `e1_detectors.py`: Generates e1 detectors placed at a default distance of 2m from the traffic lights.
  - `e2_detectors.py`: Generates e2 detectors with a default length of 100m.
  - `e3_detectors.py`: Generates e3 detectors that cover turns.
- Added `sumo_infos` in the `sumo_tools` module to extract connections of traffic light signals.

### Changed

- Modified `init_log.py` in the `utils` section to store logs in a separate folder.
- Modified `get_abs_path.py` in the `utils` section to include the SIM identifier in the logs.


<!-- v0.3 -->
## [v0.3] - 2023-08-28

### Added

- Added traffic light module
  - `traffic_light_action_type.py`: Defines two types of traffic light control: "Choose Next Phase" and "Next or Not".
  - `traffic_light.py`: Defines the basic properties and methods of each traffic light.
  - `traffic_light_builder.py`: Initializes all traffic lights in a scene and defines interfaces for accessing information and control.
  - `choose_next_phase.py`: Defines the control method "Choose Next Phase".
  - `next_or_not.py`: Defines the control method "Next or Not".

### Changed

- Modified the vehicle module to no longer create multiple classes for the same vehicle.
  - Added `update_vehicle_feature`, which updates the current information of the vehicle at each step.
  - Added and improved different vehicle action types, including `lane` and `lane with continuous speed`.
  - Added attributes to the vehicle, including `action type` and `lane index`.

<!-- v0.4 -->
## [v0.4] - 2023-08-30

### Add

- Added four different aircraft action types:
  - `stationary.py`: The aircraft remains stationary at its initial position.
  - `horizontal_movement.py`: The aircraft can only move horizontally, with eight possible heading angles.
  - `vertical_movement.py`: The aircraft can only move vertically, with three possible heading values: up, stationary, and down.
  - `combined_movement.py`: The aircraft can move both upward and downward simultaneously, combining azimuth and pitch angles. There are a total of 40 combinations.

### Changed

- Added `base_builder.py` to standardize the interface between different builders:
  - `aircraft_builder.py`, `vehicle_builder.py`, `traffic_light_builder.py`
- Provided examples for vehicle, aircraft, and traffic light under the new builder:
  - `traffic_light_action`: `tls_choosenextphase.py` and `tls_nextornot.py`
  - `aircraft_actions`: `aircraft_combined.py`, `aircraft_horizontal.py`, `aircraft_stationary.py`, and `aircraft_vertical.py`
  - `vehicle_action`: `vehicle_lane.py` and `vehicle_lane_with_continuous_speed.py`

### Fixed

- In `traffic_light.py`, set `this_phase` to False before each update in `__update_this_phase()`. Previously, it would cause all `this_phase` values to be True.


<!-- v0.5 -->
## [v0.5] - 2023-08-31

### Add

- 添加 `tshub_env` module
  - `base_sumo_env.py`, 启动 SUMO 的仿真环境;
  - `tshub_env.py`, 整合 "Veh"（车辆）、"Air"（航空）和 "Traf"（信号灯），整体控制与获得信息
- 添加 `sumo_env` 在 `example` 里面
  - `single_junction`: 单路口环境
  - `three_junctions`: 三个路口的环境, 车辆 id 前面有 `ego` 表示需要控制的车辆，其余是背景车

### Changed

- `aircraft_builder.py`: 将 sumo 从 aircraft_inits 中单独拿出来, 这样 builder 的时候传入一次 sumo 即可
- 更新了 `utils` 中一系列的函数
  - `check_folder.py`, 检查文件夹是否存在, 如果不存在则进行创建;
  - `format_dict.py`, 格式化 dict, 用于 print 更好的显示;
  - `nested_dict_conversion.py`, 嵌套的 dict 转换;
  - `get_abs_path.py`, 相对路径转换为绝对路径;

### Fixed

- `base_aircraft_action.py` 修改 `new_position` 的类型, 将 tuple 修改为 list, 解决 TypeError 报错，TypeError: 'tuple' object does not support item assignment


<!-- v0.6 -->
## [v0.6] - 2023-09-02

### Add

- 在 `sumo_tools` 中添加 `generate_route.py` 模块, 用于快速给场景生成 route 文件
  - 主要的思路是 xx
  - 可以控制 ego 车辆和背景车辆的混合比例，以 ego 开头就是需要控制的车辆, 其他的车就是背景车, 只能获得 state, 无法进行控制
- 在 `sumo_tools` 中添加 `generate_add.py` 模块, 用于快速给场景生成 add 文件, 监测信号灯的状态变化
- 初始化文档的模块，使用 Sphinx 进行文档的书写
  - 书写 introduction 部分，介绍 
  - 书写 installation 部分，介绍如何安装

### Changed

- `setup.py`, 添加 `extras_require`, 添加额外的 doc 环境的支持

<!-- 添加生成 route 的模块, 添加整合生成 add 和 detector 的模块 -->

<!-- v0.5 -->
<!-- 将三个内容整合在一起，得到一个 base env -->
<!-- 添加 uml 框架图 -->
<!-- setup 的时候需要分模块进行安装, doc 的时候才需要安装 sphinx 库 -->

<!-- v0.3 -->
<!-- 添加 memory 模块 -->
<!-- 环境适配 gym 和 rllib -->

<!-- v0.5 -->
<!-- 添加 feature process 模块 -->