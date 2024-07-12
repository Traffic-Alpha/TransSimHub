'''
@Author: WANG Maonan
@Date: 2024-07-12 21:38:26
@Description: 场景加载相关的方法 (用于初始化场景)
TODO
1. 加载灯光也需要在这里完成
2. terrain 可以使用多个 terrain 拼接而成
3. skybox 需要进一步优化
4. 加入 logger, 方便用户判断哪些是加载了
@LastEditTime: 2024-07-13 03:23:42
'''
from pathlib import Path
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
)

from ...vis3d_utils.colors import SceneColors

class SceneLoader(object):
    MAP_FILENAME = "map.glb"
    ROAD_MAP_NODE_NAME = "road_map"

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
    

    def init_scene(self) -> None:
        self.load_map()
        self.load_road_lines()
        self.load_lane_lines()
        # self.load_sky_box()
        # self.load_terrain()

        return self.map_radius, self.map_center


    def load_map(self) -> None:
        """Load map & 并获得中心位置
        """
        map_path = self.scenario_glb_dir / self.MAP_FILENAME
        try:
            map_np = self._showbase_instance.loader.loadModel(map_path, noCache=True)
            node_path = self._root_np.attachNewNode(self.ROAD_MAP_NODE_NAME)
            map_np.reparent_to(node_path)
            # Ensure SceneColors.Road.value is defined or handle it appropriately
            node_path.setColor(SceneColors.Road.value)
            map_bounds = map_np.getBounds()
            self.map_radius = map_bounds.getRadius()
            map_model_center = map_bounds.getCenter()
            self.map_center = (
                map_model_center.getX(), 
                map_model_center.getY(), 
                map_model_center.getZ()
            )
        except Exception as e:
            print(f"Error loading map: {e}")
        return map_np


    def load_road_lines(self):
        """Road lines (solid, yellow)
        """
        road_lines_path = self.scenario_glb_dir / "road_lines.glb"
        if road_lines_path.exists():
            road_lines_np = self._load_line_data(road_lines_path, "road_lines")
            solid_lines_np = self._root_np.attachNewNode(road_lines_np)
            solid_lines_np.setColor(SceneColors.EdgeDivider.value)
            solid_lines_np.setRenderModeThickness(2) # 设置显示的粗细
        return solid_lines_np

    
    def load_lane_lines(self):
        # Lane lines (dashed, white)
        lane_lines_path = self.scenario_glb_dir / "lane_lines.glb"
        if lane_lines_path.exists():
            lane_lines_np = self._load_line_data(lane_lines_path, "lane_lines")
            dashed_lines_np = self._root_np.attachNewNode(lane_lines_np)
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


    def load_sky_box(self) -> None:
        """初始化环境的时候, 设置 skybox
        """
        # 加载 skybox 模型
        skybox = self._showbase_instance.loader.loadModel(self.skybox_dir/"skybox.bam")
        skybox_scale = self.map_radius * 2 # 设置 skybox 的大小
        skybox.set_scale(skybox_scale)

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
            self.map_center[2] - self.map_radius*0.9 # TODO, 关于高度的设置
        )
        # skybox.setH(0)

        # Ensure the skybox is always rendered behind everything else
        skybox.set_bin('background', 0)
        skybox.set_depth_write(False)
        skybox.set_compass()  # This makes the skybox fixed relative to the camera's rotation

    def load_terrain(self):
        self.terrain_node = ShaderTerrainMesh()

        # Set a heightfield, the heightfield should be a 16-bit png and
        # have a quadratic size of a power of two.
        heightfield = self._showbase_instance.loader.loadTexture(self.terrain_dir/"heightfield.png")
        heightfield.wrap_u = SamplerState.WM_clamp
        heightfield.wrap_v = SamplerState.WM_clamp
        self.terrain_node.heightfield = heightfield

        # Set the target triangle width. For a value of 10.0 for example,
        # the terrain will attempt to make every triangle 10 pixels wide on screen.
        self.terrain_node.target_triangle_width = 10.0

        # Generate the terrain
        self.terrain_node.generate()

        # Attach the terrain to the main scene and set its scale. With no scale
        # set, the terrain ranges from (0, 0, 0) to (1, 1, 1)
        self.terrain = self._root_np.attach_new_node(self.terrain_node)
        self.terrain.set_scale(
            self.map_radius*2, 
            self.map_radius*2, 
            1
        )
        self.terrain.set_pos(
            self.map_center[0]-self.map_radius, 
            self.map_center[1]-self.map_radius, 
            self.map_center[2] - 3 # 将 terrain 的高度稍微设置的低一些, 避免 road 被遮挡
        )

        # Set a shader on the terrain. The ShaderTerrainMesh only works with
        # an applied shader. You can use the shaders used here in your own application
        terrain_shader = Shader.load(
            Shader.SL_GLSL, 
            self.terrain_dir/"terrain.vert.glsl",
            self.terrain_dir/"terrain.frag.glsl"
        )
        self.terrain.set_shader(terrain_shader)
        self.terrain.set_shader_input(
            "camera", 
            self._showbase_instance.camera
        )

        # Set some texture on the terrain
        grass_tex = self._showbase_instance.loader.loadTexture(self.terrain_dir/"ground.png")
        grass_tex.set_minfilter(SamplerState.FT_linear_mipmap_linear)
        grass_tex.set_anisotropic_degree(16)
        self.terrain.set_texture(grass_tex)