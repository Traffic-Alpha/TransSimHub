'''
Author: WANG Maonan
Date: 2025-06-18 15:40:12
LastEditors: WANG Maonan
Description: 加载车辆模型用于渲染
LastEditTime: 2025-07-29 15:02:38
'''
import os
import bpy
import json
from mathutils import Euler, Vector
from typing import Optional, List, Dict

class VehicleManager:
    """管理车辆模型加载和缓存
    """
    def __init__(
            self, 
            models_base_path: str, # 汽车模型
            collection_name: str = "vehicles",
            centers: Optional[List[List[float]]] = None, # 多个中心点坐标列表, 可以是多个路口
            radius: float = 100.0, # 过滤半径 (米)
        ):
        self.models_base_path = models_base_path # 车辆模型存储位置
        self.collection_name = collection_name # 车辆存储的集合名称
        self.model_cache = {}  # 模型路径 -> Blender对象 的映射
        self.vehicle_objects = {}  # 当前时刻的车辆对象

        # 根据距离中心点的距离过滤车辆
        self.centers = [Vector(center) for center in centers] if centers else None
        self.radius = radius
        
    def load_vehicles(self, json_path: str) -> Dict[str, bpy.types.Object]:
        """加载指定时刻的车辆"""
        self.clear_vehicles()
        
        try:
            with open(json_path, 'r') as f:
                vehicles_data = json.load(f)
            
            for vehicle_id, vehicle_info in vehicles_data.items():
                pos = Vector(vehicle_info['pos']) # 获得车辆位置
                # 范围过滤检查（多个中心点）
                if self.centers and not self._is_in_range(pos):
                    continue
                
                model_path = os.path.join(self.models_base_path, vehicle_info['model'])
                
                # 使用缓存或加载新模型
                if model_path not in self.model_cache:
                    obj = self._load_glb_model(model_path, vehicle_id)
                    if obj is None:
                        continue
                    self.model_cache[model_path] = obj
                
                # 复制缓存的模型（共享模型）
                template = self.model_cache[model_path]
                obj = bpy.data.objects.new(vehicle_id, template.data) # 创建新对象实例（共享网格数据）
                
                # 定位车辆
                self._position_object(
                    obj=obj,
                    pos=vehicle_info['pos'],
                    heading_rad=vehicle_info['heading'],
                    collection_name=self.collection_name
                )
                
                self.vehicle_objects[vehicle_id] = obj
                print(f"加载车辆: {vehicle_id} 位置: {vehicle_info['pos']}")
            
            return self.vehicle_objects
        
        except Exception as e:
            print(f"加载车辆时出错: {str(e)}")
            return {}

    def _is_in_range(self, position: Vector) -> bool:
        """检查位置是否在任意中心点半径范围内（忽略Z轴）"""
        # 创建平面位置向量 (忽略Z轴)
        plane_pos = Vector((position.x, position.y, 0))
        
        for center in self.centers:
            # 创建平面中心点向量 (忽略Z轴)
            plane_center = Vector((center.x, center.y, 0))
            
            # 计算平面距离
            distance = (plane_pos - plane_center).length
            if distance <= self.radius:
                return True
        
        return False
        
    def clear_vehicles(self) -> None:
        """清除当前时刻的所有车辆"""
        for obj in self.vehicle_objects.values():
            bpy.data.objects.remove(obj, do_unlink=True)
        self.vehicle_objects.clear()
    
    def _load_glb_model(self, glb_path: str, obj_name: str) -> Optional[bpy.types.Object]:
        """加载单个GLB模型"""
        try:
            previous_selection = list(bpy.context.selected_objects)
            bpy.ops.import_scene.gltf(filepath=glb_path)
            
            imported_objects = [
                obj for obj in bpy.context.selected_objects 
                if obj not in previous_selection
            ]
            
            if not imported_objects:
                print(f"警告: 从 {glb_path} 导入模型但未获得新对象")
                return None
            
            obj = imported_objects[0]
            obj.name = f"{obj_name}_template"  # 标记为模板对象

            # 应用变换以确保尺寸数据准确
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

            # 隐藏模板对象（不显示在渲染中）
            obj.hide_viewport = True
            obj.hide_render = True
                        
            return obj
        
        except Exception as e:
            print(f"导入模型 {glb_path} 时出错: {str(e)}")
            return None

    def _position_object(
            self, 
            obj: bpy.types.Object, 
            pos: List[float], 
            heading_rad: float, 
            collection_name: str
        ) -> None:
        """定位车辆对象
        参数:
            obj: 要定位的Blender对象
            pos: [x, y, z] 位置坐标 (z是地面高度)
            heading_rad: 朝向角度(弧度)
            collection_name: 集合名称
        """
        # 添加到目标集合
        if collection_name not in bpy.data.collections:
            new_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(new_collection)
        
        # 将车辆添加到 collection
        bpy.data.collections[collection_name].objects.link(obj)

        # 计算对象高度 (从边界框获取)
        bbox = [Vector(v) for v in obj.bound_box]
        min_z = min(v.z for v in bbox)
        max_z = max(v.z for v in bbox)
        height = max_z - min_z
        
        # 设置位置 (z = 地面高度 + 1/2高度)
        obj.location = Vector((pos[0], pos[1], pos[2] + height/2))
        
        # 设置旋转
        obj.rotation_mode = 'XYZ'
        obj.rotation_euler = Euler((0, 0, heading_rad), 'XYZ')
        
        # 更新视图
        bpy.context.view_layer.update()