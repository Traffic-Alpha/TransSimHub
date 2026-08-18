'''
@Author: WANG Maonan
@Date: 2026-08-15
@Description: 在 Blender 内「自动装配」tshub3d 场景 (只依赖 bpy, 在 Blender 里运行).

以前用 Blender 做高精度渲染需要人工准备 .blend (导入场景、摆相机、打光), 这里把这
三件事全部自动化: 静态场景 glb (build_scene.py 产出) + 剧集 JSON (core.export 产出) -> 完整可渲染的 Blender 场景.

坐标: 与 tshub/SUMO 一致 (Z-up, 米). build_scene.py 的 glb 由 Blender 导出,
再导入回来坐标不变, 因此相机的 eye/target 可以直接使用 tshub 世界坐标.
@LastEditTime: 2026-08-15
'''
import math
import os

import bpy
from mathutils import Vector

# 静态场景各文件 -> collection 名称 (缺文件则跳过)
STATIC_LAYERS = (
    'map', 'ground', 'road_lines', 'lane_lines',
    'buildings', 'vegetation', 'props',
)

VEHICLES_COLLECTION = 'vehicles'
AIRCRAFT_COLLECTION = 'aircraft'
CAMERA_COLLECTION = 'camera'
TEMPLATE_PREFIX = '_tmpl_'

# ---------------------------------------------------------------- #
# 打光风格 (light style)
# ---------------------------------------------------------------- #
# 一个 style 同时决定「太阳」和「天空」两个光源, 二者的比值决定画面观感:
#   sun_*  : 方向光 —— 决定阴影的方向/硬度/色温 (Sun 灯, 单位 W/m^2)
#   sky_*  : 物理天空 (Sky Texture) —— 既是背景也是环境光, 决定阴影里的补光
# 关键经验: 物理天空非常亮, sky_strength 用 1.0 会把阴影填平、整幅图发蓝发灰;
# 压低天空、保持较高的 sun/sky 比, 才有实的阴影和准的路面颜色.
#
# 字段说明:
#   elevation/rotation : 太阳高度角 / 方位角 (度)
#   sun_energy         : 太阳辐照度 (W/m^2)
#   sun_temperature    : 太阳色温 (K), 越低越暖 (日出日落 ~2500, 正午 ~6500)
#   sun_size_deg       : 太阳视角直径 (度), 越大阴影边缘越柔 (真实太阳 0.53, 阴天用大值)
#   sky_strength       : 天空 (环境光) 强度倍率
#   aerosol/ozone/air  : 大气密度 —— aerosol 越大越灰蒙 (雾霾/阴天), ozone 影响天空蓝度
#   exposure           : 该风格的曝光补偿 (stop)
LIGHT_STYLES = {
    # 晴天白日 (默认): 中高太阳, 阴影清晰, 颜色准
    'day': {
        'elevation': 48.0, 'rotation': 135.0,
        'sun_energy': 3.2, 'sun_temperature': 5800, 'sun_size_deg': 0.53,
        'sky_strength': 0.38, 'aerosol': 1.0, 'ozone': 0.8, 'exposure': 0.0,
    },
    # 正午顶光: 阴影短而硬, 对比最强 (适合看车道线/标线)
    'noon': {
        'elevation': 78.0, 'rotation': 100.0,
        'sun_energy': 3.6, 'sun_temperature': 6300, 'sun_size_deg': 0.53,
        'sky_strength': 0.42, 'aerosol': 0.8, 'ozone': 0.9, 'exposure': -0.15,
    },
    # 黄金时刻: 低角度暖光 + 长投影, 画面最"好看"
    'golden': {
        'elevation': 11.0, 'rotation': 250.0,
        'sun_energy': 2.8, 'sun_temperature': 3500, 'sun_size_deg': 0.8,
        'sky_strength': 0.55, 'aerosol': 2.5, 'ozone': 1.2, 'exposure': 0.1,
    },
    # 黄昏蓝调: 太阳贴近地平线, 几乎无方向光, 冷蓝调
    'dusk': {
        'elevation': 1.5, 'rotation': 265.0,
        'sun_energy': 1.3, 'sun_temperature': 2600, 'sun_size_deg': 1.5,
        'sky_strength': 0.9, 'aerosol': 3.0, 'ozone': 1.3, 'exposure': 0.35,
    },
    # 阴天: 无明显方向光, 全靠天空漫射 (感知任务里最常见的"平光"条件)
    'overcast': {
        'elevation': 45.0, 'rotation': 135.0,
        'sun_energy': 0.8, 'sun_temperature': 6800, 'sun_size_deg': 25.0,
        'sky_strength': 1.0, 'aerosol': 3.5, 'ozone': 1.0, 'exposure': -0.6,
    },
}
# 注: 没有 night —— 场景里没有路灯/车灯/窗光等发光体, 只压暗环境光只会得到
# 一张又黑又平的图. 要做夜景得先补发光资产 (路灯 glb + 车灯 emission 材质).



# ---------------------------------------------------------------- #
# 基础工具
# ---------------------------------------------------------------- #
def clear_scene() -> None:
    """清空场景 (工厂设置, 无默认立方体/灯光/相机)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def get_collection(name: str, link_to_scene: bool = True):
    """按名字取 collection, 没有就新建."""
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        if link_to_scene:
            bpy.context.scene.collection.children.link(coll)
    return coll


def import_glb(path: str) -> list:
    """导入一个 glb, 返回新增的对象列表."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [obj for obj in bpy.data.objects if obj not in before]


def move_to_collection(objs, coll) -> None:
    """把对象移动到指定 collection (从其它 collection 解绑)."""
    for obj in objs:
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        coll.objects.link(obj)


def disable_shadow_casting(objs) -> None:
    """Keep thin decal-like meshes visible without letting them draw dark shadow seams."""
    for obj in objs:
        if hasattr(obj, 'visible_shadow'):
            obj.visible_shadow = False
        if hasattr(obj, 'cycles_visibility'):
            obj.cycles_visibility.shadow = False


# ---------------------------------------------------------------- #
# 静态场景
# ---------------------------------------------------------------- #
def import_static_scene(glb_dir: str) -> dict:
    """导入 build_scene.py 产出的静态场景 glb, 每类一个 collection."""
    loaded = {}
    for layer in STATIC_LAYERS:
        path = os.path.join(glb_dir, f'{layer}.glb')
        if not os.path.exists(path):
            continue
        objs = import_glb(path)
        move_to_collection(objs, get_collection(layer))
        if layer in ('road_lines', 'lane_lines'):
            disable_shadow_casting(objs)
        loaded[layer] = objs
        print(f'[assembly] {layer}.glb -> {len(objs)} objects')
    if not loaded:
        raise FileNotFoundError(f'静态场景目录内没有可用的 glb: {glb_dir}')
    return loaded


# ---------------------------------------------------------------- #
# 世界环境与打光
# ---------------------------------------------------------------- #
def _set_sky_type(sky_node) -> None:
    """选一个当前 Blender 版本支持的物理天空模型.

    5.x 把 Nishita 拆成了 SINGLE/MULTIPLE_SCATTERING, 旧版本叫 NISHITA.
    """
    for sky_type in ('MULTIPLE_SCATTERING', 'NISHITA', 'HOSEK_WILKIE', 'PREETHAM'):
        try:
            sky_node.sky_type = sky_type
            return
        except TypeError:
            continue


def resolve_style(style) -> dict:
    """style 名或自定义 dict -> 完整参数 (缺省项按 'day' 补齐)."""
    cfg = dict(LIGHT_STYLES['day'])
    if isinstance(style, dict):
        cfg.update(style)
    else:
        if style not in LIGHT_STYLES:
            print(f'[assembly] 未知 light style "{style}", 回退 day. '
                  f'可选: {", ".join(LIGHT_STYLES)}')
        cfg.update(LIGHT_STYLES.get(style, {}))
    return cfg


def setup_world(style='day', apply_exposure: bool = True) -> dict:
    """按 light style 建立「物理天空 + 太阳」两个光源, 返回生效的参数.

    天空只负责环境光与背景 (sun_disc 关掉), 直射光由 Sun 灯提供 —— 这样阴影方向
    可控、噪点也远低于让天空自带太阳圆盘.
    """
    cfg = resolve_style(style)
    elevation = math.radians(cfg['elevation'])
    rotation = math.radians(cfg['rotation'])

    # --- 天空 (背景 + 环境光) --- #
    world = bpy.data.worlds.get('TshubSky') or bpy.data.worlds.new('TshubSky')
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    nodes.clear()
    # 节点/接口名会被 Blender 界面语言本地化, 一律按 type / identifier 查找
    background = nodes.new('ShaderNodeBackground')
    output = nodes.new('ShaderNodeOutputWorld')
    sky = nodes.new('ShaderNodeTexSky')
    _set_sky_type(sky)
    sky.sun_elevation = elevation
    sky.sun_rotation = rotation
    if hasattr(sky, 'sun_disc'): # 太阳由 Sun 灯提供, 天空只出环境光
        sky.sun_disc = False
    # 大气参数 (不同天空模型支持的字段不同, 有才设)
    for attr, key in (('aerosol_density', 'aerosol'), ('ozone_density', 'ozone'),
                      ('air_density', 'air')):
        if hasattr(sky, attr) and cfg.get(key) is not None:
            setattr(sky, attr, float(cfg[key]))
    background.inputs['Strength'].default_value = cfg['sky_strength']
    links.new(sky.outputs[0], background.inputs[0])
    links.new(background.outputs[0], output.inputs[0])
    bpy.context.scene.world = world

    # --- 太阳 (方向光) --- #
    sun_data = bpy.data.lights.get('TshubSun') or bpy.data.lights.new('TshubSun', type='SUN')
    sun_data.type = 'SUN'
    sun_data.energy = float(cfg['sun_energy'])
    sun_data.angle = math.radians(float(cfg.get('sun_size_deg', 0.53))) # 视角直径, 越大阴影越柔
    if hasattr(sun_data, 'use_temperature') and cfg.get('sun_temperature'):
        sun_data.use_temperature = True
        sun_data.temperature = float(cfg['sun_temperature'])
    sun = bpy.data.objects.get('TshubSun')
    if sun is None:
        sun = bpy.data.objects.new('TshubSun', sun_data)
        get_collection('lighting').objects.link(sun)
    # 太阳方向与天空一致: 先绕 Y 转到高度角, 再绕 Z 转到方位角
    sun.rotation_euler = (0.0, math.pi / 2 - elevation, rotation)

    if apply_exposure and cfg.get('exposure') is not None:
        bpy.context.scene.view_settings.exposure = float(cfg['exposure'])

    print(f'[assembly] light: sun {cfg["sun_energy"]}W @{cfg["elevation"]}° '
          f'{cfg.get("sun_temperature", "-")}K / sky {cfg["sky_strength"]} '
          f'aerosol {cfg.get("aerosol")} / exposure {cfg.get("exposure")}')
    return cfg


def setup_render(resolution=(1280, 720), samples: int = 64,
                 engine: str = 'CYCLES', denoise: bool = True,
                 exposure: float = None, view_transform: str = 'AgX',
                 look: str = 'Punchy') -> None:
    """渲染参数: 引擎 / GPU / 采样 / 分辨率 / 色彩管理.

    色彩管理默认 AgX + Punchy: 物理天空的动态范围很大, Standard 会把路面直接烧成
    死白; AgX 能压住高光, 但单用会发灰, 配 Punchy 才能把对比度和饱和度找回来。
    """
    scene = bpy.context.scene
    scene.render.engine = engine
    scene.render.resolution_x = int(resolution[0])
    scene.render.resolution_y = int(resolution[1])
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    if exposure is not None: # None = 沿用当前值 (通常由 light style 决定)
        scene.view_settings.exposure = exposure
    set_color_management(view_transform, look)

    if engine == 'CYCLES':
        scene.cycles.samples = int(samples)
        scene.cycles.use_denoising = denoise
        scene.cycles.device = 'GPU' if setup_gpu() else 'CPU'


def set_color_management(view_transform: str = 'Standard', look: str = 'None') -> None:
    """设置视图变换与 Look (不同 Blender 版本 / OCIO 配置的可选项不同, 逐个试)."""
    view_settings = bpy.context.scene.view_settings
    for candidate in (view_transform, 'Standard', 'Filmic'):
        try:
            view_settings.view_transform = candidate
            break
        except TypeError:
            continue
    for candidate in (look, f'{view_settings.view_transform} - {look}', 'None'):
        try:
            view_settings.look = candidate
            break
        except TypeError:
            continue
    print(f'[assembly] color: view_transform={view_settings.view_transform}, look={view_settings.look}')


def setup_gpu() -> bool:
    """启用 Cycles GPU (优先 OPTIX, 退回 CUDA), 返回是否成功."""
    addon = bpy.context.preferences.addons.get('cycles')
    if addon is None:
        return False
    prefs = addon.preferences
    for device_type in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = device_type
        except TypeError:
            continue
        prefs.refresh_devices()
        gpus = [d for d in prefs.devices if d.type == device_type]
        if not gpus:
            continue
        for device in prefs.devices:
            device.use = (device.type == device_type)
        print(f'[assembly] Cycles GPU: {device_type} x{len(gpus)}')
        return True
    print('[assembly] 未找到可用 GPU, 回退 CPU 渲染')
    return False


# ---------------------------------------------------------------- #
# 相机
# ---------------------------------------------------------------- #
def look_at_euler(eye, target):
    """由 (eye, target) 求 Blender 相机欧拉角 (相机看向自身 -Z, 上方为 +Y)."""
    direction = Vector(target) - Vector(eye)
    if direction.length < 1e-6:
        direction = Vector((0.0, 0.0, -1.0))
    return direction.to_track_quat('-Z', 'Y').to_euler()


def sync_cameras(camera_specs: list) -> list:
    """按相机规格创建/更新相机对象 (按 name 复用), 返回 (spec, camera 对象) 列表."""
    coll = get_collection(CAMERA_COLLECTION)
    cameras = []
    for spec in camera_specs:
        name = spec['name']
        cam = bpy.data.objects.get(name)
        if cam is None or cam.type != 'CAMERA':
            cam_data = bpy.data.cameras.new(name)
            cam = bpy.data.objects.new(name, cam_data)
            coll.objects.link(cam)
        data = cam.data
        if spec.get('ortho_size'): # 俯视正交 (BEV / 路口俯视)
            data.type = 'ORTHO'
            # rig.ortho_size 的语义是「纵向覆盖的世界尺寸」(与 Panda 的 film height 一致),
            # 所以正交尺寸要按纵向来拟合, 否则非方形画幅下覆盖范围会和 Panda 对不上.
            data.sensor_fit = 'VERTICAL'
            data.ortho_scale = float(spec['ortho_size'])
        else:
            data.type = 'PERSP'
            data.sensor_fit = 'HORIZONTAL'
            data.angle = math.radians(float(spec.get('fov_deg') or 90.0))
        data.clip_start = 0.1
        data.clip_end = 3000.0
        cam.location = Vector(spec['eye'])
        cam.rotation_euler = look_at_euler(spec['eye'], spec['target'])
        cameras.append((spec, cam))
    return cameras


def remove_cameras(keep_names=()) -> None:
    """删除不在本帧规格里的相机 (载体消失时清理)."""
    coll = bpy.data.collections.get(CAMERA_COLLECTION)
    if coll is None:
        return
    for cam in list(coll.objects):
        if cam.name not in keep_names:
            bpy.data.objects.remove(cam, do_unlink=True)


# ---------------------------------------------------------------- #
# 动态物体 (车辆 / 飞行器)
# ---------------------------------------------------------------- #
class ModelLibrary:
    """glb 模型库: 每个模型只导入一次, 之后用 collection instance 复用.

    车辆 glb 常常是多个部件 (车身/玻璃/轮胎, 各自材质贴图), 所以模板用一个未挂到
    场景的 collection 保存整棵层级, 实例化时用 Empty + instance_collection ——
    既保留材质, 又不复制网格数据.
    """

    def __init__(self, base_dir: str, yaw_offset_deg: float = 0.0) -> None:
        self.base_dir = base_dir
        self.yaw_offset = math.radians(yaw_offset_deg)
        self._templates = {}
        self._instances = {}

    def _template(self, model_rel: str):
        if model_rel in self._templates:
            return self._templates[model_rel]
        path = os.path.join(self.base_dir, model_rel)
        if not os.path.exists(path):
            print(f'[assembly] 缺少模型: {path}')
            self._templates[model_rel] = None
            return None
        objs = import_glb(path)
        tmpl = bpy.data.collections.new(f'{TEMPLATE_PREFIX}{model_rel}') # 不挂到场景 -> 模板本身不渲染
        move_to_collection(objs, tmpl)
        self._templates[model_rel] = tmpl
        print(f'[assembly] model {model_rel} -> {len(objs)} objects')
        return tmpl

    def sync(self, objects: dict, collection_name: str) -> None:
        """按本帧数据增删改实例. objects: {id: {model, position, heading}}."""
        coll = get_collection(collection_name)
        for obj_id in list(self._instances):
            if obj_id not in objects:
                bpy.data.objects.remove(self._instances.pop(obj_id), do_unlink=True)

        for obj_id, info in objects.items():
            inst = self._instances.get(obj_id)
            if inst is None:
                tmpl = self._template(info['model'])
                if tmpl is None:
                    continue
                inst = bpy.data.objects.new(obj_id, None)
                inst.instance_type = 'COLLECTION'
                inst.instance_collection = tmpl
                inst.empty_display_size = 0.5
                coll.objects.link(inst)
                self._instances[obj_id] = inst
            pos = info['position']
            # 模型 pivot 在车底中心 -> 直接放到地面高度, 不再抬升半个车高
            inst.location = (float(pos[0]), float(pos[1]), float(pos[2]) if len(pos) > 2 else 0.0)
            inst.rotation_euler = (0.0, 0.0, float(info['heading']) + self.yaw_offset)

    def clear(self) -> None:
        for obj in self._instances.values():
            bpy.data.objects.remove(obj, do_unlink=True)
        self._instances.clear()
