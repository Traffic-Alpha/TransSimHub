'''
@Author: WANG Maonan
@Date: 2024-07-07 23:33:53
@Description: TSHub 渲染 3D 的场景, 这里所有物体都是只添加在场景中, 不添加在 BulletWorld, 不进行碰撞检测
    -> TSHubRenderer 主要由以下的组成:
        -> rendering_components, 
@LastEditTime: 2024-07-14 20:27:15
'''
import math
import random
import numpy as np

from pathlib import Path
from loguru import logger
from typing import Collection, Dict, Literal, Optional, Tuple, Union

from direct.task import Task
from panda3d.core import (
    Camera,
    CardMaker,
    FrameBufferProperties,
    Geom,
    GeomLinestrips,
    GeomNode,
    GeomTrifans,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexReader,
    GeomVertexWriter,
    GraphicsOutput,
    GraphicsPipe,
    NodePath,
    OrthographicLens,
    Shader,
    ShaderInput,
    Texture,
    WindowProperties,
    loadPrcFileData,
    Vec4,
    AmbientLight, 
    DirectionalLight
)

from ..vis3d_utils.colors import Colors, SceneColors
from ..vis3d_utils.coordinates import Pose, Heading, Point

from ..vis3d_renderer._showbase_instance import _ShowBaseInstance
from ..vis3d_renderer.base_render import BaseRender, DEBUG_MODE

from .elements.traffic_signals import signal_state_to_color

from ...utils.get_abs_path import get_abs_path

from ..vis3d_utils.masks import CamMask

# 场景渲染步骤
from .rendering_components import (
    SceneLoader,
    SceneSync
)

BACKEND_LITERALS = Literal[
    "pandagl",      # 使用 OpenGL 渲染
    "pandadx9",     # 使用 DirectX 9 渲染
    "pandagles",    # 使用 OpenGL ES 渲染，适用于较旧的移动设备
    "pandagles2",   # 使用 OpenGL ES 2 渲染，适用于较新的移动设备
    "p3headlessgl", # 使用一个不渲染图形的 OpenGL 上下文，适用于服务器端渲染或无头渲染
    "p3tinydisplay",# 使用 Panda3D 的 TinyDisplay 渲染器，一个非常基础的软件渲染后端
] # 只能是以上几种作为选择

class TSHubRenderer(BaseRender):
    """The utility used to render simulation geometry.
    """
    def __init__(
        self,
        simid: str,
        scenario_glb_dir:str, # 场景 glb 文件夹
        use_render_pipeline:bool=False, # 使用 render_pipeline 此时就是 onscreen 渲染
        render_mode:str="onscreen", # onscreen or offscreen
        debug_mode: DEBUG_MODE = DEBUG_MODE.ERROR,
        rendering_backend: BACKEND_LITERALS = "pandagl",
    ) -> None:
        super().__init__()
        self.current_file_path = get_abs_path(__file__)
        self._simid = simid # 仿真的 id 

        # 场景 node path 记录
        self._is_setup = False # 还没有对场景进行初始化
        self._root_np = None
        self._vehicles_np = None # 车辆节点, 在上面加入新的车辆
        self._signals_np = None # 信号灯节点

        self.use_render_pipeline = use_render_pipeline
        
        # 设置 showbase 的参数
        _ShowBaseInstance.set_use_render_pipeline(use_render_pipeline)
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
    # Step 1, 初始化场景
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
        self._signals_np = self._root_np.attachNewNode("signals") # 信号灯的 node
        
        # 场景初始化器
        scene_loader = SceneLoader(
            root_np=self._root_np,
            showbase_instance=self._showbase_instance,
            scenario_glb_dir=scenario_glb_dir,
            skybox_dir=self.current_file_path("../_assets_3d/skybox/"),
            terrain_dir=self.current_file_path("../_assets_3d/terrain/"),
            map_road_lane_glsl_dir=self.current_file_path("../_assets_3d/map_road_lines/"),
        )
        # 完成了场景的初始化
        self.map_radius, self.map_center = scene_loader.initialize_scene(self.use_render_pipeline)
        self._is_setup = True # 完成初始化

        # 初始化场景同步器
        self.scene_sync = SceneSync(
            root_np=self._root_np,
            showbase_instance=self._showbase_instance
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
    def step(self, tshub_obs):
        """使用 `.taskMgr.step()` 进行单步的渲染. 从而可以和 sumo 同步
        """
        sensor_data = self.scene_sync._sync(tshub_obs) # 首先更新 panda3d 中的物体
        self._showbase_instance.taskMgr.step()
        return sensor_data # 返回传感器的数据
    

    # ----------- #
    # 场景测试工具
    # ----------- #
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

        # 获取 Camera 节点
        camera_node = self._showbase_instance.cam
        # 设置 camera 的 mask
        camera_node.node().setCameraMask(CamMask.MapMask | CamMask.VehMask | CamMask.GroundMask | CamMask.SkyBoxMask)
        return Task.cont
    
    # ----------------- #
    # Gym Env Interface
    # ----------------- #
    def reset(self) -> None:
        """Reset the render back to initialized state.
        """
        if self._vehicles_np is not None:
            self._vehicles_np.removeNode()
            self._vehicles_np = self._root_np.attachNewNode("vehicles")
        if self._signals_np is not None:
            self._signals_np.removeNode()
            self._signals_np = self._root_np.attachNewNode("signals")

        self.scene_sync.reset()

        # 设置相机的参数 (相机的参数可以在调试部分设置)
        self._showbase_instance.camLens.set_fov(90)
        # self._showbase_instance.camLens.set_near_far(0.1, 50000)


    def teardown(self):
        """Clean up internal resources.
        """
        if self._root_np is not None:
            self._root_np.clearLight()
            self._root_np.removeNode()
            self._root_np = None
        self._vehicles_np = None
        self._signals_np = None
        self._is_setup = False


    def destroy(self):
        """Destroy the renderer. Cleans up all remaining renderer resources.
        """
        self.teardown()
        self._showbase_instance.userExit() # 关闭窗口
        self._showbase_instance = None


    def __del__(self):
        self.destroy()

    # ------------------------------- #
    # Traffic Signal Node 创建&更新&删除
    # ------------------------------- #
    def create_signal_node(
        self, sig_id: str, 
        position: Point, 
        color: Union[Colors, SceneColors]
    ) -> bool:
        """Create a signal node.
        """
        if sig_id in self._signal_nodes:
            return False

        # Create geometry node
        name = f"signal-{sig_id}"
        geo_format = GeomVertexFormat.getV3()
        vdata = GeomVertexData(name, geo_format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, "vertex")

        num_pts = 10  # number of points around the circumference
        seg_radians = 2 * math.pi / num_pts
        vertex.addData3(0, 0, 0)
        for i in range(num_pts):
            angle = i * seg_radians
            x = math.cos(angle)
            y = math.sin(angle)
            vertex.addData3(x, y, 0)

        prim = GeomTrifans(Geom.UHStatic)
        prim.addVertex(0)  # add center point
        prim.add_next_vertices(num_pts)  # add outer points
        prim.addVertex(1)  # add first outer point again to complete the circle
        assert prim.closePrimitive()

        geom = Geom(vdata)
        geom.addPrimitive(prim)

        geom_node = GeomNode(name)
        geom_node.addGeom(geom)

        node_path = self._root_np.attachNewNode(geom_node)
        node_path.setName(name)
        node_path.setColor(color.value)
        node_path.setPos(position.x, position.y, 0.01)
        node_path.setScale(0.9, 0.9, 1)
        self._signal_nodes[sig_id] = node_path
        return True

    def begin_rendering_signal(self, sig_id: str):
        """Add the signal node to the scene graph"""
        signal_np = self._signal_nodes.get(sig_id, None)
        if not signal_np:
            self._log.warning("Renderer ignoring invalid signal id: %s", sig_id)
            return
        signal_np.reparentTo(self._signals_np)

    def update_signal_node(
        self, sig_id: str, 
        position: Point, 
        color: Union[Colors, SceneColors]
    ) -> None:
        """Move the specified signal node."""
        signal_np = self._signal_nodes.get(sig_id, None)
        if not signal_np:
            self._log.warning("Renderer ignoring invalid signal id: %s", sig_id)
            return
        signal_np.setPos(position.x, position.y, 0.01)
        signal_np.setColor(color.value)

    def remove_signal_node(self, sig_id: str):
        """Remove a signal node
        """
        signal_np = self._signal_nodes.get(sig_id, None)
        if not signal_np:
            self._log.warning("Renderer ignoring invalid signal id: %s", sig_id)
            return
        signal_np.removeNode()
        del self._signal_nodes[sig_id]

#     def remove_buffer(self, buffer):
#         """Remove the rendering buffer.
#         """
#         self._showbase_instance.graphicsEngine.removeWindow(buffer)

#     def set_interest(self, interest_filter: re.Pattern, interest_color: Colors):
#         """Sets the color of all vehicles that have ids that match the given pattern.

#         Args:
#             interest_filter (re.Pattern): The regular expression pattern to match.
#             interest_color (Colors): The color that the vehicle should show as.
#         """
#         assert isinstance(interest_filter, re.Pattern)
#         self._interest_filter = interest_filter
#         self._interest_color = interest_color