'''
Author: WANG Maonan
Date: 2025-06-18 13:31:20
LastEditors: WANG Maonan
Description: 使用 Blender 渲染, 三种渲染模式: (1) rgb; (2) mask; (3) depth;
LastEditTime: 2025-07-30 11:14:45
'''
import os
import bpy

class TimestepRenderer:
    """渲染时间序列
    """
    def __init__(
            self, 
            resolution: int = 1080,
            image_format: str = "PNG",
            camera_collection: str = "camera",
            render_mask: bool = False,
            render_depth: bool = False
        ):
        self.renderer = BlenderRenderer()
        self.resolution = resolution # 图片分辨率
        self.image_format = image_format
        self.camera_collection = camera_collection # blender 中相机所在的集合
        self.render_mask = render_mask # 是否渲染 mask
        self.render_depth = render_depth # 是否渲染 depth

    def render_timestep(self, output_dir: str) -> None:
        """渲染单个时刻
        """
        self.renderer.render_all_cameras(
            camera_collection=self.camera_collection,
            output_dir=output_dir,
            resolution=self.resolution,
            image_format=self.image_format,
            render_mask=self.render_mask,
            render_depth=self.render_depth
        )
        
class BlenderRenderer:
    """Blender多通道渲染器
    """
    
    def __init__(self):
        self._setup_render_engine()
    
    def _setup_render_engine(self) -> None:
        """初始化渲染引擎设置
        """
        # 启用详细调试信息（0=无，1=基本，2=详细）
        bpy.app.debug = True
        bpy.app.debug_value = 2  # 输出更详细的统计信息

        preferences = bpy.context.preferences
        cycles_preferences = preferences.addons['cycles'].preferences
        cycles_preferences.compute_device_type = 'CUDA'
        
        for device in cycles_preferences.devices:
            device['use'] = 0 if 'Intel' in device['name'] else 1
        
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'GPU'

        bpy.context.scene.cycles.kernel_cache_limit = 2048  # 允许缓存更多内核（MB）
        bpy.context.scene.cycles.use_kernel_optimization = True  # 启用内核优化
    
    def _setup_vehicle_mask(self) -> None:
        """设置车辆蒙版渲染环境，只保留车辆，其他不渲染
        """
        # 隐藏非车辆对象（只显示车辆集合中的对象）
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                # 如果对象在'vehicles'集合中，则显示；否则隐藏
                obj.hide_render = 'vehicles' not in [col.name for col in obj.users_collection]
    
    def _setup_depth_output(self, output_dir: str, camera_name:str) -> None:
        """设置深度图渲染并保存到指定目录（每个相机生成单独的EXR文件）
        
        关键特性：
        1. 完全独立于RGB渲染流程，不会互相干扰
        2. 自动使用当前场景激活的相机（由render_all_cameras设置）
        3. 生成标准化深度图（0-1范围，OPEN_EXR格式）
        4. 自动清理合成器节点避免影响后续渲染

        Args:
            output_dir: 深度图保存目录（会自动创建）
        """
        scene = bpy.context.scene
        
        # ======================
        # 1. 防止与RGB渲染冲突
        # ======================
        original_filepath = scene.render.filepath  # 备份原始路径
        scene.render.filepath = ""  # 清空防止自动保存冗余PNG
        
        # ======================
        # 2. 配置合成器节点
        # ======================
        scene.use_nodes = True
        tree = scene.node_tree
        
        # 清除所有现有节点（确保干净的合成环境）
        for node in tree.nodes:
            tree.nodes.remove(node)
        
        # 创建必要节点
        render_layers = tree.nodes.new('CompositorNodeRLayers')
        file_output = tree.nodes.new('CompositorNodeOutputFile')
        
        # ======================
        # 3. 深度图参数设置
        # ======================
        # 启用深度通道（必须在渲染前设置）
        view_layer = bpy.context.view_layer
        view_layer.use_pass_z = True
        
        # 配置深度数据标准化（将原始深度映射到0-1范围）
        map_range = tree.nodes.new('CompositorNodeMapRange')
        map_range.inputs['From Min'].default_value = 0.1    # 近裁剪面距离
        map_range.inputs['From Max'].default_value = 150.0   # 远裁剪面距离
        map_range.inputs['To Min'].default_value = 0.0       # 映射到0
        map_range.inputs['To Max'].default_value = 1.0       # 映射到1
        
        # ======================
        # 4. 文件输出设置
        # ======================
        file_output.format.file_format = 'OPEN_EXR'  # 必须使用EXR保存浮点数据
        file_output.file_slots[0].path = camera_name # 相机名称
        file_output.base_path = output_dir           # 设置输出目录
        
        # 兼容不同Blender版本（处理节点输出名称差异）
        map_range_output = "Result" if "Result" in map_range.outputs else "Value"
        
        # ======================
        # 5. 节点连接
        # ======================
        # 渲染层深度 → 标准化 → 文件输出
        tree.links.new(render_layers.outputs['Depth'], map_range.inputs['Value'])
        tree.links.new(map_range.outputs[map_range_output], file_output.inputs[0])
        
        # ======================
        # 6. 执行渲染
        # ======================
        # 注意：此时scene.camera已由render_all_cameras设置好
        bpy.ops.render.render(write_still=True)  # 触发合成器保存
        
        # ======================
        # 7. 清理现场
        # ======================
        # 删除所有合成节点（避免影响后续RGB/Mask渲染）
        for node in tree.nodes:
            tree.nodes.remove(node)
        scene.use_nodes = False
        
        # 恢复原始文件路径（不影响后续操作）
        scene.render.filepath = original_filepath
    
    def _restore_scene(self) -> None:
        """恢复场景原始状态 (所有物体都进行渲染)
        """
        for obj in bpy.data.objects:
            obj.hide_render = False
    
    def _get_camera_list(self, camera_collection: str) -> list:
        """获取相机列表
        
        Args:
            camera_collection: 相机集合名称
            
        Returns:
            相机对象列表
        """
        cam_collection = bpy.data.collections.get(camera_collection)
        if not cam_collection:
            raise ValueError(f"相机集合 '{camera_collection}' 不存在")
        
        return [obj for obj in cam_collection.objects if obj.type == 'CAMERA']
    
    def _render_rgb_for_all_cameras(self, cameras: list, output_dir: str) -> None:
        """批量渲染所有相机的RGB图像
        
        Args:
            cameras: 相机对象列表
            output_dir: 输出目录
        """
        bpy.context.scene.cycles.samples = 64  # RGB高质量
        scene = bpy.context.scene
        rgb_dir = os.path.join(output_dir, 'high_quality_rgb')
        os.makedirs(rgb_dir, exist_ok=True)
        
        for cam_obj in cameras:
            scene.camera = cam_obj
            base_name = cam_obj.name
            scene.render.filepath = os.path.join(rgb_dir, f"{base_name}.png")
            bpy.ops.render.render(write_still=True)
            print(f"渲染RGB: {base_name}")
    
    def _render_mask_for_all_cameras(self, cameras: list, output_dir: str) -> None:
        """批量渲染所有相机的Mask图像
        
        Args:
            cameras: 相机对象列表
            output_dir: 输出目录
        """
        bpy.context.scene.cycles.samples = 16  # Mask低采样
        scene = bpy.context.scene
        mask_dir = os.path.join(output_dir, 'high_quality_mask')
        os.makedirs(mask_dir, exist_ok=True)
        
        # 一次性设置mask环境
        self._setup_vehicle_mask()
        
        try:
            for cam_obj in cameras:
                scene.camera = cam_obj
                base_name = cam_obj.name
                scene.render.filepath = os.path.join(mask_dir, f"{base_name}.png")
                bpy.ops.render.render(write_still=True)
                print(f"渲染蒙版: {base_name}")
        finally:
            # 确保无论如何都会恢复场景
            self._restore_scene()
    
    def _render_depth_for_all_cameras(self, cameras: list, output_dir: str) -> None:
        """批量渲染所有相机的Depth图像
        
        Args:
            cameras: 相机对象列表
            output_dir: 输出目录
        """
        bpy.context.scene.cycles.samples = 16  # Depth 低采样
        depth_dir = os.path.join(output_dir, 'high_quality_depth')
        os.makedirs(depth_dir, exist_ok=True)
        
        for cam_obj in cameras:
            bpy.context.scene.camera = cam_obj
            base_name = cam_obj.name
            self._setup_depth_output(depth_dir, base_name)
            print(f"渲染深度: {base_name}")
    
    def render_all_cameras(
        self,
        camera_collection: str = 'camera',
        output_dir: str = '/output',
        resolution: int = 1080,
        image_format: str = 'PNG',
        render_mask: bool = False,
        render_depth: bool = False
    ) -> None:
        """
        渲染所有相机视角的多通道图像
        
        参数:
            camera_collection: 相机集合名称
            output_dir: 输出根目录
            resolution: 渲染分辨率
            image_format: 图像格式
            render_mask: 是否渲染mask
            render_depth: 是否渲染depth
        """
        scene = bpy.context.scene
        
        # 设置渲染参数
        scene.render.resolution_x = resolution
        scene.render.resolution_y = resolution
        scene.render.image_settings.file_format = image_format.upper()
        
        # 获取相机列表
        cameras = self._get_camera_list(camera_collection)
        
        # 1. 先批量渲染所有RGB
        self._render_rgb_for_all_cameras(cameras, output_dir)
        
        # 2. 如果需要，批量渲染所有Mask
        if render_mask:
            self._render_mask_for_all_cameras(cameras, output_dir)
        
        # 3. 如果需要，批量渲染所有Depth
        if render_depth:
            self._render_depth_for_all_cameras(cameras, output_dir)