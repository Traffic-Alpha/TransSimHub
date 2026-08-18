'''
@Author: WANG Maonan
@Date: 2026-08-15
@Description: 除 RGB 之外的输出通道 —— 语义分割 (seg) 与深度 (depth), 在 Blender 内运行.

两个通道的实现思路完全不同, 因为代价结构不同:

- **depth 单独渲一遍, 但只要 1 个样本**: 深度是「第一次命中」的几何量, 与光照无关,
  所以 1 sample + 覆盖材质 + 0 弹射就精确. 存 32 位单层 EXR 的**真实米数**(不归一化,
  归一化会丢掉量纲). 本来想用 File Output 节点在 RGB 那遍里顺带写出来 (那样是白送的),
  但 Blender 5 的 File Output 只能写多层 EXR, 通用读图库读不了 —— 见 depth_mode 注释.

- **seg 需要单独渲一遍, 但极便宜**: 用 `view_layer.material_override` 把全场景材质
  换成一个「自发光 = 物体颜色」的材质, 每个物体的 `object.color` 设成它所属类别的
  调色板色, 于是一次 1-sample、0 bounce 的渲染就得到每像素严格等于类别色的图.
  这是 Panda 那边 flat seg shader 的 Cycles 对应物, 类别体系完全一致 (core.sensors.seg_classes).

seg 渲染时必须关掉的东西 (否则标签会被污染):
  抗锯齿滤波 (filter_size -> 0.01, 否则类别边界会插值出不存在的颜色)、降噪、
  间接光 (max_bounces=0)、AgX 色调映射 (view_transform -> Standard)、天气合成器
  (雾/雨丝绝不能出现在标签图里).
@LastEditTime: 2026-08-15
'''
import os
from contextlib import contextmanager

import bpy

SEG_MATERIAL = 'TshubSegOverride'
SEG_WORLD = 'TshubSegWorld'
DEPTH_GROUP = 'TshubDepthPass'

# collection -> 语义类别. 与 Panda 侧 scene_loader.tag_seg 的打标严格一致
# (注意 vegetation 归到 ground, 与 Panda 保持一致, 不单独分树木类).
SEG_LAYER_CLASS = {
    'map': 'road',
    'lane_lines': 'lane',
    'road_lines': 'road_edge',
    'buildings': 'building',
    'ground': 'ground',
    'vegetation': 'ground',
    'props': 'pole',       # 路灯/长椅等街道设施 (与 Panda 侧 load_props 一致)
    'vehicles': 'vehicle',
    'aircraft': 'aircraft',
}


def _seg_colors():
    """从渲染器无关的类别定义里取调色板 (延迟导入: Blender 里没有 tshub 包时给个兜底)."""
    try:
        from tshub.tshub_env3d.core.sensors.seg_classes import SEG_NAME_TO_COLOR
        return SEG_NAME_TO_COLOR
    except Exception:
        # Blender 的 python 一般装不了 tshub, 这里内联同一份调色板 (CARLA/Cityscapes)
        return {
            'road': (128, 64, 128), 'lane': (157, 234, 50), 'road_edge': (180, 165, 180),
            'building': (70, 70, 70), 'ground': (145, 170, 100), 'sky': (70, 130, 180),
            'vehicle': (0, 0, 142), 'aircraft': (170, 120, 50), 'pole': (153, 153, 153),
        }


SEG_COLORS = _seg_colors()


def _srgb_to_linear(value: float) -> float:
    """sRGB (0~1) -> 线性. object.color / 灯光颜色都是线性值, 而调色板是 sRGB 字节值;
    渲染时再经 Standard (sRGB) 编码写回 PNG, 才能得到与调色板完全相同的字节."""
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _linear_rgba(color255):
    return (*(_srgb_to_linear(c / 255.0) for c in color255), 1.0)


# ---------------------------------------------------------------- #
# 语义分割
# ---------------------------------------------------------------- #
def assign_seg_colors() -> int:
    """给每个物体写上所属类别的颜色 (object.color), 供 seg 覆盖材质读取.

    车辆/飞行器是 collection instance: 模板物体和实例化用的 Empty 都要着色 ——
    不同情况下 Cycles 的 Object Info 可能取到其中任意一个.
    """
    count = 0
    for layer, class_name in SEG_LAYER_CLASS.items():
        coll = bpy.data.collections.get(layer)
        if coll is None:
            continue
        color = _linear_rgba(SEG_COLORS[class_name])
        for obj in coll.all_objects:
            obj.color = color
            count += 1

    # 模板 collection 里的真实几何 (未挂到场景, all_objects 扫不到)
    from scene_assembly import TEMPLATE_PREFIX
    for coll in bpy.data.collections:
        if not coll.name.startswith(TEMPLATE_PREFIX):
            continue
        class_name = 'aircraft' if 'evetol' in coll.name or 'aircraft' in coll.name else 'vehicle'
        color = _linear_rgba(SEG_COLORS[class_name])
        for obj in coll.all_objects:
            obj.color = color
            count += 1
    return count


def _seg_material():
    """覆盖材质: 自发光 = 物体颜色 (一套材质覆盖全场景, 颜色由 object.color 决定)."""
    mat = bpy.data.materials.get(SEG_MATERIAL)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(SEG_MATERIAL)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    obj_info = nodes.new('ShaderNodeObjectInfo')
    emission = nodes.new('ShaderNodeEmission')
    output = nodes.new('ShaderNodeOutputMaterial')
    emission.inputs['Strength'].default_value = 1.0
    links.new(obj_info.outputs['Color'], emission.inputs['Color'])
    links.new(emission.outputs['Emission'], output.inputs['Surface'])
    return mat


def _seg_world():
    """seg 用的世界: 天空 = sky 类别的纯色 (背景像素直接落在 sky 标签上)."""
    world = bpy.data.worlds.get(SEG_WORLD)
    if world is not None:
        return world
    world = bpy.data.worlds.new(SEG_WORLD)
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    nodes.clear()
    background = nodes.new('ShaderNodeBackground')
    output = nodes.new('ShaderNodeOutputWorld')
    background.inputs['Color'].default_value = _linear_rgba(SEG_COLORS['sky'])
    background.inputs['Strength'].default_value = 1.0
    links.new(background.outputs[0], output.inputs[0])
    return world


@contextmanager
def seg_mode():
    """临时切换到「渲染标签图」的状态, 退出时全部还原."""
    scene = bpy.context.scene
    view_layer = bpy.context.view_layer
    cycles = getattr(scene, 'cycles', None)
    saved = {
        'override': view_layer.material_override,
        'world': scene.world,
        'filter_size': scene.render.filter_size,
        'dither': scene.render.dither_intensity,
        'compositor': scene.compositing_node_group,
        'view_transform': scene.view_settings.view_transform,
        'look': scene.view_settings.look,
        'exposure': scene.view_settings.exposure,
        'samples': getattr(cycles, 'samples', None),
        'denoise': getattr(cycles, 'use_denoising', None),
        'bounces': getattr(cycles, 'max_bounces', None),
    }
    try:
        view_layer.material_override = _seg_material()
        scene.world = _seg_world()
        scene.render.filter_size = 0.01 # 关抗锯齿: 类别边界不能插值
        scene.render.dither_intensity = 0.0 # 关抖动: 否则 8 位输出会有 ±1 噪声, 颜色反查不到类别
        scene.compositing_node_group = None # 天气 (雾/雨) 不能出现在标签图里
        scene.view_settings.view_transform = 'Standard' # AgX 会改变颜色 -> 反查不到类别
        scene.view_settings.look = 'None'
        scene.view_settings.exposure = 0.0
        if cycles is not None:
            cycles.samples = 1 # 纯自发光, 一个样本就够
            cycles.use_denoising = False # 降噪会把标签糊掉
            cycles.max_bounces = 0 # 不要间接光叠加
        yield
    finally:
        view_layer.material_override = saved['override']
        scene.world = saved['world']
        scene.render.filter_size = saved['filter_size']
        scene.render.dither_intensity = saved['dither']
        scene.compositing_node_group = saved['compositor']
        scene.view_settings.view_transform = saved['view_transform']
        scene.view_settings.look = saved['look']
        scene.view_settings.exposure = saved['exposure']
        if cycles is not None:
            cycles.samples = saved['samples']
            cycles.use_denoising = saved['denoise']
            cycles.max_bounces = saved['bounces']


# ---------------------------------------------------------------- #
# 深度
# ---------------------------------------------------------------- #
@contextmanager
def depth_mode():
    """临时切换到「渲染深度图」的状态: 合成器直接输出 Z pass, 存 32 位单层 EXR (米).

    为什么不用 File Output 节点顺带写出来 (那样 depth 就是白送的):
    Blender 5 的 File Output 节点格式被锁死在 OPEN_EXR_MULTILAYER, 只能产出多层 EXR,
    cv2 / imageio 都读不了; per-item 的 override_node_format 也一样是多层.
    所以这里改成单独渲一遍 —— 但深度是「第一次命中」的几何量, 1 个样本就精确,
    再配合覆盖材质 (不算光照) 与 0 次弹射, 代价与 seg 那一遍相当.
    """
    scene = bpy.context.scene
    view_layer = bpy.context.view_layer
    cycles = getattr(scene, 'cycles', None)
    image_settings = scene.render.image_settings
    saved = {
        'override': view_layer.material_override,
        'filter_size': scene.render.filter_size,
        'compositor': scene.compositing_node_group,
        'file_format': image_settings.file_format,
        'color_mode': image_settings.color_mode,
        'color_depth': image_settings.color_depth,
        'samples': getattr(cycles, 'samples', None),
        'denoise': getattr(cycles, 'use_denoising', None),
        'bounces': getattr(cycles, 'max_bounces', None),
    }
    try:
        view_layer.use_pass_z = True
        view_layer.material_override = _seg_material() # 着色无关, 只为省掉光照计算
        scene.render.filter_size = 0.01 # 关抗锯齿: 深度不能在物体边缘插值
        scene.compositing_node_group = _depth_compositor() # 输出 Z 而不是颜色
        image_settings.file_format = 'OPEN_EXR' # 单层 EXR, 通用读图库可读
        # 用 RGB 而不是 BW: BW 写出的 EXR 通道名是 'V', OpenCV 只认 R/G/B/Y, 会读成 None.
        # 三个通道值相同 (都是米), 取任意一个通道即可; ZIP 压缩后冗余代价很小.
        image_settings.color_mode = 'RGB'
        image_settings.color_depth = '32'
        if cycles is not None:
            cycles.samples = 1
            cycles.use_denoising = False
            cycles.max_bounces = 0
        yield
    finally:
        view_layer.material_override = saved['override']
        scene.render.filter_size = saved['filter_size']
        scene.compositing_node_group = saved['compositor']
        image_settings.file_format = saved['file_format']
        image_settings.color_mode = saved['color_mode']
        image_settings.color_depth = saved['color_depth']
        if cycles is not None:
            cycles.samples = saved['samples']
            cycles.use_denoising = saved['denoise']
            cycles.max_bounces = saved['bounces']


def _depth_compositor():
    """一个只把 Z pass 送到输出的合成器节点组 (深度渲染专用)."""
    group = bpy.data.node_groups.get(DEPTH_GROUP)
    if group is not None:
        return group
    group = bpy.data.node_groups.new(DEPTH_GROUP, 'CompositorNodeTree')
    group.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    render_layers = group.nodes.new('CompositorNodeRLayers')
    output = group.nodes.new('NodeGroupOutput')
    output.location = (400, 0)
    group.links.new(render_layers.outputs['Depth'], output.inputs[0])
    return group
