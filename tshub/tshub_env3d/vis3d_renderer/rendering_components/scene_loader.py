'''
@Author: WANG Maonan
@Date: 2024-07-12 21:38:26
@Description: 场景加载相关的方法 (用于初始化场景)
@LastEditTime: 2024-07-14 20:25:46
'''
from pathlib import Path
from loguru import logger
from panda3d.core import (
    Shader,
    SamplerState,
    ShaderTerrainMesh,
    Geom,
    GeomLinestrips,
    GeomNode,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexReader,
    GeomVertexWriter,
    AmbientLight,
    CardMaker,
    Vec4,
    DirectionalLight
)
from ...vis3d_utils.masks import CamMask
from ...vis3d_utils.colors import SceneColors, Colors

class SceneLoader(object):
    ROAD_MAP_NODE_NAME = "road_map"
    MAP_FILENAME = "map.glb"
    TERRAIN_FILENAME = "ground.glb"
    LANE_FILENAME = "lane_lines.glb"
    ROAD_FILENAME = "road_lines.glb"

    def __init__(
            self, 
            root_np,
            showbase_instance,
            skybox_dir:str,
            terrain_dir:str,
            scenario_glb_dir:str,
            map_road_lane_glsl_dir:str
        ) -> None:
        self.skybox_dir = Path(skybox_dir) # the skybox path model
        self.terrain_dir = Path(terrain_dir) # the path for terrain model
        self.scenario_glb_dir = Path(scenario_glb_dir) # 场景地图的路径
        self.map_road_lane_glsl_dir = Path(map_road_lane_glsl_dir) # lane 的 glsl 文件
        self._showbase_instance = showbase_instance # panda3d ShowBase (所有模型都挂载在这上面)
        self._root_np = root_np # 用于挂载 node

        # load map 之后场景的基础信息
        self.map_radius = None
        self.map_center = None
    

    def initialize_scene(self, use_render_pipeline=False) -> None:
        logger.info("SIM: Starting TSHub3D scene initialization.")
        self.load_map()
        self.load_road_lines()
        self.load_lane_lines()
        if not use_render_pipeline:
            self.load_sky_box()
            self.load_flat_terrain()
            self.setup_lighting()

        return self.map_radius, self.map_center


    def load_map(self) -> None:
        """Load map & 并获得中心位置
        """
        map_path = self.scenario_glb_dir / self.MAP_FILENAME
        logger.info(f"SIM: 加载场景地图, {map_path}.")
        try:
            map_np = self._showbase_instance.loader.loadModel(map_path, noCache=True)
            node_path = self._root_np.attachNewNode(self.ROAD_MAP_NODE_NAME)
            map_np.reparent_to(node_path)
            # 定义 mask
            node_path.hide(CamMask.AllOn)
            node_path.show(CamMask.MapMask) # 只给部分 camera 展示
            # 设置路面的颜色
            node_path.setColor(SceneColors.Road.value)
            map_bounds = map_np.getBounds()
            self.map_radius = map_bounds.getRadius()
            map_model_center = map_bounds.getCenter()
            self.map_center = (
                map_model_center.getX(), 
                map_model_center.getY(), 
                map_model_center.getZ()
            )
            logger.info(f"SIM: 场景地图加载成功.")
            logger.info(f"SIM: 地图的中心 {self.map_center}.")
            logger.info(f"SIM: 地图的半径 {self.map_radius}.")
        except Exception as e:
            print(f"Error loading map: {e}")
        return map_np


    def load_road_lines(self):
        """Road lines (solid, yellow)
        """
        road_lines_path = self.scenario_glb_dir / SceneLoader.ROAD_FILENAME
        logger.info(f"SIM: 加载道路边界线, {road_lines_path}.")
        if road_lines_path.exists():
            road_lines_np = self._load_line_data(road_lines_path, "road_lines")
            solid_lines_np = self._root_np.attachNewNode(road_lines_np)
            # 定义 mask
            solid_lines_np.hide(CamMask.AllOn)
            solid_lines_np.show(CamMask.MapMask) # 只给部分 camera 展示
            # 设置车道边线的颜色
            solid_lines_np.setColor(SceneColors.EdgeDivider.value)
            solid_lines_np.setRenderModeThickness(2) # 设置显示的粗细
            logger.info(f"SIM: 加载道路线成功.")
        return solid_lines_np

    
    def load_lane_lines(self):
        """Lane lines (dashed, white)
        """
        lane_lines_path = self.scenario_glb_dir / SceneLoader.LANE_FILENAME
        logger.info(f"SIM: 加载车道线, {lane_lines_path}.")
        if lane_lines_path.exists():
            lane_lines_np = self._load_line_data(lane_lines_path, "lane_lines")
            dashed_lines_np = self._root_np.attachNewNode(lane_lines_np)
            # 定义 mask
            dashed_lines_np.hide(CamMask.AllOn)
            dashed_lines_np.show(CamMask.MapMask) # 只给部分 camera 展示
            # 设置车道线的颜色
            dashed_lines_np.setColor(SceneColors.LaneDivider.value)
            dashed_lines_np.setRenderModeThickness(2)
            
            dashed_line_shader = Shader.load(
                Shader.SL_GLSL,
                vertex=self.map_road_lane_glsl_dir/"dashed_line_shader.vert",
                fragment=self.map_road_lane_glsl_dir/"dashed_line_shader.frag",
            )
            dashed_lines_np.setShader(dashed_line_shader, priority=20)
            dashed_lines_np.setShaderInput(
                "iResolution", self._showbase_instance.getSize()
            )
            logger.info(f"SIM: 加载车道线成功.")
            return dashed_lines_np


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


    def setup_lighting(
            self, 
            ambient_color: Vec4 = Vec4(0.25, 0.25, 0.25, 1), 
            directional_color: Vec4 = Vec4(1, 1, 1, 1), 
            light_temperature: int = 6000, 
            light_height: int = 200
        ) -> None:
        """设置光照
        """
        logger.info("SIM: 设置光照.")
        # Set up ambient light
        ambient_light = AmbientLight('ambientLight')
        ambient_light.setColor(ambient_color)
        ambient_light.set_color_temperature(light_temperature)
        ambient_light_node_path = self._root_np.attachNewNode(ambient_light)
        self._root_np.setLight(ambient_light_node_path)
        
        # Set up directional light
        directional_light = DirectionalLight('directionalLight')
        directional_light.setColor(directional_color)
        directional_light.set_color_temperature(light_temperature)
        directional_light_node_path = self._root_np.attachNewNode(directional_light)
        directional_light_node_path.setPos(
            self.map_center[0]-self.map_radius,
            self.map_center[1]-self.map_radius,
            light_height
        )
        directional_light_node_path.lookAt(self.map_center) # 照向地图中心
        self._root_np.setLight(directional_light_node_path)
        self._root_np.setShaderAuto() # 场景开启阴影接收
        
    def load_sky_box(self) -> None:
        """初始化环境的时候, 设置 skybox
        """
        logger.info(f"SIM: 初始化 Skybox.")
        # 加载 skybox 模型
        skybox = self._showbase_instance.loader.loadModel(self.skybox_dir/"skybox.bam")
        skybox_scale = self.map_radius * 2 # 设置 skybox 的大小
        skybox.set_scale(skybox_scale)
        # 设置 skybox 的 mask
        skybox.hide(CamMask.AllOn)
        skybox.show(CamMask.SkyBoxMask) # 只给部分 camera 展示

        # 设置 skybox 纹理
        skybox_texture = self._showbase_instance.loader.loadTexture(self.skybox_dir/"skybox.jpg")
        skybox_texture.set_minfilter(SamplerState.FT_linear)
        skybox_texture.set_magfilter(SamplerState.FT_linear)
        skybox_texture.set_wrap_u(SamplerState.WM_repeat)
        skybox_texture.set_wrap_v(SamplerState.WM_mirror)
        skybox_texture.set_anisotropic_degree(16)
        skybox.set_texture(skybox_texture)

        skybox_shader = Shader.load(
            Shader.SL_GLSL,
            self.skybox_dir/"skybox.vert.glsl",
            self.skybox_dir/"skybox.frag.glsl"
        )
        skybox.set_shader(skybox_shader)
        skybox.reparentTo(self._root_np)
        skybox.setPos(
            self.map_center[0], 
            self.map_center[1], 
            100
        )

        # Ensure the skybox is always rendered behind everything else
        skybox.set_bin('background', 0) # 确保 skybox 首先被渲染
        skybox.set_depth_write(False) # skybox 不会遮挡任意的对象
        skybox.set_compass()  # This makes the skybox fixed relative to the camera's rotation

    def load_flat_terrain(self):
        """直接加载生成的平面 terrain
        """
        ground_path = self.scenario_glb_dir / SceneLoader.TERRAIN_FILENAME
        logger.info(f"SIM: 加载地平面, {ground_path}.")
        if ground_path.exists():
            ground_np = self._showbase_instance.loader.loadModel(ground_path, noCache=True)
            node_path = self._root_np.attachNewNode("ground_node")
            ground_np.reparent_to(node_path) # 将 ground_np（地面模型的 NodePath）作为子节点附加到了 node_path 上
            # 定义 mask
            ground_np.hide(CamMask.AllOn)
            ground_np.show(CamMask.GroundMask) # 只给部分 camera 展示
            # 设置地面的颜色
            ground_np.set_bin('background', 1)  # Ensure terrain is rendered after skybox
            ground_np.set_depth_write(False) 

        return ground_np

    # TODO, 可以尝试加入地面的纹理
    # def load_terrain(self) -> None:
    #     self.terrain_node = ShaderTerrainMesh()

    #     # Set a heightfield, the heightfield should be a 16-bit png and
    #     # have a quadratic size of a power of two.
    #     heightfield = self._showbase_instance.loader.loadTexture(self.terrain_dir/"heightfield.png")
    #     heightfield.wrap_u = SamplerState.WM_clamp
    #     heightfield.wrap_v = SamplerState.WM_clamp
    #     self.terrain_node.heightfield = heightfield

    #     # Set the target triangle width. For a value of 10.0 for example,
    #     # the terrain will attempt to make every triangle 10 pixels wide on screen.
    #     self.terrain_node.target_triangle_width = 10.0

    #     # Generate the terrain
    #     self.terrain_node.generate()

    #     # Attach the terrain to the main scene and set its scale. With no scale
    #     # set, the terrain ranges from (0, 0, 0) to (1, 1, 1)
    #     self.terrain = self._root_np.attach_new_node(self.terrain_node)
    #     self.terrain.set_scale(
    #         self.map_radius*5, 
    #         self.map_radius*5, 
    #         1
    #     )
    #     self.terrain.set_pos(
    #         self.map_center[0]-2*self.map_radius, 
    #         self.map_center[1]-2*self.map_radius, 
    #         self.map_center[2] - 3 # 将 terrain 的高度稍微设置的低一些, 避免 road 被遮挡
    #     )
        
    #     # Set a shader on the terrain. The ShaderTerrainMesh only works with
    #     # an applied shader. You can use the shaders used here in your own application
    #     terrain_shader = Shader.load(
    #         Shader.SL_GLSL, 
    #         self.terrain_dir/"terrain.vert.glsl",
    #         self.terrain_dir/"terrain.frag.glsl"
    #     )
    #     self.terrain.set_shader(terrain_shader)
    #     self.terrain.set_shader_input(
    #         "camera", 
    #         self._showbase_instance.camera
    #     )

    #     # Set some texture on the terrain
    #     grass_tex = self._showbase_instance.loader.loadTexture(self.terrain_dir/"ground.png")
    #     grass_tex.set_minfilter(SamplerState.FT_linear_mipmap_linear)
    #     grass_tex.set_anisotropic_degree(16)
    #     self.terrain.set_texture(grass_tex)