<!--
 * @Author: WANG Maonan
 * @Date: 2023-08-23 17:15:09
 * @Description: All notable changes to this project.
 * @LastEditTime: 2023-11-02 14:55:01
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

<!-- v0.9 -->
## [v0.9] - 2023-11-02

### Added

- Added environment for vehicle control
  - Introduced [Vehicle Speed Scenario](./benchmark/sumo_envs/veh_speed/), which is accomplished by controlling vehicle speed.
- Added [plot_reward_curves.py](./tshub/utils/plot_reward_curves.py) in utils, for plotting reward curve with standard deviation from log files.
- Added examples of multi-agents for traffic signal control.
  - Introduced environment [Multi-Traffic Signal Control](./benchmark/sumo_envs/multi_junctions_tsc/), which includes $3$ traffic signals.
  - Added multi-traffic signal control environment in `TsHub`, see [Multi-Agent TSC Env](./benchmark/traffic_light/multi_agents/env_utils/).
  - Provided examples of `MAPPO` algorithm, controlling multiple traffic signals. Detailed algorithm can be found at [MAPPO Traffic Signal Control](./benchmark/traffic_light/multi_agents/mappo_models/).
- Added introduction to traffic signal control based on reinforcement learning, [RL for TSC](./benchmark/traffic_light/).

### Changed

- Unified the connection method of `from_edge` and `direction` to `f"{from_edge}--{direction}"`.
- Updated doc description about the new state of traffic light, `fromEdge_toEdge`.
- Updated the rule-based method in single agent to adapt to the new connection method of `from_edge` and `direction`.

<!-- v0.8 -->
## [v0.8] - 2023-09-26

### Added

- Added support for `map` to retrieve properties of different polygons
  - Added `polygon.py` to define the properties of a polygon
  - Added `map_builder.py` to initialize static information in the scene, constructing types and shapes of all polygons based on `*.poly.xml` and `*.osm` files
- Added examples about `map`
  - Created `get_poly_info.py` to retrieve properties of polygons in the map
  - Developed `plot_poly_shape.py` to visualize information in the map
- Introduced a utility function `osm_build.py` to convert from `osm` to `sumo net`
- Documented the process of creating the environment from `osm` to the map used in experiments
  - Export the required area from [openstreetmap](https://www.openstreetmap.org/)
  - Run `osm_build.py` to generate `*.net.xml` and `*.poly.xml`, as demonstrated in the `osm_build.py` example in the `sumo_tools` directory of the `example` folder
  - [Optionally] Add background images
  - Run `generate_detectors.py` to create detectors
  - Run `generate_routes.py` to generate traffic flows
- Modified `tshub` to support the static information `map builder`
  - Added an example `tshub_env_map.py` to demonstrate how to access environment information in `env`


### Changed

- Added `custom_update_cover_radius` to `aircraft.py` to allow users to customize the update of `cover_radius` based on `position` and `communication_range`
  - Updated the default `update_cover_radius` in `aircraft.py` to support parameter input and return `cover_radius`
  - Updated the creation of `aircraft` in `aircraft_builder.py`
  - Added an example `aircraft_custom_update_cover_radius.py` in the `example` folder to illustrate how to customize `custom_update_cover_radius`
- Added `color` to `aircraft.py` to allow users to customize the color of the coverage radius circle

### Fixed

- Modified the addition of polygons in `aircraft.py` to ensure they are displayed in white color without altering the original image colors.

<!-- v0.7 -->
## [v0.7] - 2023-09-22

### Added

- Add "status description," "action design," and "program examples" to the following three objects:
  - `aircraft`, `vehicle`, `traffic lights`
- Add Chinese documentation:
  - TransSimHub scene creation, including signal light output, detector generation, and traffic flow generation
  - TransSimHub Object, introducing the three basic components of `TransSimHub`: aircraft, vehicle, and traffic lights
  - Add examples of scene combinations, integrating the usage of all three components: signal light control scene, aircraft control scene
  - Add an example of using RL to control traffic lights

### Changed

- `traffic_light.py`:
  - Add additional attributes:
    - Add `this_phase_index` in the traffic light data class (int)
    - Add `last_step_vehicle_id_list` in the traffic light data class (List(str)). Through the vehicle ID, we can calculate the waiting time at the intersection.
- `aircraft.py`:
  - Add the `aircraft type` attribute to handle different types of aircraft differently.
  - Set `setLineWidth` to width 3 to optimize the visualization effect of aircraft.
- `traffic_light_builder.py`:
  - Modify `process_detector_data` to support processing list data types and merge them.

### Fixed

- Resolve the issue where `vehicle` cannot retrieve `next_tls` when using `libsumo` [vehicle.py](https://github.com/Traffic-Alpha/TransSimHub/blob/main/tshub/vehicle/vehicle.py#L97).
- In the `aircraft example`, fix the issue where `get_aircraft_state.py` does not pass `sumo` and cannot obtain `aircraft info`.


<!-- v0.6 -->
## [v0.6] - 2023-09-01

### Added

- Added `generate_route.py` module in `sumo_tools` for quickly generating route files for scenarios.
  - `generate_trip.py`: Generates *.trip.xml files based on the number of entering vehicles (veh/min) for each time period. Allows control over the mixture ratio of ego vehicles and background vehicles. The default maximum speed is 17 m/s, equivalent to 61.2 km/h.
  - `generate_turn_def.py`: Generates *.turndefs.xml files based on the turning probabilities for each time period.
  - `interpolation` module: Provides interpolation for smooth changes in flows or turndefs.
- Added `generate_add.py` module in `sumo_tools` for quickly generating add files to monitor changes in traffic signal states.
  - See [SUMO Simulation Output](https://sumo.dlr.de/docs/Simulation/Output/) for possible additional files to add.
- Initialized documentation using Sphinx for writing the documentation.
  - `doc` supports `readthedocs` documentation: [Transsimhub Documentation](https://transsimhub.readthedocs.io/)
  - Wrote the `introduction` section to introduce the TransSimHub repository.
  - Wrote the `installation` section to explain how to install TransSimHub.
- Added `normalization_dict.py` in `utils`, which normalizes the keys in a dictionary to make their sum equal to 1.
- Added `traffic_light_ids.py` in `sumo_tools/sumo_infos` to return the IDs of traffic lights in the network.

### Changed

- Modified `setup.py` to include `extras_require` for additional support for the `doc` environment.
- Updated `init_log.py` to include the function and corresponding line numbers in the log.
- Added a `vehicle type` attribute in `vehicle.py` to differentiate between ego vehicles and background vehicles.

### Fixed

- Updated `dict_to_str` to handle the format of np.array, as it cannot be directly converted. Added type checking and conversion to resolve TypeError: Object of type ndarray is not JSON serializable.
- Fixed the highlighting functionality in `vehicle_builder.py` to avoid highlighting duplicate vehicles.


<!-- v0.5 -->
## [v0.5] - 2023-08-31

### Added

- Added `tshub_env` module
  - `base_sumo_env.py`: Initializes the SUMO simulation environment.
  - `tshub_env.py`: Integrates "Veh" (vehicles), "Air" (aircraft), and "Traf" (traffic lights) for overall control and information retrieval.
- Added `sumo_env` in `example`
  - `single_junction`: Environment for a single junction.
  - `three_junctions`: Environment for three junctions, including ego vehicle and background vehicles.

### Changed

- `aircraft_builder.py`: Separated SUMO initialization from `aircraft_inits` and now pass SUMO once during the builder process.
- Updated a series of utility functions in `utils`
  - `check_folder.py`: Checks if a folder exists and creates it if it doesn't.
  - `format_dict.py`: Formats a dictionary for better display when printing.
  - `nested_dict_conversion.py`: Converts nested dictionaries.
  - `get_abs_path.py`: Converts relative paths to absolute paths.

### Fixed

- Modified the type of `new_position` in `base_aircraft_action.py` from tuple to list to resolve a TypeError: 'tuple' object does not support item assignment.


<!-- v0.4 -->
## [v0.4] - 2023-08-30

### Added

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

<!-- v0.6 -->
<!-- 添加 uml 框架图 -->
<!-- log 可以设置 level -->
<!-- 环境适配 gym 和 rllib -->

<!-- v0.7 -->
<!-- 添加 feature process 模块 -->