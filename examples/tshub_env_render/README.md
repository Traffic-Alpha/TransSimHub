<!--
 * @Author: WANG Maonan
 * @Date: 2023-11-13 23:37:33
 * @Description: visualization in TransSimHub (TsHub)
 * @LastEditTime: 2023-11-14 12:48:22
-->
# Visualization for TransSimHub

TransSimHub supports pixel-based state output. There are two rendering modes provided by TransSimHub, namely `rgb` and `sumo_gui`. Each of these rendering modes supports three perspectives: `global`, `local intersection`, and `follow vehicle`. Rendering the scene is straightforward, simply use the `.render()` method. The `mode` parameter is used to specify whether to render with `rgb` or `sumo_gui`.

The code below renders in `rgb` mode and uses `plt2arr` to convert `plt` to `array`.

```python
from tshub.utils.plt_to_array import plt2arr

obs, reward, info, done = tshub_env.step(actions=actions)
fig = tshub_env.render(mode='rgb')
fig_array = plt2arr(fig) # convert fig to array
```

By changing the `mode` to `sumo_gui`, you can output in `sumo-gui` style. In this mode, you need to pass in a file path, and the result will be saved directly to the specified folder. Note that this rendering method requires `sumo-gui` to be enabled and the simulation window to be fullscreen, otherwise the output image will be incomplete.

```python
obs, reward, info, done = tshub_env.step(actions=actions)
fig = tshub_env.render(
    mode='sumo_gui',
    save_folder=image_save_folder
)
```

Both `rgb` and `sumo_gui` support three visualization modes: global rendering, local intersection rendering, and follow vehicle rendering. Each will be introduced in detail below. The following is a diagram that summarizes the six rendering methods:

```
TransSimHub Rendering Modes
|
|-- Pixel-based State Output
|   |
|   |-- RGB Rendering Mode
|   |   |
|   |   |-- Global Rendering
|   |   |-- Local Intersection Rendering
|   |   |-- Follow Vehicle Rendering
|   |
|   |-- SUMO-GUI Rendering Mode
|       |
|       |-- Global Rendering
|       |-- Local Intersection Rendering
|       |-- Follow Vehicle Rendering

```

## Global Rendering

When only `mode` and `save_folder` are passed into `render`, without specifying `focus_id`, it will save the global simulation effect.

```python
obs, reward, info, done = tshub_env.step(actions=actions)
fig = tshub_env.render(
    mode='sumo_gui', # 'rgb'
    save_folder=image_save_folder
)
```

Below are examples of global rendering effects in `rgb` and `sumo-gui` modes:

<table>
  <tr>
    <td><img src="./assets/rgb_global.gif" width="450"/></td>
    <td><img src="./assets/sumogui_global.gif" width="450"/></td>
  </tr>
  <tr>
    <td align="center">RGB Mode Global</td>
    <td align="center">SUMO-GUI Mode Global</td>
  </tr>
</table>


## Local Intersection Rendering

Sometimes we are only interested in the information of a local intersection. In this case, you can specify `focus_type` as `node` in `render`, and give the `node id`. Finally, specify `focus_distance` to indicate our observation range. Below is an example of intersection rendering:

```python
obs, reward, info, done = tshub_env.step(actions=actions)
fig = tshub_env.render(
    focus_id='25663429', 
    focus_type='node', 
    focus_distance=80,
    mode='sumo_gui',
    save_folder=image_save_folder
)
```

Below are examples of local intersection rendering effects in `rgb` and `sumo-gui` modes:

<table>
  <tr>
    <td><img src="./assets/rgb_node.gif" width="450"/></td>
    <td><img src="./assets/sumogui_node.gif" width="450"/></td>
  </tr>
  <tr>
    <td align="center">RGB Mode Local Intersection</td>
    <td align="center">SUMO-GUI Local Intersection</td>
  </tr>
</table>


## Follow Vehicle Rendering

Sometimes we are interested in the state around a certain vehicle. In this case, you can use the follow vehicle mode. You just need to specify `focus_type` as `vehicle`, and set `focus_id` to the ID of the vehicle of interest. Below is the sample code:

```python
obs, reward, info, done = tshub_env.step(actions=actions)
fig = tshub_env.render(
    focus_id='-1105574288#1__0__background.1', 
    focus_type='vehicle', 
    focus_distance=80,
    mode='sumo_gui',
    save_folder=image_save_folder
)
```

Below are examples of follow vehicle rendering effects in `rgb` and `sumo-gui` modes:

<table>
  <tr>
    <td><img src="./assets/rgb_vehicle.gif" width="450"/></td>
    <td><img src="./assets/sumogui_vehicle.gif" width="450"/></td>
  </tr>
  <tr>
    <td align="center">RGB Mode Follow Vehicle</td>
    <td align="center">SUMO-GUI Follow Vehicle</td>
  </tr>
</table>