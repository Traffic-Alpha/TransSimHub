'''
@Author: WANG Maonan
@Date: 2026-08-18
@Description: Panda 侧的模型实例池 —— 每个 glb 只加载一次, 之后共享几何.

为什么需要: 车流里车辆不断进出, 每辆新车都会建一个 node. 直接用
`loader.loadModel(path)` 即使命中 Panda 的 ModelPool, 也仍然要**拷贝一整棵子图**
(实测每辆车 ~20-100ms, 在 100 步的路口场景里占了 15% 的总耗时).

改成「模板 + instanceTo」后, 每辆车只是一个持有变换的空 node, 底下 instance 到共享的
模板几何: 实测 0.02ms/辆 (快三个数量级), 显存里也只有一份网格.

注意: 因为几何是共享的, **不要对单辆车的 node 改材质/颜色** —— 会影响到同款所有车.
现在没有这种用法 (车身颜色来自 glb 材质); 真要做逐车染色, 得对那辆车单独 copyTo.
'''
from pathlib import Path
from typing import Dict

from loguru import logger
from panda3d.core import Filename

_templates: Dict[str, object] = {} # glb 路径 -> 已加载并脱离场景图的模板 NodePath
_dimensions: Dict[str, tuple] = {} # glb 路径 -> (length, width, height), 同款车尺寸相同


def _model_filename(model_path: str) -> Filename:
    """Return an absolute Panda VFS filename on Linux, macOS, and Windows."""
    return Filename.from_os_specific(str(Path(model_path).resolve()))


def instance_model(showbase_instance, model_path: str, name: str, parent=None):
    """取 (或首次加载) 模型模板, 实例化成一个可独立摆位的 node 并返回.

    Args:
        showbase_instance: Panda ShowBase (提供 loader).
        model_path: glb 绝对路径.
        name: 新 node 的名字 (如 vehicle-<id>).
        parent: 父节点; 为 None 时先挂在模板所在的游离节点下, 由调用方再 reparent.
    """
    model_file = _model_filename(model_path)
    cache_key = model_file.get_fullpath()
    template = _templates.get(cache_key)
    if template is None:
        template = showbase_instance.loader.loadModel(model_file)
        template.detachNode() # 模板本身不参与渲染, 只作为实例源
        _templates[cache_key] = template
        logger.debug(f"SIM: 模型模板已缓存 {model_file} (共 {len(_templates)} 个).")

    holder = parent.attachNewNode(name) if parent is not None else showbase_instance.render.attachNewNode(name)
    template.instanceTo(holder)
    return holder


def model_dimensions(showbase_instance, model_path: str):
    """取模型包围盒尺寸 (length, width, height); 同一个 glb 只算一次.

    尺寸只取决于模型本身, 而 getBounds() 每辆车算一遍要 ~6ms (车流进出时很可观),
    所以按 glb 路径缓存.
    """
    model_file = _model_filename(model_path)
    cache_key = model_file.get_fullpath()
    dims = _dimensions.get(cache_key)
    if dims is None:
        template = _templates.get(cache_key)
        if template is None: # 尚未加载过 (正常流程里 instance_model 会先跑)
            template = showbase_instance.loader.loadModel(model_file)
            template.detachNode()
            _templates[cache_key] = template
        bounds = template.getBounds()
        lo, hi = bounds.getMin(), bounds.getMax()
        dims = (hi.getX() - lo.getX(), hi.getY() - lo.getY(), hi.getZ() - lo.getZ())
        _dimensions[cache_key] = dims
    return dims


def clear_model_templates() -> None:
    """清空模板缓存 (换场景/换资产目录时用)."""
    for template in _templates.values():
        template.removeNode()
    _templates.clear()
    _dimensions.clear()
