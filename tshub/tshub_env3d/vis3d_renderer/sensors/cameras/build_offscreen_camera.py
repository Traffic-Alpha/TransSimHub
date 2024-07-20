'''
@Author: WANG Maonan
@Date: 2024-07-15 11:53:11
@Description: 创建不同类型的 Offscreen Camera Type
@LastEditTime: 2024-07-21 02:21:31
'''
from panda3d.core import (
    FrameBufferProperties,
    GraphicsOutput,
    GraphicsPipe,
    OrthographicLens,
    Texture,
    WindowProperties,
    PerspectiveLens,
)

from .offscreen_camera import (
    # 俯拍摄像头
    OffscreenBEVCamera,
    # 路口摄像头
    OffscreenJunctionFrontCamera,
    OffscreenJunctionBackCamera,
    # 前方摄像头
    OffscreenFrontCamera,
    OffscreenFrontRightCamera,
    OffscreenFrontLeftCamera,
    # 后方摄像头
    OffscreenBackCamera,
    OffscreenBackLeftCamera,
    OffscreenBackRightCamera
)
from .offscreen_camera.offscreen_camera_type import OffscreenCameraType

def build_offscreen_camera(
    name: str, # camera_id
    mask,
    width: int,
    height: int,
    resolution: float,
    showbase_instance,
    root_np, 
    camera_type: str = 'Off_BEV_Camera' # 默认为 BEV
) -> None:
    """生成一个 offscreen 的 camera. 每一个 camera 都会绑定在一个 sensor 上面, 然后 P3DOffscreenCamera 会设置角度

    Args:
        name (str): camera 的 id, 用于创建 node, 和找到这个 camera
        width (int): 生成的图像的宽度
        height (int): 生成的图像的高度
        resolution (float): 缩放因子，它用于缩放胶片大小的宽度和高度。例如：
            1. resolution=1 表示胶片大小被设置为原始的 width 和 height 值，没有进行任何缩放。视野直接基于这些尺寸。
            2. resolution=0.1 表示胶片大小被缩小到原始 width 和 height 值的10%。这实际上缩小了视野，使得场景中的对象看起来更大或更近，因为你是在放大观察场景的更小部分。
    """
    # setup buffer
    win_props = WindowProperties.size(width, height)
    fb_props = FrameBufferProperties()
    fb_props.setRgbColor(True)
    fb_props.setRgbaBits(8, 8, 8, 1)
    # XXX: Though we don't need the depth buffer returned, setting this to 0
    #      causes undefined behavior where the ordering of meshes is random.
    fb_props.setDepthBits(8)

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
    # Set background color to black
    buffer.setClearColor((0, 0, 0, 0))

    # setup texture
    tex = Texture()
    region = buffer.getDisplayRegion(0)
    region.window.addRenderTexture(
        tex, GraphicsOutput.RTM_copy_ram, GraphicsOutput.RTP_color
    )

    # setup camera (人眼的视角, 有 3D 效果)
    lens = PerspectiveLens()
    lens.setFov(90)  # Set the field of view to 45 degrees, or another value as needed
    # lens.setNearFar(0.1, 1000)  # Set near and far clipping planes

    # ------

    # setup camera (没有 3D 的效果)
    # lens = OrthographicLens()
    lens.setFilmSize(width * resolution, height * resolution)

    camera_np = showbase_instance.makeCamera(
        buffer, camName=name, 
        scene=root_np, lens=lens
    )
    camera_np.reparentTo(root_np) # 设置 camera 在 node 上

    # mask is set to make undesirable objects invisible to this camera
    camera_np.node().setCameraMask(mask)

    # 设置 camera, 这里 camera update 的方式不一样

    # 俯视 (UAV/UAM)
    _camera_type = OffscreenCameraType(camera_type)
    if _camera_type == OffscreenCameraType.BEV:
        camera = OffscreenBEVCamera(camera_np=camera_np, buffer=buffer, tex=tex)
    # 路口的摄像头
    elif _camera_type == OffscreenCameraType.Junction_Front: # 正对路口
        camera = OffscreenJunctionFrontCamera(camera_np, buffer, tex)
    elif _camera_type == OffscreenCameraType.Junction_Back: # 对着道路出口
        camera = OffscreenJunctionBackCamera(camera_np, buffer, tex)
    # 前拍
    elif _camera_type == OffscreenCameraType.Front:
        camera = OffscreenFrontCamera(camera_np, buffer, tex)
    elif _camera_type == OffscreenCameraType.Front_LEFT: # 前拍 (左侧)
        camera = OffscreenFrontLeftCamera(camera_np, buffer, tex)
    elif _camera_type == OffscreenCameraType.Front_RIGHT: # 前拍 (右侧)
        camera = OffscreenFrontRightCamera(camera_np, buffer, tex)
    # 后拍
    elif _camera_type == OffscreenCameraType.Back:
        camera = OffscreenBackCamera(camera_np, buffer, tex)
    elif _camera_type == OffscreenCameraType.Back_LEFT: # 后拍 (左侧)
        camera = OffscreenBackLeftCamera(camera_np, buffer, tex)
    elif _camera_type == OffscreenCameraType.Back_RIGHT: # 后拍 (右侧)
        camera = OffscreenBackRightCamera(camera_np, buffer, tex)    
    else:
        raise ValueError(f"请你确认 camera 的名字, {camera_type}")
    return camera