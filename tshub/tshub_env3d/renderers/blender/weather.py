'''
@Author: WANG Maonan
@Date: 2026-08-15
@Description: 天气效果 (雾 / 雨 / 雪), 在 Blender 内运行.

设计取舍: 天气**不做物理仿真**, 只保证「相机画面里看得出来」, 且几乎不增加渲染时间.
三种手段, 由弱到强各司其职:

1. 光照修正 —— 天气会顺带改写 light style (下雨天太阳弱、天空散射强), 由
   `WEATHER_STYLES[x]['light']` 合并到 scene_assembly.LIGHT_STYLES 上;
2. 材质修正 —— 湿路面 (变暗 + 变光滑, 反射天空) / 积雪 (地面路面变白),
   这是"下雨/下雪"最强的一条视觉线索, 且只改材质, 零渲染开销;
3. 画面合成 —— 深度雾 (Mist pass 按距离混合雾色) + 雨丝/雪花叠加层.
   都在合成器里做: 雾是深度正确的, 雨雪是屏幕空间的程序化贴图, Cycles 采样不变,
   所以开天气几乎不影响渲染耗时 (实测 <5%).

为什么不用体积雾 (Volume Scatter): Cycles 体积采样会让每帧慢 2 倍以上, 而这些相机
视角下与深度雾的观感差别很小 —— 不值当.

注意: 雨丝/雪花是屏幕空间叠加, **不会出现在语义分割 pass 里** —— 对做感知数据增强
来说这正是想要的 (标签不变, 输入退化).

Blender 5 API 变化: 合成器不再是 `scene.node_tree`, 而是挂在
`scene.compositing_node_group` 上的一个 CompositorNodeTree 节点组 (用 NodeGroupOutput
输出); 混合节点统一成了 ShaderNodeMix.
@LastEditTime: 2026-08-15
'''
import math

import bpy
import numpy as np

COMPOSITOR_GROUP = 'TshubComposite' # 天气与 depth 输出共用这一个合成器节点组
OVERLAY_IMAGE = 'TshubWeatherOverlay'
OVERLAY_NODE = 'WeatherOverlay'

# 天气预设.
#   light      : 覆盖到 light style 上的参数 (见 scene_assembly.LIGHT_STYLES)
#   fog        : 深度雾 —— color 雾色, start/depth 起雾距离与浓到饱和的距离 (米), strength 上限
#   wet        : 路面湿滑程度 0~1 (变暗 + 噪声驱动的斑驳反光)
#   overlay    : 屏幕空间雨丝层 {count, length, angle, strength}
WEATHER_STYLES = {
    'clear': {},
    # 雾天: 能见度低, 光很平; 不加粒子层
    'fog': {
        'light': {'sun_energy': 1.0, 'sun_size_deg': 20.0, 'sky_strength': 1.1,
                  'aerosol': 5.0, 'exposure': -0.3},
        'fog': {'color': (0.80, 0.82, 0.84), 'start': 8.0, 'depth': 130.0, 'strength': 1.0},
    },
    # 雨天: 阴沉 + 湿滑路面 + 斜向雨丝
    'rain': {
        'light': {'sun_energy': 0.5, 'sun_size_deg': 25.0, 'sky_strength': 0.85,
                  'sun_temperature': 6800, 'aerosol': 3.0, 'exposure': -0.55},
        # 雨天的雾要克制: 起雾远一点、上限低一点, 否则路面被雾提亮, 反而不像下雨
        'fog': {'color': (0.55, 0.58, 0.62), 'start': 40.0, 'depth': 500.0, 'strength': 0.45},
        'wet': 0.9,
        'overlay': {'count': 2200, 'length': 60, 'angle': 14.0, 'strength': 0.45},
    },
}

# 湿路面涉及的静态图层
_ROAD_LAYERS = ('map', 'road_lines', 'lane_lines')


# ---------------------------------------------------------------- #
# 材质工具 (Blender 界面语言可能是中文, 节点/接口一律按 type / identifier 找)
# ---------------------------------------------------------------- #
def _principled(material):
    if not material or not material.node_tree:
        return None
    for node in material.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            return node
    return None


def _socket(node, identifier: str):
    for socket in node.inputs:
        if socket.identifier == identifier:
            return socket
    return None


def _out_socket(node, identifier: str):
    for socket in node.outputs:
        if socket.identifier == identifier:
            return socket
    return None


def _materials_in(layers) -> list:
    seen, materials = set(), []
    for layer in layers:
        coll = bpy.data.collections.get(layer)
        if coll is None:
            continue
        for obj in coll.all_objects:
            for slot in getattr(obj, 'material_slots', []):
                mat = slot.material
                if mat is not None and mat.name not in seen:
                    seen.add(mat.name)
                    materials.append(mat)
    return materials


NOISE_NODE = 'TshubWetNoise'


def _wet_roughness_noise(bsdf, node_tree, rough_min: float, rough_max: float) -> None:
    """用世界坐标噪声驱动粗糙度, 做出「有的地方积水锃亮、有的地方只是潮」的斑驳感.

    关键: 湿路面**不能**是一整片均匀的低粗糙度 —— 平坦路面上均匀镜面反射看起来
    就是一块金属板. 真实的湿沥青反光是斑驳的, 所以这里让粗糙度随位置起伏.
    """
    if node_tree.nodes.get(NOISE_NODE) is not None:
        return
    geometry = node_tree.nodes.new('ShaderNodeNewGeometry')
    geometry.location = (-900, -300)
    noise = node_tree.nodes.new('ShaderNodeTexNoise')
    noise.name = NOISE_NODE
    noise.location = (-700, -300)
    _socket(noise, 'Scale').default_value = 0.35 # 世界坐标单位是米 -> 几米一块水洼
    detail = _socket(noise, 'Detail')
    if detail is not None:
        detail.default_value = 4.0
    # Fac(0~1) -> rough_min ~ rough_max, 用 MULTIPLY_ADD (Math 的接口按下标最稳)
    remap = node_tree.nodes.new('ShaderNodeMath')
    remap.operation = 'MULTIPLY_ADD'
    remap.location = (-500, -300)
    remap.inputs[1].default_value = rough_max - rough_min
    remap.inputs[2].default_value = rough_min

    node_tree.links.new(geometry.outputs['Position'], _socket(noise, 'Vector'))
    node_tree.links.new(noise.outputs['Fac'], remap.inputs[0])
    node_tree.links.new(remap.outputs[0], _socket(bsdf, 'Roughness'))


def apply_road_wetness(amount: float) -> int:
    """湿路面: 略微变暗 + 斑驳的反光 —— 「在下雨」最强的一条视觉线索."""
    amount = max(0.0, min(1.0, float(amount)))
    count = 0
    for mat in _materials_in(_ROAD_LAYERS):
        bsdf = _principled(mat)
        if bsdf is None:
            continue
        base = _socket(bsdf, 'Base Color')
        rough = _socket(bsdf, 'Roughness')
        if base is not None:
            r, g, b, a = base.default_value
            darken = 1.0 - 0.32 * amount # 别压太狠: 又暗又亮的镜面才像金属
            base.default_value = (r * darken, g * darken, b * darken, a)
        if rough is not None:
            dry = float(rough.default_value)
            # 积水处最亮 (0.12), 只是潮湿处仍然偏粗糙 -> 反光被打散
            _wet_roughness_noise(bsdf, mat.node_tree,
                                 rough_min=0.12 + 0.10 * (1 - amount),
                                 rough_max=dry * (1.0 - 0.45 * amount))
        count += 1
    print(f'[weather] wet road: {count} materials (amount={amount})')
    return count


# ---------------------------------------------------------------- #
# 屏幕空间粒子层 (雨丝 / 雪花), 用 numpy 直接生成一张图
# ---------------------------------------------------------------- #
def _blur3(arr: np.ndarray) -> np.ndarray:
    """便宜的 3x3 均值模糊 (让粒子边缘不那么硬)."""
    out = arr.copy()
    for shift in (-1, 1):
        out += np.roll(arr, shift, axis=0) + np.roll(arr, shift, axis=1)
    return out / 5.0


def _rain_alpha(width, height, count, length, angle_deg, rng) -> np.ndarray:
    alpha = np.zeros((height, width), np.float32)
    rad = math.radians(angle_deg)
    dx, dy = math.sin(rad), -math.cos(rad) # 斜向下
    xs = rng.integers(0, width, count)
    ys = rng.integers(0, height, count)
    lengths = rng.integers(max(4, length // 3), length, count)
    strengths = rng.uniform(0.2, 1.0, count)
    for x0, y0, seg_len, value in zip(xs, ys, lengths, strengths):
        steps = np.arange(seg_len)
        xx = ((x0 + dx * steps).astype(np.int32)) % width
        yy = ((y0 + dy * steps).astype(np.int32)) % height
        # 雨丝头尾淡出, 看起来更像高速运动的水线
        fade = value * np.clip(np.sin(np.pi * steps / max(seg_len - 1, 1)), 0.15, 1.0)
        np.maximum.at(alpha, (yy, xx), fade.astype(np.float32))
    return _blur3(alpha)


def make_overlay_image(overlay: dict, width: int, height: int, seed: int = 0):
    """生成一张白色雨丝图 (黑底), 供合成器以 Screen 方式叠加."""
    rng = np.random.default_rng(seed)
    alpha = _rain_alpha(width, height, int(overlay.get('count', 1500)),
                        int(overlay.get('length', 55)),
                        float(overlay.get('angle', 14.0)), rng)

    image = bpy.data.images.get(OVERLAY_IMAGE)
    if image is not None and tuple(image.size) != (width, height):
        bpy.data.images.remove(image)
        image = None
    if image is None:
        image = bpy.data.images.new(OVERLAY_IMAGE, width, height, alpha=True, float_buffer=True)
    pixels = np.empty((height, width, 4), np.float32)
    pixels[..., 0] = pixels[..., 1] = pixels[..., 2] = alpha
    pixels[..., 3] = 1.0
    image.pixels.foreach_set(pixels.ravel())
    image.update() # 通知 Blender 像素已变 (逐帧重新生成时必须)
    return image


# ---------------------------------------------------------------- #
# 合成器: 深度雾 + 粒子叠加
# ---------------------------------------------------------------- #
def _clear_compositor() -> None:
    bpy.context.scene.compositing_node_group = None
    group = bpy.data.node_groups.get(COMPOSITOR_GROUP)
    if group is not None:
        bpy.data.node_groups.remove(group)


def ensure_compositor_group():
    """取/建合成器节点组 (直通版: 渲染结果 -> 输出), 并挂到场景上.

    天气 (雾/雨) 与 depth 的 File Output 都往这一个组里加节点, 所以两者可以并存.
    """
    scene = bpy.context.scene
    group = bpy.data.node_groups.get(COMPOSITOR_GROUP)
    if group is None:
        group = bpy.data.node_groups.new(COMPOSITOR_GROUP, 'CompositorNodeTree')
        group.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
        render_layers = group.nodes.new('CompositorNodeRLayers')
        output = group.nodes.new('NodeGroupOutput')
        output.location = (900, 0)
        group.links.new(render_layers.outputs['Image'], output.inputs[0])
    scene.compositing_node_group = group
    return group


def setup_compositor(fog: dict = None, overlay_image=None, overlay_strength: float = 0.3) -> None:
    """建立合成器节点组: 渲染结果 -> (深度雾) -> (粒子叠加) -> 输出."""
    _clear_compositor()
    if not fog and overlay_image is None:
        return # clear 天气: 不挂合成器 (需要 depth 时再由 ensure_compositor_group 建直通组)

    scene = bpy.context.scene
    group = ensure_compositor_group()
    nodes, links = group.nodes, group.links
    render_layers = next(n for n in nodes if n.type == 'R_LAYERS')
    output = next(n for n in nodes if n.type == 'GROUP_OUTPUT')
    current = render_layers.outputs['Image']

    if fog: # 深度雾: 用 Mist pass 作为混合系数, 距离越远越接近雾色
        bpy.context.view_layer.use_pass_mist = True
        mist = scene.world.mist_settings
        mist.start = float(fog.get('start', 10.0))
        mist.depth = float(fog.get('depth', 200.0))
        mist.falloff = fog.get('falloff', 'QUADRATIC')

        fog_mix = nodes.new('ShaderNodeMix')
        fog_mix.data_type = 'RGBA'
        fog_mix.blend_type = 'MIX'
        fog_mix.location = (300, 0)
        _socket(fog_mix, 'B_Color').default_value = (*fog.get('color', (0.8, 0.82, 0.85)), 1.0)
        links.new(current, _socket(fog_mix, 'A_Color'))

        strength = float(fog.get('strength', 1.0))
        if strength >= 0.999: # 直接用 Mist 作系数
            links.new(render_layers.outputs['Mist'], _socket(fog_mix, 'Factor_Float'))
        else: # 乘一个上限, 避免远处完全糊成一片
            scale = nodes.new('ShaderNodeMath')
            scale.operation = 'MULTIPLY'
            scale.location = (120, -200)
            scale.inputs[1].default_value = strength
            links.new(render_layers.outputs['Mist'], scale.inputs[0])
            links.new(scale.outputs[0], _socket(fog_mix, 'Factor_Float'))
        current = _out_socket(fog_mix, 'Result_Color')

    if overlay_image is not None: # 雨丝 / 雪花: Screen 叠加 (黑底不影响画面)
        image_node = nodes.new('CompositorNodeImage')
        image_node.name = OVERLAY_NODE
        image_node.image = overlay_image
        image_node.location = (300, -420)

        overlay_mix = nodes.new('ShaderNodeMix')
        overlay_mix.data_type = 'RGBA'
        overlay_mix.blend_type = 'SCREEN'
        overlay_mix.location = (600, 0)
        _socket(overlay_mix, 'Factor_Float').default_value = float(overlay_strength)
        links.new(current, _socket(overlay_mix, 'A_Color'))
        links.new(image_node.outputs['Image'], _socket(overlay_mix, 'B_Color'))
        current = _out_socket(overlay_mix, 'Result_Color')

    links.new(current, output.inputs[0])
    scene.compositing_node_group = group


def set_overlay_frame(index: int, overlay: dict, resolution) -> None:
    """逐帧重新生成雨丝图, 避免整段序列里雨丝/雪花是钉死的.

    (比在合成器里平移一张图更简单: numpy 生成一张 1280x720 的粒子图只要几十毫秒,
    相对每帧数秒的 Cycles 渲染可以忽略, 而且每帧的粒子分布都是新的.)
    """
    if not overlay:
        return
    group = bpy.data.node_groups.get(COMPOSITOR_GROUP)
    if group is None or group.nodes.get(OVERLAY_NODE) is None:
        return
    make_overlay_image(overlay, int(resolution[0]), int(resolution[1]), seed=index)


# ---------------------------------------------------------------- #
# 对外入口
# ---------------------------------------------------------------- #
def resolve_weather(name) -> dict:
    if isinstance(name, dict):
        return name
    if name not in WEATHER_STYLES:
        print(f'[weather] 未知天气 "{name}", 按 clear 处理. 可选: {", ".join(WEATHER_STYLES)}')
        return {}
    return WEATHER_STYLES[name]


def apply_weather(name='clear', resolution=(1280, 720), seed: int = 0) -> dict:
    """应用天气 (材质 + 合成器), 返回需要合并到 light style 上的光照修正.

    调用顺序: 先 apply_weather 拿到 light 修正, 再 setup_world(合并后的 style) ——
    因为天气会改写太阳/天空 (下雨天没有硬阴影).
    """
    cfg = resolve_weather(name)
    if cfg.get('wet'):
        apply_road_wetness(cfg['wet'])

    overlay_cfg = cfg.get('overlay')
    overlay_image = None
    if overlay_cfg:
        overlay_image = make_overlay_image(overlay_cfg, int(resolution[0]), int(resolution[1]), seed)
    setup_compositor(
        fog=cfg.get('fog'),
        overlay_image=overlay_image,
        overlay_strength=(overlay_cfg or {}).get('strength', 0.3),
    )
    print(f'[weather] {name}: fog={bool(cfg.get("fog"))} '
          f'rain_overlay={bool(overlay_cfg)} wet={cfg.get("wet", 0)}')
    return dict(cfg.get('light', {}))


def overlay_config(name) -> dict:
    """取该天气的粒子层配置 (没有则 None), 供逐帧刷新使用."""
    return resolve_weather(name).get('overlay')
