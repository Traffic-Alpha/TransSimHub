'''
@Author: WANG Maonan
@Date: 2024-07-07 23:33:53
@Description: TSHub 渲染 3D 的场景, 这里所有物体都是只添加在场景中, 不添加在 BulletWorld, 不进行碰撞检测
    -> TSHubRenderer 主要由以下的组成:
        -> rendering_components, 
LastEditTime: 2025-07-28 21:14:29
'''
import math
from loguru import logger
from typing import Dict, Optional, List, Union

from direct.task import Task

from tshub.tshub_env3d.scene.utils.colors import Colors, SceneColors

from tshub.tshub_env3d.renderers.panda.masks import CamMask
from tshub.tshub_env3d.renderers.panda.segmentation import tag_seg
from tshub.tshub_env3d.renderers.panda._showbase_instance import _ShowBaseInstance
from tshub.tshub_env3d.renderers.panda.base_render import DEBUG_MODE, BACKEND_LITERALS

from tshub.utils.get_abs_path import get_abs_path

# 渲染器无关的场景描述层
from tshub.tshub_env3d.scene import SceneFrame, SceneStatic, RendererBackend

# 场景渲染步骤
from .rendering_components import (
    SceneLoader,
    SceneSync
)

class TSHubRenderer(RendererBackend):
    """The utility used to render simulation geometry.

    Panda3D 渲染后端: 实现渲染器无关的 RendererBackend 接口 (reset/sync/destroy),
    消费 SceneFrame / SceneStatic 出图. 未来可并列其他后端 (PyTorch3D / moderngl ...).
    """
    def __init__(
        self,
        simid: str,
        sensor_config:Dict[str, List[str]],
        preset:str, # 预设的传感器分辨率大小, 320P, 480P, 720P, 1080P
        resolution:float, # 传感器的分辨率
        scenario_glb_dir:str, # 场景 glb 文件夹
        sky:str = 'day', # 天空: 'day' / 'dust'
        render_mode:str = "onscreen", # onscreen or offscreen
        debug_mode: DEBUG_MODE = DEBUG_MODE.ERROR,
        rendering_backend: BACKEND_LITERALS = "pandagl",
        debuger_print_node: bool = False, # reset 时打印 node path (panda 调试)
        debuger_spin_camera: bool = False, # 显示绕场景旋转的相机 (panda 调试)
        **kwargs, # 吞掉其他后端通用但 panda 不需要的参数
    ) -> None:
        super().__init__()
        self.current_file_path = get_abs_path(__file__)
        self._simid = simid # 仿真的 id
        self.sensor_config = sensor_config # 加载传感器
        self.preset = preset
        self.resolution = resolution
        self.sky = sky
        self.debuger_print_node = debuger_print_node
        self.debuger_spin_camera = debuger_spin_camera

        # 场景 node path 记录
        self._is_setup = False # 还没有对场景进行初始化
        self._root_np = None
        self._vehicles_np = None # 车辆节点, 在上面加入新的车辆
        self._aircraft_np = None # 飞行器节点
        self._signals_np = None # 信号灯节点
        
        # 设置 showbase 的参数
        _ShowBaseInstance.set_render_mode(render_mode)
        _ShowBaseInstance.set_rendering_verbosity(debug_mode=debug_mode)
        _ShowBaseInstance.set_rendering_backend(rendering_backend=rendering_backend)
        # 每一个仿真都有自己的 Renderer, 但是所有的 Renderer object 共用 ShowBaseInstance
        self._showbase_instance: _ShowBaseInstance = _ShowBaseInstance() # 初始化 Pnada3D ShowBase
        self._interest_color: Optional[Union[Colors, SceneColors]] = SceneColors.Agent # 希望 ego 车辆的颜色
        
        # 初始化场景
        self.setup(scenario_glb_dir)

    @property
    def id(self) -> str:
        """The id of the simulation rendered.
        """
        return self._simid

    @property
    def is_setup(self) -> bool:
        """If the renderer has been fully initialized.
        """
        return self._is_setup
    
    # ---------------- #
    # Step 1, 初始化场景 (只需要初始化一次, reset 的时候不需要重新加载环境信息)
    # ---------------- #
    def setup(self, scenario_glb_dir:str) -> None:
        """Initialize this renderer. 初始化场景共分为以下的几个步骤:
        1. 初始化 node path (self._root_np)
        2. 加载 map, road, lane
        3. 加载 skybox
        4. 加载 terrain (目前是 plane terrain)
        5. 加载 light
        """
        self._ensure_root() # 初始化场景的 node
        self._vehicles_np = self._root_np.attachNewNode("vehicles") # 车辆的 node
        tag_seg(self._vehicles_np, 'vehicle') # 语义分割: 车辆 (子车辆继承此标签)
        self._aircraft_np = self._root_np.attachNewNode("aircraft") # 飞行器的 node
        tag_seg(self._aircraft_np, 'aircraft') # 语义分割: 飞行器
        self._signals_np = self._root_np.attachNewNode("signals") # 信号灯的 node
        
        # 场景初始化器
        scene_loader = SceneLoader(
            root_np=self._root_np,
            showbase_instance=self._showbase_instance,
            scenario_glb_dir=scenario_glb_dir,
            skybox_dir=self.current_file_path("../../_assets_3d/skybox/"),
            terrain_dir=self.current_file_path("../../_assets_3d/terrain/"),
            map_road_lane_glsl_dir=self.current_file_path("../../_assets_3d/map_road_lines/"),
            sky=self.sky,
        )
        # 完成了场景的初始化
        self.map_radius, self.map_center = scene_loader.initialize_scene()
        self._is_setup = True # 完成初始化

        # 初始化场景同步器 (sensor 在这里进行设置)
        self.scene_sync = SceneSync(
            root_np=self._root_np,
            showbase_instance=self._showbase_instance,
            sensor_config=self.sensor_config,
            preset=self.preset,
            resolution=self.resolution,
        )

    def _ensure_root(self) -> None:
        """初始化场景的根节点 node
        """
        if self._root_np is None:
            self._root_np = self._showbase_instance.setup_sim_root(self._simid)
            logger.debug(
                f"SIM: Renderer started with backend \
                    {self._showbase_instance.pipe.get_type()}",
            )

    # ---------------------------------- #
    # Step 2, step (include sync), reset
    # ---------------------------------- #
    def sync(self, frame: SceneFrame, should_count_vehicles=False):
        """消费一帧渲染器无关的 SceneFrame, 同步渲染为 3D 并读回传感器数据.
        """
        sensor_data = self.scene_sync._sync(frame) # 更新 panda3d 中的物体 & 更新 camera

        # 是否统计车辆信息
        if should_count_vehicles:
            veh_infos = {}
            for veh_id, veh_element in self.scene_sync._vehicle_elements.items():
                _veh_pose = veh_element.get_element_pose_from_bumper()
                _veh_model = veh_element.veh_model_name
                veh_infos[veh_id] = {
                    'pos': _veh_pose.position.tolist(),
                    'heading': _veh_pose.heading_.real,
                    'model': _veh_model
                }
            return {'image': sensor_data, 'veh_elements': veh_infos} # 返回 (传感器的数据, 车辆统计信息)

        return sensor_data # 返回 (传感器的数据, )

    def step(self, frame: SceneFrame, should_count_vehicles=False):
        """step: 委托给 sync (语义等价), 兼容旧接口命名."""
        return self.sync(frame, should_count_vehicles)


    # ----------- #
    # 场景测试工具
    # ----------- #
    @staticmethod
    def print_node_paths(nodepath, prefix='->') -> None:
        """递归打印 node paths (reset 调试用)."""
        logger.info(f'SIM: {prefix} {nodepath.getName()}')
        for child in nodepath.getChildren():
            TSHubRenderer.print_node_paths(child, prefix + '  ')

    def dummyTask(self, task):
        """添加任务避免 userExit 出错
        """
        return task.cont
    
    def test_spin_camera_task(self, task):
        """用于测试场景加载是否正确, 使得 camera 在 map 的中心
        """
        angleDegrees = task.time * 6.0
        angleRadians = angleDegrees * (math.pi / 180.0)
        distance = 30 # 调整距离关注点的距离, 越小车显示越大 (Distance from the center of the model on the X-Y plane)
        height = 20 # 视角的高度 (Lower the height to change the viewing angle)
        cameraX = self.map_center[0] + distance * math.sin(angleRadians)
        cameraY = self.map_center[1] - distance * math.cos(angleRadians)
        cameraZ = self.map_center[2] + height
        self._showbase_instance.camera.setPos(cameraX, cameraY, cameraZ)
        self._showbase_instance.camera.lookAt(*self.map_center)  # Adjust the camera to look at the center of the model
        self._showbase_instance.camLens.set_fov(90)

        # 获取 Camera 节点
        camera_node = self._showbase_instance.cam
        # 设置 camera 的 mask
        camera_node.node().setCameraMask(
            CamMask.MapMask | CamMask.VehMask | CamMask.GroundMask |
            CamMask.SkyBoxMask | CamMask.AircraftMask
        )
        return Task.cont
    
    # ----------------- #
    # Gym Env Interface
    # ----------------- #
    def reset(self, static: SceneStatic) -> None:
        """Reset the render back to initialized state.
        """
        if self._vehicles_np is not None:
            self._vehicles_np.removeNode()
            self._vehicles_np = self._root_np.attachNewNode("vehicles")
            tag_seg(self._vehicles_np, 'vehicle') # reset 重建后重新打标签
        if self._aircraft_np is not None:
            self._aircraft_np.removeNode()
            self._aircraft_np = self._root_np.attachNewNode("aircraft")
            tag_seg(self._aircraft_np, 'aircraft')
        if self._signals_np is not None:
            self._signals_np.removeNode()
            self._signals_np = self._root_np.attachNewNode("signals")

        # 初始化场景的时候, 需要新建一下路口的摄像头 (rig 几何已由 build_tls_rigs 计算)
        self.scene_sync.reset(static)

        # 加入一个简单任务, 避免 userExit 出错
        self._showbase_instance.taskMgr.add(self.dummyTask, "dummyTask")

        # reset 后打印 node path (查看每次 reset 是否会重置所有 node 和 camera)
        if self.debuger_print_node:
            self.print_node_paths(self._root_np)

        # 场景添加绕行相机, 可以进行可视化调试
        if self.debuger_spin_camera:
            self._showbase_instance.taskMgr.add(self.test_spin_camera_task, "SpinCamera")

    def teardown(self) -> None:
        """Clean up internal resources.
        """
        if self._root_np is not None:
            self._root_np.clearLight()
            self._root_np.removeNode()
            self._root_np = None
        self._vehicles_np = None
        self._aircraft_np = None
        self._signals_np = None
        self._is_setup = False


    def destroy(self):
        """Destroy the renderer. Cleans up all remaining renderer resources.
        """
        self.teardown()
        showbase_instance = getattr(self, "_showbase_instance", None)
        if showbase_instance is not None:
            showbase_instance.destroy() # 关闭 Panda3D ShowBase, 不触发 sys.exit()
        self._showbase_instance = None


    def __del__(self):
        try:
            self.destroy()
        except (AttributeError, TypeError, SystemExit):
            pass
