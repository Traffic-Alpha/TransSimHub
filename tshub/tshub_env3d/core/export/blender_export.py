'''
@Author: WANG Maonan
@Date: 2026-08-15
@Description: 离线高精度渲染 (Blender) 的「剧集 (episode) 导出」—— 渲染器无关.

在线 Panda3D 后端每步直接出图; 离线 Blender/Cycles 走另一条路: 先把一次仿真
「导出」成纯数据 (每步一个 JSON), 再交给 Blender 后台批量渲染. 这样 Blender 侧
不依赖 tshub/SUMO/Panda3D, 只消费 JSON, 也不再需要手工准备 .blend 文件.

导出的目录结构:
    <episode_dir>/manifest.json      场景 glb 目录 / 车模目录 / 分辨率 等全局信息
    <episode_dir>/frames/0000.json   每一仿真步: 车辆 + 飞行器位姿 + 相机位姿

坐标与航向约定 (与 Panda 后端完全一致, 保证两条路径出图可比):
- 位置: tshub/SUMO 世界坐标 (x, y 为地面, z 为高度), 单位米;
- 车辆 position 为「车头 (front bumper)」, 导出时换算为「车辆中心」(同 Pose.from_front_bumper);
- heading: 导出为 tshub/SMARTS 约定的弧度 (0 = +Y/正北, 逆时针为正),
  即 Panda 侧 `pose.as_panda3d()` 使用的那个角度的弧度形式.
@LastEditTime: 2026-08-15
'''
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from ..state.scene_elements import SceneFrame, SceneStatic
from ..sensors.sensor_rig import compute_camera_pose, get_camera_rig
from ..models.vehicle_models import select_vehicle_model_name, vehicle_models_dir
from ..models.aircraft_models import select_aircraft_model_name, aircraft_models_dir

MANIFEST_NAME = 'manifest.json'
FRAMES_DIRNAME = 'frames'


# ---------------------------------------------------------------- #
# 纯几何工具 (与 core.utils.coordinates 中的实现等价, 但不引入 shapely/numpy)
# ---------------------------------------------------------------- #
def sumo_heading_to_ccw_deg(sumo_heading_deg: float) -> float:
    """SUMO 航向 (度, 0=正北, 顺时针) -> tshub/SMARTS 航向 (度, 0=+Y, 逆时针).

    等价于 `math.degrees(Heading.from_sumo(sumo_heading_deg))` (差整数圈).
    """
    return (-float(sumo_heading_deg)) % 360.0


def heading_to_vec(heading_ccw_deg: float) -> Tuple[float, float]:
    """航向 (度, 0=+Y, 逆时针) -> 单位方向向量, 等价于 core_math.radians_to_vec."""
    rad = math.radians(heading_ccw_deg)
    return (-math.sin(rad), math.cos(rad))


def front_bumper_to_center(position, heading_ccw_deg: float, length: float) -> Tuple[float, float, float]:
    """车头坐标 -> 车辆中心坐标 (等价于 Pose.from_front_bumper)."""
    dx, dy = heading_to_vec(heading_ccw_deg)
    half = 0.5 * float(length or 0.0)
    x, y = float(position[0]), float(position[1])
    z = float(position[2]) if len(position) > 2 else 0.0
    return (x - dx * half, y - dy * half, z)


# ---------------------------------------------------------------- #
# 相机位姿 (复用 sensor_rig, 与 Panda 后端同一套 rig 与同一个公式)
# ---------------------------------------------------------------- #
def build_camera_specs(
        sensor_config: Dict[str, Any],
        tls_rigs: Dict[str, Dict[str, Any]],
        carriers: Dict[str, Dict[str, Any]],
        skip_modalities: Tuple[str, ...] = ('seg',),
    ) -> List[Dict[str, Any]]:
    """算出当前帧所有相机的世界位姿 (eye/target) 与镜头参数.

    Args:
        sensor_config: 与 Tshub3DEnvironment 相同的传感器配置.
        tls_rigs: build_tls_rigs 的结果 (路口相机的载体位姿).
        carriers: 本帧可用的车辆 / 飞行器载体,
            {'vehicle': {veh_id: (center_xyz, heading_ccw_deg)}, 'aircraft': {...}}.
        skip_modalities: 跳过的模态 (Blender 侧暂不支持语义分割 pass).
    Returns:
        [{name, element_id, sensor_type, eye, target, fov_deg, ortho_size, top_down}, ...]
    """
    specs: List[Dict[str, Any]] = []

    def _emit(element_id: str, sensor_type: str, carrier_xy, heading_deg,
              carrier_z: float = 0.0, height_override: Optional[float] = None) -> None:
        rig = get_camera_rig(sensor_type)
        if rig.modality in skip_modalities:
            return
        eye, target = compute_camera_pose(
            rig, carrier_xy, heading_deg,
            height_override=height_override, carrier_z=carrier_z,
        )
        specs.append({
            'name': f'{element_id}__{sensor_type}',
            'element_id': element_id,
            'sensor_type': sensor_type,
            'eye': [float(v) for v in eye],
            'target': [float(v) for v in target],
            'fov_deg': rig.fov_deg,
            'ortho_size': rig.ortho_size,
            'top_down': rig.top_down,
        })

    # 车辆 / 飞行器: 相机随载体移动, 每帧都要重算
    for category in ('vehicle', 'aircraft'):
        for element_id, element_cfg in sensor_config.get(category, {}).items():
            carrier = carriers.get(category, {}).get(element_id)
            if carrier is None: # 该载体本帧不在场景中 (车辆尚未出发 / 已驶离)
                continue
            (cx, cy, cz), heading_deg = carrier
            for sensor_type in element_cfg.get('sensor_types', []):
                _emit(element_id, sensor_type, (cx, cy), heading_deg, carrier_z=cz)

    # 路口相机: 固定不动, 位姿来自 build_tls_rigs
    for element_id, rig_info in tls_rigs.items():
        heading_deg = sumo_heading_to_ccw_deg(rig_info.get('heading', 0.0))
        for sensor_type in rig_info.get('sensor_types', []):
            _emit(element_id, sensor_type,
                  rig_info['position'][:2], heading_deg,
                  carrier_z=0.0, height_override=rig_info.get('tls_camera_height'))

    return specs


# ---------------------------------------------------------------- #
# 剧集导出器
# ---------------------------------------------------------------- #
class BlenderEpisodeExporter:
    """把一次仿真导出为 Blender 可直接消费的 JSON 剧集.

    典型用法 (在 tshub 环境中, 不需要任何渲染后端):

        exporter = BlenderEpisodeExporter(out_dir, scenario_glb_dir, sensor_config)
        obs = env.reset()
        exporter.reset(build_tls_rigs(obs, sensor_config))
        for _ in range(steps):
            obs, *_ = env.step(actions)
            exporter.add_frame(build_frame(obs))
        exporter.close()
    """

    def __init__(
            self,
            episode_dir: str,
            scenario_glb_dir: str,
            sensor_config: Dict[str, Any],
            resolution: Tuple[int, int] = (1280, 720),
            samples: int = 64,
            style: str = 'day',
            vehicles_dir: str = None,
            aircraft_dir: str = None,
        ) -> None:
        self.episode_dir = Path(episode_dir)
        self.frames_dir = self.episode_dir / FRAMES_DIRNAME
        self.scenario_glb_dir = str(Path(scenario_glb_dir).resolve())
        self.sensor_config = sensor_config or {}
        self.resolution = (int(resolution[0]), int(resolution[1]))
        self.samples = int(samples)
        self.style = style
        self.vehicles_dir = str(Path(vehicles_dir or vehicle_models_dir()).resolve())
        self.aircraft_dir = str(Path(aircraft_dir or aircraft_models_dir()).resolve())

        self._tls_rigs: Dict[str, Dict[str, Any]] = {}
        self._model_cache: Dict[str, str] = {} # 车辆 id -> 模型 (一辆车整局只随机一次)
        self._frame_files: List[str] = []

    # ----------- 生命周期 ----------- #
    def reset(self, tls_rigs: Dict[str, Dict[str, Any]] = None, static: SceneStatic = None) -> None:
        """开始一局导出. 传 tls_rigs (build_tls_rigs 结果) 或直接传 SceneStatic."""
        if static is not None:
            tls_rigs = static.tls_rigs
            self.scenario_glb_dir = str(Path(static.scenario_glb_dir).resolve())
            self.sensor_config = static.sensor_config or self.sensor_config
        self._tls_rigs = tls_rigs or {}
        self._model_cache.clear()
        self._frame_files.clear()
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        for stale in self.frames_dir.glob('*.json'): # 避免与上一局的帧混在一起
            stale.unlink()

    def add_frame(self, frame: SceneFrame) -> str:
        """导出一仿真步, 返回写出的 JSON 路径."""
        index = len(self._frame_files)
        vehicles, vehicle_carriers = self._export_vehicles(frame)
        aircraft, aircraft_carriers = self._export_aircraft(frame)
        cameras = build_camera_specs(
            sensor_config=self.sensor_config,
            tls_rigs=self._tls_rigs,
            carriers={'vehicle': vehicle_carriers, 'aircraft': aircraft_carriers},
        )
        payload = {
            'index': index,
            'vehicles': vehicles,
            'aircraft': aircraft,
            'cameras': cameras,
        }
        frame_path = self.frames_dir / f'{index:04d}.json'
        frame_path.write_text(json.dumps(payload))
        self._frame_files.append(f'{FRAMES_DIRNAME}/{frame_path.name}')
        return str(frame_path)

    def close(self) -> str:
        """写出 manifest, 返回 manifest 路径."""
        manifest = {
            'scenario_glb_dir': self.scenario_glb_dir,
            'vehicles_dir': self.vehicles_dir,
            'aircraft_dir': self.aircraft_dir,
            'resolution': list(self.resolution),
            'samples': self.samples,
            'style': self.style,
            'sensor_config': self.sensor_config,
            'frames': self._frame_files,
        }
        self.episode_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self.episode_dir / MANIFEST_NAME
        manifest_path.write_text(json.dumps(manifest, indent=2))
        logger.info(f'SIM: Blender episode exported ({len(self._frame_files)} frames) -> {manifest_path}')
        return str(manifest_path)

    # ----------- 内部 ----------- #
    def _export_vehicles(self, frame: SceneFrame):
        vehicles: Dict[str, Any] = {}
        carriers: Dict[str, Any] = {}
        for veh_id, pose in frame.vehicles.items():
            heading_deg = sumo_heading_to_ccw_deg(pose.heading)
            center = front_bumper_to_center(pose.position, heading_deg, pose.length)
            if veh_id not in self._model_cache: # 同一辆车整局使用同一个模型
                self._model_cache[veh_id] = select_vehicle_model_name(pose.object_type)
            vehicles[veh_id] = {
                'model': self._model_cache[veh_id],
                'position': list(center),
                'heading': math.radians(heading_deg),
                'type': pose.object_type,
            }
            carriers[veh_id] = (center, heading_deg)
        return vehicles, carriers

    def _export_aircraft(self, frame: SceneFrame):
        aircraft: Dict[str, Any] = {}
        carriers: Dict[str, Any] = {}
        for aid, pose in frame.aircraft.items():
            heading_deg = sumo_heading_to_ccw_deg(pose.heading)
            position = [float(v) for v in pose.position]
            aircraft[aid] = {
                'model': select_aircraft_model_name(pose.object_type),
                'position': position,
                'heading': math.radians(heading_deg),
                'type': pose.object_type,
            }
            carriers[aid] = (tuple(position), heading_deg)
        return aircraft, carriers
