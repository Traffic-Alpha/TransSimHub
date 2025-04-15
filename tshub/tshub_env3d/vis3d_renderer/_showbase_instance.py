'''
@Author: WANG Maonan
@Date: 2024-07-03 23:43:42
@Description: 继承 ShowBase, Panda3D 的主界面
LastEditTime: 2025-01-16 19:46:14
'''
from ...utils.get_abs_path import get_abs_path
current_file_path = get_abs_path(__file__)

import simplepbr
from loguru import logger
from threading import Lock
from direct.showbase.ShowBase import ShowBase

from panda3d.core import (
    NodePath,
    Shader,
    loadPrcFileData,
)

from .base_render import DEBUG_MODE, BACKEND_LITERALS

class _ShowBaseInstance(ShowBase):
    """Wraps a singleton instance of ShowBase from Panda3D.
    """
    _debug_mode: DEBUG_MODE = DEBUG_MODE.WARNING
    _rendering_backend: BACKEND_LITERALS = "p3headlessgl" # pandagl
    _render_mode: str = "onscreen" # onscreen or offscreen

    @classmethod
    def load_config(cls, key, value) -> None:
        """Helper method to load configuration.
        """
        loadPrcFileData("", f"{key} {value}")
        
    def __new__(cls, use_render_pipeline=False):
        # Singleton pattern:  ensure only 1 ShowBase instance
        if "__it__" not in cls.__dict__:
            if cls._debug_mode <= DEBUG_MODE.INFO:
                cls.load_config("gl-debug", "#t") # 启用 OpenGL 的调试模式
                cls.load_config("want-pstats", "1") # 启用 Panda3D 的性能统计工具 PStats
            
            # 设置渲染后端，例如"pandagl"，由类属性决定
            cls.load_config("load-display", cls._rendering_backend)
            cls.load_config("window-title", "TSHub 3D") # 设置窗口标题
            
            # 设置辅助渲染器, 辅助显示后端可以在主显示后端无法使用时作为备选
            aux_displays = [
                "pandagl", "pandadx9", "pandadx8", 
                "pandagles", "pandagles2", "p3headlessgl", "p3tinydisplay"
            ]
            for display in aux_displays:
                cls.load_config("aux-display", display)

            # Load other configurations
            configs = {
                "sync-video": "false", # 禁用垂直同步，否则渲染速率会被限制为屏幕的刷新率
                "model-cache-compressed-textures": "1", # 启用模型缓存中的压缩纹理，这可以减少内存使用，提高性能。
                "framebuffer-multisample": "1", # 启用帧缓冲区多重采样，这是抗锯齿技术的一种，可以提高渲染图形的质量。
                "multisamples": "8", # 设置多重采样的数量，这里设置为8，这将进一步提高抗锯齿的效果，但可能会增加图形处理的负担。
                "audio-library-name": "null", # 禁用音频库，不处理音频输出
                "notify-level": cls._debug_mode.name.lower(), # 设置通知级别
                "default-directnotify-level": cls._debug_mode.name.lower(), # 设置默认的直接通知级别
                "print-pipe-types": "false", # 禁止打印管道类型信息
                # "show-buffers": "#t", # 开启 Panda3D 的缓冲区可视化功能
                "threading-model": "Cull/Draw" # 设置 Panda3D 的线程模型。这里指定使用分离的剔除（Cull）和绘制（Draw）线程，这样可以在多核处理器上提高渲染效率。
            }
            for key, value in configs.items():
                cls.load_config(key, value)
                
        it = cls.__dict__.get("__it__")
        if it is None:
            cls.__it__ = it = object.__new__(cls)
            it.init()
        return it

    def __init__(self) -> None:
        """单例模式 (singleton pattern), 使用 init() 而不是这里的 __init__()
        """
        pass

    def init(self) -> None:
        """Initializer for the purposes of maintaining a singleton of this class.
        """
        self._render_lock = Lock()
        try:
            # There can be only 1 ShowBase instance at a time.
            if _ShowBaseInstance._render_mode == "offscreen":
                super().__init__(windowType="offscreen") # 此时是没有界面的
            elif _ShowBaseInstance._render_mode == "onscreen":
                super().__init__() # 开启可视化界面
            simplepbr.init(
                msaa_samples=16,
                use_hardware_skinning=True,
                use_normal_maps=True,
                use_330=False
            ) # https://github.com/Moguri/panda3d-simplepbr

            self.setBackgroundColor(255, 255, 255, 1) # 设置背景颜色, (0,0,0) 是黑色
            self.setFrameRateMeter(True) # 是否显示 FPS
            logger.info("SIM: 初始化 ShowBase 实例")
        except Exception as e:
            raise e
        
    # #################################
    # 下面两个 method 用于调整 class 的参数
    # #################################
    @classmethod
    def set_render_mode(cls, render_mode: str) -> None:
        """Sets the render mode.
        """
        cls._render_mode = render_mode
              
    @classmethod
    def set_rendering_verbosity(cls, debug_mode: DEBUG_MODE) -> None:
        """Set rendering debug information verbosity.
        """
        cls._debug_mode = debug_mode
        cls.load_config("notify-level", cls._debug_mode.name.lower())
        cls.load_config("default-directnotify-level", cls._debug_mode.name.lower())

    @classmethod
    def set_rendering_backend(
        cls,
        rendering_backend: BACKEND_LITERALS,
    ) -> None:
        """Sets the rendering backend.
        """
        if "__it__" not in cls.__dict__:
            cls._rendering_backend = rendering_backend
        else:
            if cls._rendering_backend != rendering_backend:
                logger.warning("SIM: Cannot apply rendering backend after setup.")

    # ##################
    # 关于 showbase 的删除
    # ##################
    def destroy(self) -> None:
        """Destroy this renderer and clean up all remaining resources.
        """
        super().destroy()
        self.__class__.__it__ = None

    def __del__(self) -> None:
        try:
            self.destroy()
        except (AttributeError, TypeError):
            pass
    
    # #############
    # 设置 SIM ROOT
    # #############
    def setup_sim_root(self, simid: str):
        """Creates the simulation root node in the scene graph.
        """
        root_np = NodePath(simid)
        # 根节点放在 render 上面
        with self._render_lock:
            root_np.reparentTo(self.render)
                    
        unlit_shader = Shader.load(
            Shader.SL_GLSL,
            vertex=current_file_path("../_assets_3d/shader/unlit_shader.vert"),
            fragment=current_file_path("../_assets_3d/shader/unlit_shader.frag"),
        )
        root_np.setShader(unlit_shader, priority=10)

        logger.info("SIM: 完成了 SIM Root 的设置.")
        return root_np