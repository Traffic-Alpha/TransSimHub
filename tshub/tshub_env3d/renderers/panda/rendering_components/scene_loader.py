'''
@Author: WANG Maonan
@Date: 2024-07-12 21:38:26
@Description: 场景加载相关的方法 (用于初始化场景)
LastEditTime: 2025-07-28 22:54:28
'''
from pathlib import Path
from loguru import logger
from panda3d.core import (
    Shader,
    AmbientLight,
    Vec3,
    Vec4,
    DirectionalLight,
)
from tshub.tshub_env3d.renderers.panda.masks import CamMask
from tshub.tshub_env3d.renderers.panda.segmentation import tag_seg

class SceneLoader(object):
    ROAD_MAP_NODE_NAME = "road_map"
    MAP_FILENAME = "map.glb"
    TERRAIN_FILENAME = "ground.glb"
    LANE_FILENAME = "lane_lines.glb"
    ROAD_FILENAME = "road_lines.glb"
    BUILDING_FILENAME = "buildings.glb"
    VEGETATION_FILENAME = "vegetation.glb"
    PROPS_FILENAME = "props.glb"
    SKY_COLORS = {
        "day": {
            "horizon": (0.68, 0.78, 0.86),
            "zenith": (0.36, 0.58, 0.82),
            "clear": (0.62, 0.74, 0.86, 1),
        },
        "dust": {
            "horizon": (0.78, 0.70, 0.58),
            "zenith": (0.53, 0.62, 0.72),
            "clear": (0.72, 0.66, 0.56, 1),
        },
    }

    def __init__(
            self, 
            root_np,
            showbase_instance,
            skybox_dir:str,
            scenario_glb_dir:str,
            sky:str = 'day' # 天空: 'day' / 'dust' (程序化 city-builder 渐变)
        ) -> None:
        self.sky = sky
        self.skybox_dir = Path(skybox_dir) # the skybox path model
        self.scenario_glb_dir = Path(scenario_glb_dir) # 场景地图的路径
        self._showbase_instance = showbase_instance # panda3d ShowBase (所有模型都挂载在这上面)
        self._root_np = root_np # 用于挂载 node

        # load map 之后场景的基础信息
        self.map_radius = None
        self.map_center = None

    def initialize_scene(self) -> None:
        logger.info("SIM: Starting TSHub3D scene initialization.")
        self.load_map()
        self.load_road_lines()
        self.load_lane_lines()
        self.load_flat_terrain()
        self.load_buildings()
        self.load_vegetation()
        self.load_props()
        self.load_sky_box()
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
            tag_seg(node_path, 'road') # 语义分割: 路面
            # 路面/路缘颜色来自 glb 材质 (Blender 示意风格纯色), 不再用 setColor 覆盖
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


    def load_buildings(self):
        """加载建筑 (env 场景的 buildings.glb; 不存在则跳过). 按 mesh 加载 + MapMask.
        """
        path = self.scenario_glb_dir / SceneLoader.BUILDING_FILENAME
        if not path.exists():
            return None
        logger.info(f"SIM: 加载建筑, {path}.")
        model = self._showbase_instance.loader.loadModel(path, noCache=True)
        buildings_np = self._root_np.attachNewNode("buildings")
        model.reparent_to(buildings_np)
        buildings_np.hide(CamMask.AllOn)
        buildings_np.show(CamMask.MapMask) # 环境几何
        tag_seg(buildings_np, 'building') # 语义分割: 建筑
        # 外墙颜色来自 glb 材质 (Blender 示意风格浅灰灰模), 不再用 setColor 覆盖
        logger.info(f"SIM: 建筑加载成功.")
        return buildings_np

    def load_vegetation(self):
        """加载树木/植被资产 (vegetation.glb; 不存在则跳过)."""
        path = self.scenario_glb_dir / SceneLoader.VEGETATION_FILENAME
        if not path.exists():
            return None
        logger.info(f"SIM: 加载植被, {path}.")
        model = self._showbase_instance.loader.loadModel(path, noCache=True)
        vegetation_np = self._root_np.attachNewNode("vegetation")
        model.reparent_to(vegetation_np)
        vegetation_np.hide(CamMask.AllOn)
        vegetation_np.show(CamMask.MapMask)
        tag_seg(vegetation_np, 'ground')
        logger.info(f"SIM: 植被加载成功.")
        return vegetation_np

    def load_props(self):
        """加载路边小物件 (props.glb; 不存在则跳过)."""
        path = self.scenario_glb_dir / SceneLoader.PROPS_FILENAME
        if not path.exists():
            return None
        logger.info(f"SIM: 加载路边小物件, {path}.")
        model = self._showbase_instance.loader.loadModel(path, noCache=True)
        props_np = self._root_np.attachNewNode("props")
        model.reparent_to(props_np)
        props_np.hide(CamMask.AllOn)
        props_np.show(CamMask.MapMask)
        tag_seg(props_np, 'pole')  # 语义分割: 路灯/长椅等街道设施
        logger.info(f"SIM: 路边小物件加载成功.")
        return props_np

    def load_road_lines(self):
        """Road edge lines (现在是 ribbon mesh, 纯色黄). 按 mesh 加载 (与 load_map 一致).
        """
        road_lines_path = self.scenario_glb_dir / SceneLoader.ROAD_FILENAME
        logger.info(f"SIM: 加载道路边界线, {road_lines_path}.")
        if not road_lines_path.exists():
            return None
        model = self._showbase_instance.loader.loadModel(road_lines_path, noCache=True)
        solid_lines_np = self._root_np.attachNewNode("road_lines")
        model.reparent_to(solid_lines_np)
        solid_lines_np.hide(CamMask.AllOn)
        solid_lines_np.show(CamMask.MapMask) # 只给部分 camera 展示
        tag_seg(solid_lines_np, 'road_edge') # 语义分割: 道路边界线/路缘 (单独一类)
        logger.info(f"SIM: 加载道路线成功.")
        return solid_lines_np


    def load_lane_lines(self):
        """Lane divider lines (现在是 ribbon mesh, 纯色白). 按 mesh 加载 (与 load_map 一致).
        """
        lane_lines_path = self.scenario_glb_dir / SceneLoader.LANE_FILENAME
        logger.info(f"SIM: 加载车道线, {lane_lines_path}.")
        if not lane_lines_path.exists():
            return None
        model = self._showbase_instance.loader.loadModel(lane_lines_path, noCache=True)
        dashed_lines_np = self._root_np.attachNewNode("lane_lines")
        model.reparent_to(dashed_lines_np)
        dashed_lines_np.hide(CamMask.AllOn)
        dashed_lines_np.show(CamMask.MapMask) # 只给部分 camera 展示
        tag_seg(dashed_lines_np, 'lane') # 语义分割: 车道分隔线 (单独一类)
        logger.info(f"SIM: 加载车道线成功.")
        return dashed_lines_np


    def setup_lighting(
            self, 
            ambient_color: Vec4 = Vec4(0.80, 0.82, 0.86, 1),   # 平摊补光 (填充阴影, 与 IBL 一起提亮)
            directional_color: Vec4 = Vec4(1.30, 1.26, 1.17, 1),  # 略暖的主方向光 (太阳, 加强)
            light_height: int = 100,
            light_direction: Vec3 = None  # 可选光照方向
        ) -> None:
        """设置光照
        """
        logger.info("SIM: 设置光照.")
        
        # 确保 map_center 是 Vec3 类型
        if isinstance(self.map_center, tuple):
            map_center = Vec3(*self.map_center)  # 将 tuple 转换为 Vec3
        else:
            map_center = Vec3(self.map_center)  # 确保是 Vec3
        
        # 环境光
        # 注: 不要在 setColor 之后调 set_color_temperature —— Panda 里它会把颜色覆盖成该色温的
        # 满强度值 (~1.0), 冲掉这里精心调的暗光强度, 导致整体过亮/颜色发白 (过曝观感).
        # 色温倾向已直接编码进 setColor 的 RGB (环境略冷, 方向略暖).
        ambient_light = AmbientLight('ambientLight')
        ambient_light.setColor(ambient_color)
        ambient_light_node_path = self._root_np.attachNewNode(ambient_light)
        self._root_np.setLight(ambient_light_node_path)

        # 定向光
        directional_light = DirectionalLight('directionalLight')
        directional_light.setColor(directional_color)
        directional_light_node_path = self._root_np.attachNewNode(directional_light)

        # 设置光源位置
        if light_direction is None:
            light_direction = Vec3(-1, -1, -0.5)  # 默认斜45度方向
        light_direction.normalize()

        light_pos = map_center - light_direction * self.map_radius
        light_pos.z = light_height  # 设置高度

        directional_light_node_path.setPos(light_pos)
        directional_light_node_path.lookAt(map_center)  # 朝向场景中心

        self._root_np.setLight(directional_light_node_path)
        self._root_np.setShaderAuto()

    def load_sky_box(self) -> None:
        """初始化程序化 city-builder 天空.
        """
        logger.info(f"SIM: 初始化 Skybox.")
        sky_colors = self.SKY_COLORS.get(self.sky)
        if sky_colors is None:
            raise ValueError(f"SIM: 不支持的天空类型: {self.sky!r}, 可选: {sorted(self.SKY_COLORS)}")
        self._showbase_instance.setBackgroundColor(*sky_colors["clear"])
        # 加载 skybox 模型
        skybox = self._showbase_instance.loader.loadModel(self.skybox_dir/"skybox.bam")
        skybox_scale = self.map_radius * 2 # 设置 skybox 的大小
        skybox.set_scale(skybox_scale)
        # 设置 skybox 的 mask
        skybox.hide(CamMask.AllOn)
        skybox.show(CamMask.SkyBoxMask) # 只给部分 camera 展示
        tag_seg(skybox, 'sky') # 语义分割: 天空

        skybox_shader = Shader.load(
            Shader.SL_GLSL,
            self.skybox_dir/"skybox.vert.glsl",
            self.skybox_dir/"skybox.frag.glsl"
        )
        skybox.set_shader(skybox_shader)
        skybox.set_shader_input("sky_horizon_color", Vec3(*sky_colors["horizon"]))
        skybox.set_shader_input("sky_zenith_color", Vec3(*sky_colors["zenith"]))
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

        # IBL: 用与天空一致的 cubemap 给 simplepbr 设环境光照, 让明亮天空真正照亮地面/车辆
        # (解决「天空亮但地面/车暗」的不一致; cubemap 由 skybox/gen_env_cubemap.py 生成).
        env_dir = self.skybox_dir / f"env_{self.sky}"
        pipeline = getattr(self._showbase_instance, 'pipeline', None)
        if pipeline is not None and env_dir.exists():
            from simplepbr import EnvMap
            pipeline.env_map = EnvMap.from_file_path(str(env_dir / "#.png"))
            logger.info(f"SIM: 已启用 IBL 环境光照 (env_{self.sky}).")

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
            tag_seg(node_path, 'ground') # 语义分割: 地面/草地
            # 设置地面的颜色
            ground_np.set_bin('background', 1)  # Ensure terrain is rendered after skybox
            ground_np.set_depth_write(False) 

        return ground_np
