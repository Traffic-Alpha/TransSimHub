'''
@Author: WANG Maonan
@Date: 2024-07-15 11:53:11
@Description: 创建一个 offscreen 相机 (buffer + texture + camera_np), 相机行为由 CameraRig 驱动.
LastEditTime: 2026-07-10
'''
from panda3d.core import (
    FrameBufferProperties,
    GraphicsOutput,
    GraphicsPipe,
    Texture,
    WindowProperties,
    OrthographicLens,
    PerspectiveLens,
)

from .offscreen_camera.camera import OffscreenCamera
from tshub.tshub_env3d.scene import CameraRig
from tshub.tshub_env3d.renderers.panda.segmentation import configure_seg_camera


def build_offscreen_camera(
    name: str, # camera_id
    mask,
    width: int,
    height: int,
    resolution: float,
    showbase_instance,
    root_np,
    rig: CameraRig, # 相机规格 (决定位姿/朝向), 见 scene.sensor_rig
    height_override: float = None,
    carrier_dimensions=None,
) -> OffscreenCamera:
    """生成一个 offscreen 的 camera. 每一个 camera 都会绑定在一个 sensor 上面, 由 CameraRig 决定角度.

    Args:
        name (str): camera 的 id, 用于创建 node, 和找到这个 camera
        width (int): 生成的图像的宽度
        height (int): 生成的图像的高度
        resolution (float): 缩放因子，它用于缩放胶片大小的宽度和高度。例如：
            1. resolution=1 表示胶片大小被设置为原始的 width 和 height 值，没有进行任何缩放。视野直接基于这些尺寸。
            2. resolution=0.1 表示胶片大小被缩小到原始 width 和 height 值的10%。这实际上缩小了视野，使得场景中的对象看起来更大或更近，因为你是在放大观察场景的更小部分。
        rig (CameraRig): 相机规格, 决定 eye/target 与朝向.
    """
    # setup buffer
    win_props = WindowProperties.size(width, height)
    fb_props = FrameBufferProperties()
    fb_props.setRgbColor(True)
    fb_props.setRgbaBits(8, 8, 8, 8)
    # XXX: Though we don't need the depth buffer returned, setting this to 0
    #      causes undefined behavior where the ordering of meshes is random.
    fb_props.setDepthBits(24)         # 深度缓冲位数
    fb_props.setAuxRgba(1)            # 添加辅助通道（用于阴影）
    fb_props.setStencilBits(8)        # 启用模板缓冲（某些阴影技术需要）
    if rig.modality != 'seg':
        fb_props.setMultisamples(4)   # 离屏 buffer 显式请求 MSAA, 减少 BEV 细线锯齿
    # seg 相机不开 MSAA: 需要硬边纯色, 否则边缘抗锯齿混色无法精确映射回 label-id

    buffer = showbase_instance.win.engine.makeOutput(
        showbase_instance.pipe,
        "{}-buffer".format(name),
        -100,
        fb_props,
        win_props,
        GraphicsPipe.BFRefuseWindow,
        showbase_instance.win.getGsg(),
        showbase_instance.win,
    )
    if buffer is None:
        raise RuntimeError(
            f"SIM: failed to create offscreen camera buffer '{name}' "
            f"({width}x{height}, modality={rig.modality})."
        )
    # Set background color to black
    buffer.setClearColor((0, 0, 0, 0))

    # setup texture
    tex = Texture()
    region = buffer.getDisplayRegion(0)
    region.window.addRenderTexture(
        tex, GraphicsOutput.RTM_copy_ram, GraphicsOutput.RTP_color
    )

    # setup camera
    if rig.top_down:
        lens = OrthographicLens()
        if rig.ortho_size is not None:
            view_height = float(rig.ortho_size)
        else:
            view_height = max(60.0, float(height_override or 60.0) * 1.6)
        lens.setFilmSize(view_height * (width / height), view_height)
    else:
        lens = PerspectiveLens() # 人眼的视角, 有 3D 效果
        lens.setFov(rig.fov_deg)
        lens.setFilmSize(width * resolution, height * resolution)

    camera_np = showbase_instance.makeCamera(
        buffer, camName=name,
        scene=root_np, lens=lens
    )
    camera_np.reparentTo(root_np) # 设置 camera 在 node 上

    # mask is set to make undesirable objects invisible to this camera
    camera_np.node().setCameraMask(mask)

    # seg 相机: 配置 tag-state, 对各类节点套 flat 标签色 shader (覆盖 simplepbr 着色)
    if rig.modality == 'seg':
        configure_seg_camera(camera_np)

    # 相机行为由 CameraRig 驱动 (取代原先 11 个几乎重复的相机子类)
    return OffscreenCamera(
        camera_np=camera_np, buffer=buffer, tex=tex,
        showbase_instance=showbase_instance, rig=rig,
        carrier_dimensions=carrier_dimensions,
    )
