<!--
 * @Author: WANG Maonan
 * @Date: 2023-08-23 17:15:09
 * @Description: All notable changes to this project.
 * @LastEditTime: 2023-09-01 14:15:55
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

### Changelog

#### Added

- Added `tshub_env` module
  - `base_sumo_env.py`: Initializes the SUMO simulation environment.
  - `tshub_env.py`: Integrates "Veh" (vehicles), "Air" (aircraft), and "Traf" (traffic lights) for overall control and information retrieval.
- Added `sumo_env` in `example`
  - `single_junction`: Environment for a single junction.
  - `three_junctions`: Environment for three junctions, including ego vehicle and background vehicles.

#### Changed

- `aircraft_builder.py`: Separated SUMO initialization from `aircraft_inits` and now pass SUMO once during the builder process.
- Updated a series of utility functions in `utils`
  - `check_folder.py`: Checks if a folder exists and creates it if it doesn't.
  - `format_dict.py`: Formats a dictionary for better display when printing.
  - `nested_dict_conversion.py`: Converts nested dictionaries.
  - `get_abs_path.py`: Converts relative paths to absolute paths.

#### Fixed

- Modified the type of `new_position` in `base_aircraft_action.py` from tuple to list to resolve a TypeError: 'tuple' object does not support item assignment.

<!-- v0.6 -->
## [v0.6] - 2023-09-02

### Add

- 在 `sumo_tools` 中添加 `generate_route.py` 模块, 用于快速给场景生成 route 文件
  - 主要的思路是 xx
  - 可以控制 ego 车辆和背景车辆的混合比例，以 ego 开头就是需要控制的车辆, 其他的车就是背景车, 只能获得 state, 无法进行控制
  - 可以设置默认车辆的速度是 9m/s, 约等于 32.4km/h
- 在 `sumo_tools` 中添加 `generate_add.py` 模块, 用于快速给场景生成 add 文件, 监测信号灯的状态变化
- 初始化文档的模块，使用 Sphinx 进行文档的书写
  - `doc` 支持 `readthedocs` 文档, [Transsimhub Documentation](https://transsimhub.readthedocs.io/)
  - 书写 introduction 部分，介绍 TransSimHub 仓库
  - 书写 installation 部分，介绍如何安装 TransSimHub
- `utils` 中添加 `normalization_dict.py`, 作用是对字典中的 key 进行归一化, 使其和为 1

### Changed

- `setup.py`, 添加 `extras_require`, 添加额外的 doc 环境的支持
- `init_log.py` 支持写入调用的文件和函数
- vehicle 的属性中加入 vehicle type, 用于区分 ego vehicle 和 background vehicle.

### Fixed

- `dict_to_str` 考虑了 np.array 的格式, 无法直接进行转换, 故添加了类型判断和转换 TypeError: Object of type ndarray is not JSON serializable

<!-- 添加生成 route 的模块, 添加整合生成 add 和 detector 的模块 -->

<!-- v0.5 -->
<!-- 将三个内容整合在一起，得到一个 base env -->
<!-- 添加 uml 框架图 -->
<!-- setup 的时候需要分模块进行安装, doc 的时候才需要安装 sphinx 库 -->
<!-- log 可以设置 level -->
<!-- v0.3 -->
<!-- 添加 memory 模块 -->
<!-- 环境适配 gym 和 rllib -->

<!-- v0.5 -->
<!-- 添加 feature process 模块 -->