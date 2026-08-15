'''
@Author: WANG Maonan
@Date: 2026-07-11
@Description: Deprecated location. ``sumonet_convert`` was renamed to
``scene_generation`` (it now builds full city-builder scenes — roads, lanes,
buildings, trees, roadside people — not just a SUMO-net conversion).
'''
raise ImportError(
    "tshub.tshub_env3d.scene.sumonet_convert has been renamed to "
    "tshub.tshub_env3d.scene.scene_generation. Update your imports, e.g.\n"
    "    from tshub.tshub_env3d.scene.scene_generation.sumonet_to_tshub3d import SumoNet3D\n"
    "    from tshub.tshub_env3d.scene.scene_generation import export_scene_geometry\n"
    "and the Blender step now lives at "
    "tshub/tshub_env3d/scene/scene_generation/blender/build_scene.py."
)
