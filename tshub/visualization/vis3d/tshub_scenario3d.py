'''
@Author: WANG Maonan
@Date: 2024-07-03 23:16:12
@Description: TSHub 渲染 3D 的场景 (主程序)
@LastEditTime: 2024-07-07 21:35:47
'''
import re
import math
import numpy as np
import importlib.resources as pkg_resources

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
)

from . import _glsl as glsl
from .vis3d_utils.masks import RenderMasks
from .vis3d_utils.colors import Colors, SceneColors
from .vis3d_utils.coordinates import Pose, Heading, Point
from .vis3d_renderer.showbase_instance import _ShowBaseInstance
from .vis3d_renderer.base_scenario3d import Scenario3DBase, DEBUG_MODE
from .vis3d_elements.traffic_signals import signal_state_to_color

BACKEND_LITERALS = Literal[
    "pandagl",      # 使用 OpenGL 渲染
    "pandadx9",     # 使用 DirectX 9 渲染
    "pandagles",    # 使用 OpenGL ES 渲染，适用于较旧的移动设备
    "pandagles2",   # 使用 OpenGL ES 2 渲染，适用于较新的移动设备
    "p3headlessgl", # 使用一个不渲染图形的 OpenGL 上下文，适用于服务器端渲染或无头渲染
    "p3tinydisplay",# 使用 Panda3D 的 TinyDisplay 渲染器，一个非常基础的软件渲染后端
] # 只能是以上几种作为选择

class TSHubRenderer(Scenario3DBase):
    """The utility used to render simulation geometry.
    """
    def __init__(
        self,
        simid: str,
        scenario_glb_dir:str, # 场景 glb 文件夹
        vehicle_model:str, # 车辆的模型
        debug_mode: DEBUG_MODE = DEBUG_MODE.ERROR,
        rendering_backend: BACKEND_LITERALS = "pandagl",
    ) -> None:
        self._simid = simid # 仿真的 id
        self.vehicle_model = vehicle_model     

        self._is_setup = False # 还没有对场景进行初始化
        self._root_np = None
        self._vehicles_np = None
        self._signals_np = None
        self._road_map_np = None
        self._dashed_lines_np = None
        self.map_bounds = None # 地图的边界

        self._vehicle_nodes = {}
        self._signal_nodes = {}

        # self._camera_nodes: Dict[str, Union[P3DOffscreenCamera, P3DShaderStep]] = {}
        _ShowBaseInstance.set_rendering_verbosity(debug_mode=debug_mode)
        _ShowBaseInstance.set_rendering_backend(rendering_backend=rendering_backend)
        # Note: Each instance of the SMARTS simulation will have its own Renderer,
        # but all Renderer objects share the same ShowBaseInstance.
        self._showbase_instance: _ShowBaseInstance = _ShowBaseInstance() # 初始化一个场景
        self._interest_filter: Optional[re.Pattern] = None
        self._interest_color: Optional[Union[Colors, SceneColors]] = None # 希望 ego 车辆的颜色
        
        # 初始化场景
        self.setup(scenario_glb_dir)

    @property
    def id(self):
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
    def setup(self, scenario_glb_dir:str):
        """Initialize this renderer.
        """
        self._ensure_root() # 初始化场景的 node
        self._vehicles_np = self._root_np.attachNewNode("vehicles") # 车辆的 node
        self._signals_np = self._root_np.attachNewNode("signals") # 信号灯的 node

        # Load map
        map_path = Path(scenario_glb_dir) / "map.glb"
        self.map_bounds = self.load_road_map(map_path) # 加载地图数据

        # Road lines (solid, yellow)
        road_lines_path = Path(scenario_glb_dir) / "road_lines.glb"
        if road_lines_path.exists():
            road_lines_np = self._load_line_data(road_lines_path, "road_lines")
            solid_lines_np = self._root_np.attachNewNode(road_lines_np)
            solid_lines_np.setColor(SceneColors.EdgeDivider.value)
            solid_lines_np.hide(RenderMasks.OCCUPANCY_HIDE)
            solid_lines_np.setRenderModeThickness(2) # 设置显示的粗细

        # Lane lines (dashed, white)
        lane_lines_path = Path(scenario_glb_dir) / "lane_lines.glb"
        if lane_lines_path.exists():
            lane_lines_np = self._load_line_data(lane_lines_path, "lane_lines")
            dashed_lines_np = self._root_np.attachNewNode(lane_lines_np)
            dashed_lines_np.setColor(SceneColors.LaneDivider.value)
            dashed_lines_np.hide(RenderMasks.OCCUPANCY_HIDE)
            dashed_lines_np.setRenderModeThickness(2)
            with pkg_resources.path(
                glsl, "dashed_line_shader.vert"
            ) as vshader_path, pkg_resources.path(
                glsl, "dashed_line_shader.frag"
            ) as fshader_path:
                dashed_line_shader = Shader.load(
                    Shader.SL_GLSL,
                    vertex=str(vshader_path.absolute()),
                    fragment=str(fshader_path.absolute()),
                )
                dashed_lines_np.setShader(dashed_line_shader, priority=20)
                dashed_lines_np.setShaderInput(
                    "iResolution", self._showbase_instance.getSize()
                )
            self._dashed_lines_np = dashed_lines_np

        self._is_setup = True # 完成初始化

    def _ensure_root(self) -> None:
        """初始化场景的根节点 node
        """
        if self._root_np is None:
            self._root_np = self._showbase_instance.setup_sim_root(self._simid)
            logger.debug(
                f"SIM: Renderer started with backend {self._showbase_instance.pipe.get_type()}",
            )

    def load_road_map(self, map_path: Union[str, Path]):
        """Load the road map from its path. (加载 3D 地图的文件)
        """
        # Load map
        self._ensure_root()
        if self._road_map_np:
            logger.debug(
                f"SIM: road_map={self._road_map_np} already exists. Removing and adding a new "
                f"one from glb_path={map_path}",
            )
        
        # 加载地图
        map_np = self._showbase_instance.loader.loadModel(map_path, noCache=True)
        node_path = self._root_np.attachNewNode("road_map")
        map_np.reparent_to(node_path)
        node_path.hide(RenderMasks.OCCUPANCY_HIDE)
        node_path.setColor(SceneColors.Road.value)
        self._road_map_np = node_path
        self._is_setup = True
        return map_np.getBounds()
    
    def _load_line_data(self, path: Path, name: str) -> GeomNode:
        """从模型中提取几何线段数据，并将这些数据重新组装成一个新的 GeomNode 对象（方便后续操作）

        Args:
            path (Path): 模型的文件路径
            name (str): geom 的名称
        """
        lines = []
        road_lines_np = self._showbase_instance.loader.loadModel(path, noCache=True)
        geomNodeCollection = road_lines_np.findAllMatches("**/+GeomNode")
        for nodePath in geomNodeCollection:
            geomNode = nodePath.node()
            geom = geomNode.getGeom(0)
            vdata = geom.getVertexData()
            vreader = GeomVertexReader(vdata, "vertex")
            pts = []
            while not vreader.isAtEnd():
                v = vreader.getData3()
                pts.append((v.x, v.y, v.z))
            lines.append(pts)

        # Create geometry node
        geo_format = GeomVertexFormat.getV3()
        vdata = GeomVertexData(name, geo_format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, "vertex")

        prim = GeomLinestrips(Geom.UHStatic)
        for pts in lines:
            for x, y, z in pts:
                vertex.addData3(x, y, z)
            prim.add_next_vertices(len(pts))
            assert prim.closePrimitive()

        geom = Geom(vdata)
        geom.addPrimitive(prim)

        node_path = GeomNode(name)
        node_path.addGeom(geom)
        return node_path

    # --------------------------- #
    # Step 2, 3D 场景 Node 的更新
    # --------------------------- #
    def sync(self, tshub_obs) -> None:
        """Update the current state of the vehicles and signals within the renderer.
        """
        signal_ids = set()
        veh_ids = set()
        for veh_id, veh_info in tshub_obs['vehicle'].items():
            veh_ids.add(veh_id) # 记录当前场景下车辆的 id
            veh_type = veh_info['vehicle_type'] # 获得车辆类型
            veh_pos = veh_info['position'] # 获得车辆类型
            veh_heading = veh_info['heading'] # 获得车辆类型
            veh_length = veh_info['length'] # 获得车辆类型
            # 如果车辆存在, 则更新车辆的位置
            if veh_id in self._vehicle_nodes:
                self.update_vehicle_node(
                    vid=veh_id,
                    veh_position=veh_pos,
                    veh_heading=veh_heading,
                    veh_length=veh_length
                )
            else: # 如果车辆不在场景, 则创建车辆的 node
                self.create_vehicle_node(
                    glb_model=self.vehicle_model,
                    vid=veh_id,
                    veh_type=veh_type,
                    veh_position=veh_pos,
                    veh_heading=veh_heading,
                    veh_length=veh_length
                )
                self.begin_rendering_vehicle(vid=veh_id) # 开始渲染车辆节点

            # traffic signal 的颜色绘制在停车线上面
            # elif isinstance(actor_state, SignalState):
            #     signal_ids.add(actor_id)
            #     color = signal_state_to_color(actor_state.state)
            #     if actor_id not in self._signal_nodes:
            #         self.create_signal_node(actor_id, actor_state.stopping_pos, color)
            #         self.begin_rendering_signal(actor_id)
            #     else:
            #         self.update_signal_node(actor_id, actor_state.stopping_pos, color)

        # 车辆离开等, 则进行删除
        missing_vehicle_ids = set(self._vehicle_nodes) - set(veh_ids)
        # missing_signal_ids = set(self._signal_nodes) - signal_ids

        for vid in missing_vehicle_ids:
            self.remove_vehicle_node(vid)
            logger.info(f'SIM: 3D, Vehicle {vid} leave the scenario.')
        # for sig_id in missing_signal_ids:
        #     self.remove_signal_node(sig_id)

    def render(self):
        """Render the scene graph of the simulation (从根节点进行渲染).
        """
        if not self._is_setup:
            self._ensure_root()
            logger.warning(
                "SIM: Renderer is not setup." 
                "Rendering before scene setup may be unintentional.",
            )
        self._showbase_instance.render_node(self._root_np)

    # ------------------- #
    # 设置相机, 捕捉不同视角
    # ------------------- #
    # def camera_for_id(self, camera_id: str) -> Union[P3DOffscreenCamera, P3DShaderStep]:
    #     """Get a camera by its id.
    #     """
    #     camera = self._camera_nodes.get(camera_id)
    #     assert (
    #         camera is not None
    #     ), f"Camera {camera_id} does not exist, have you created this camera?"
    #     return camera

    # def build_offscreen_camera(
    #     self,
    #     name: str,
    #     mask: int,
    #     width: int,
    #     height: int,
    #     resolution: float,
    # ) -> None:
    #     """Generates a new off-screen camera.
    #     """
    #     # setup buffer
    #     win_props = WindowProperties.size(width, height)
    #     fb_props = FrameBufferProperties()
    #     fb_props.setRgbColor(True)
    #     fb_props.setRgbaBits(8, 8, 8, 1)
    #     # XXX: Though we don't need the depth buffer returned, setting this to 0
    #     #      causes undefined behavior where the ordering of meshes is random.
    #     fb_props.setDepthBits(8)

    #     buffer = self._showbase_instance.win.engine.makeOutput(
    #         self._showbase_instance.pipe,
    #         "{}-buffer".format(name),
    #         -100,
    #         fb_props,
    #         win_props,
    #         GraphicsPipe.BFRefuseWindow,
    #         self._showbase_instance.win.getGsg(),
    #         self._showbase_instance.win,
    #     )
    #     # Set background color to black
    #     buffer.setClearColor((0, 0, 0, 0))

    #     # Necessary for the lane lines to be in the proper proportions
    #     if self._dashed_lines_np is not None:
    #         self._dashed_lines_np.setShaderInput(
    #             "iResolution", (buffer.size.x, buffer.size.y)
    #         )

    #     # setup texture
    #     tex = Texture()
    #     region = buffer.getDisplayRegion(0)
    #     region.window.addRenderTexture(
    #         tex, GraphicsOutput.RTM_copy_ram, GraphicsOutput.RTP_color
    #     )

    #     # setup camera
    #     lens = OrthographicLens()
    #     lens.setFilmSize(width * resolution, height * resolution)

    #     camera_np = self._showbase_instance.makeCamera(
    #         buffer, camName=name, scene=self._root_np, lens=lens
    #     )
    #     camera_np.reparentTo(self._root_np) # 设置 camera 在 node 上

    #     # mask is set to make undesirable objects invisible to this camera
    #     camera_np.node().setCameraMask(camera_np.node().getCameraMask() & mask)

    #     camera = P3DOffscreenCamera(self, camera_np, buffer, tex)
    #     self._camera_nodes[name] = camera

    # --------------------- #
    # Vehicle 创建&更新&删除
    # --------------------- #
    def begin_rendering_vehicle(self, vid: str):
        """Add the vehicle node to the scene graph
        """
        vehicle_path = self._vehicle_nodes.get(vid, None)
        if not vehicle_path:
            logger.warning("SIM: Renderer ignoring invalid vehicle id: %s", vid)
            return
        vehicle_path.reparentTo(self._vehicles_np)

    def create_vehicle_node(
        self,
        glb_model: Union[str, Path],
        vid: str,
        veh_type: str,
        veh_position:Tuple[float],
        veh_heading: float,
        veh_length: float,
        color: Union[Colors, SceneColors]=Colors.BlueTransparent,
    ) -> bool:
        """Create a vehicle node.
        """
        if vid in self._vehicle_nodes:
            return False # 不会重复进行添加
        node_path = self._showbase_instance.loader.loadModel(glb_model)
        node_path.setName("vehicle-%s" % vid)
        if (
            'ego' in veh_type
            and self._interest_color is not None
        ): # 如果是 ego 车, 则使用不一样的颜色
            node_path.setColor(self._interest_color.value)
        else:
            node_path.setColor(color.value)

        pose = Pose.from_front_bumper(
            front_bumper_position=np.array(veh_position),
            heading=Heading.from_sumo(veh_heading),
            length=veh_length,
        ) # 车辆坐标转换
        pos, heading = pose.as_panda3d() # 转换为位置和角度
        node_path.setPosHpr(*pos, heading, 0, 0)
        node_path.hide(RenderMasks.DRIVABLE_AREA_HIDE)
        if color in (SceneColors.Agent,):
            node_path.hide(RenderMasks.OCCUPANCY_HIDE)
        self._vehicle_nodes[vid] = node_path
        return True

    def update_vehicle_node(
            self, 
            vid: str, 
            veh_position:Tuple[float],
            veh_heading: float,
            veh_length: float,
        ) -> None:
        """Move the specified vehicle node. (更新车辆的位置)
        """
        vehicle_path = self._vehicle_nodes.get(vid, None)
        if not vehicle_path:
            logger.warning("SIM: Renderer ignoring invalid vehicle id: %s", vid)
            return

        pose = Pose.from_front_bumper(
            front_bumper_position=np.array(veh_position),
            heading=Heading.from_sumo(veh_heading),
            length=veh_length,
        )
        pos, heading = pose.as_panda3d()
        vehicle_path.setPosHpr(*pos, heading, 0, 0)

    def remove_vehicle_node(self, vid: str):
        """Remove a vehicle node
        """
        vehicle_path = self._vehicle_nodes.get(vid, None)
        if not vehicle_path:
            logger.warning("SIM: Renderer ignoring invalid vehicle id: %s", vid)
            return
        vehicle_path.removeNode()
        del self._vehicle_nodes[vid] # 在列表中删除离开的车辆

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
        node_path.hide(RenderMasks.DRIVABLE_AREA_HIDE)
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

    # ----------- #
    # 场景测试工具
    # ----------- #
    @staticmethod
    def print_node_paths(nodepath, prefix='->') -> None:
        """定义一个递归函数来遍历和打印 node paths
        """
        print(prefix + nodepath.getName())
        for child in nodepath.getChildren():
            TSHubRenderer.print_node_paths(child, prefix + '  ')
        
    def test_spin_camera_task(self, task):
        """用于测试场景加载是否正确, 使得 camera 在 map 的中心
        """
        map_model_center = self.map_bounds.getCenter()
        map_center = (
            map_model_center.getX(), 
            map_model_center.getY(), 
            map_model_center.getZ()
        ) # 地图的中心位置

        angleDegrees = task.time * 6.0
        angleRadians = angleDegrees * (math.pi / 180.0)
        distance = 100  # Distance from the center of the model on the X-Y plane
        height = 50  # Lower the height to change the viewing angle
        cameraX = map_center[0] + distance * math.sin(angleRadians)
        cameraY = map_center[1] - distance * math.cos(angleRadians)
        cameraZ = map_center[2] + height
        self._showbase_instance.camera.setPos(cameraX, cameraY, cameraZ)
        self._showbase_instance.camera.lookAt(map_center[0], map_center[1], map_center[2])  # Adjust the camera to look at the center of the model
        return Task.cont

    # ----------- #
    # 仿真结束后关闭
    # ----------- #
    def teardown(self):
        """Clean up internal resources.
        """
        if self._root_np is not None:
            self._root_np.clearLight()
            self._root_np.removeNode()
            self._root_np = None
        self._vehicles_np = None
        for sig_id in list(self._signal_nodes):
            self.remove_signal_node(sig_id)
        self._signals_np = None
        self._road_map_np = None
        self._dashed_lines_np = None
        self._is_setup = False

    def destroy(self):
        """Destroy the renderer. Cleans up all remaining renderer resources.
        """
        self.teardown()
        self._showbase_instance.userExit() # 关闭窗口
        self._showbase_instance = None

    def __del__(self):
        self.destroy()

#     def remove_buffer(self, buffer):
#         """Remove the rendering buffer.
#         """
#         self._showbase_instance.graphicsEngine.removeWindow(buffer)


#     def reset(self):
#         """Reset the render back to initialized state."""
#         if self._vehicles_np is not None:
#             self._vehicles_np.removeNode()
#             self._vehicles_np = self._root_np.attachNewNode("vehicles")
#         if self._signals_np is not None:
#             self._signals_np.removeNode()
#             self._signals_np = self._root_np.attachNewNode("signals")
#         self._vehicle_nodes = {}
#         self._signal_nodes = {}

#     def step(self):
#         """provided for non-SMARTS uses; normally not used by SMARTS."""
#         self._showbase_instance.taskMgr.step()


#     def set_interest(self, interest_filter: re.Pattern, interest_color: Colors):
#         """Sets the color of all vehicles that have ids that match the given pattern.

#         Args:
#             interest_filter (re.Pattern): The regular expression pattern to match.
#             interest_color (Colors): The color that the vehicle should show as.
#         """
#         assert isinstance(interest_filter, re.Pattern)
#         self._interest_filter = interest_filter
#         self._interest_color = interest_color