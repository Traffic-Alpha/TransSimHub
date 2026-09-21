'''
@Author: WANG Maonan
@Date: 2026-07-10
@Description: Panda 侧的语义分割支持.

机制: 给场景各类节点打一个 "seg" 标签 (标签值见 core.sensors.seg_classes 的类别名);
seg 相机通过 Panda 的 tag-state 对带该标签的节点套一个 flat shader 状态 (输出该类的标签色),
从而覆盖掉正常的 simplepbr 着色, 一趟渲染出「每类一个纯色」的图 (rgb 相机不受影响).
颜色/类别定义来自渲染器无关的 core.sensors.seg_classes;
打标签的位置在 rendering_components/scene_loader.py 与 tshub_render.py (各加载点直接调 tag_seg).
'''
from panda3d.core import Shader, ShaderAttrib, RenderState

from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.core import SEG_RENDER_COLORS

_current_file_path = get_abs_path(__file__)

SEG_TAG = "seg"  # 节点上的标签 key

_seg_shader = None


def get_seg_shader() -> Shader:
    """加载 (并缓存) 分割用的 flat shader (frag 输出 label_color uniform)."""
    global _seg_shader
    if _seg_shader is None:
        _seg_shader = Shader.load(
            Shader.SL_GLSL,
            vertex=_current_file_path("../../_assets_3d/shader/segmentation.vert"),
            fragment=_current_file_path("../../_assets_3d/shader/segmentation.frag"),
        )
    return _seg_shader


def tag_seg(node_path, seg_class: str) -> None:
    """给一个节点打语义分割标签 (其子节点渲染时会继承该标签)."""
    node_path.setTag(SEG_TAG, seg_class)


def configure_seg_camera(camera_np) -> None:
    """把一台相机配置成分割相机: 对带 seg 标签的节点套 per-class flat 状态.

    每个语义类一个 tag-state (shader + 该类标签色, 颜色 baked 进 ShaderAttrib), 覆盖节点
    自身的 simplepbr 着色. 未打标签的节点仍按正常着色 (但 seg 相机场景里应全部打过标签).
    """
    shader = get_seg_shader()
    cam_node = camera_np.node()
    cam_node.setTagStateKey(SEG_TAG)
    for seg_class, rgba in SEG_RENDER_COLORS.items():
        attrib = ShaderAttrib.make(shader).set_shader_input("label_color", rgba)
        cam_node.setTagState(seg_class, RenderState.make(attrib))
