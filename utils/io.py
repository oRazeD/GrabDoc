import os

import bpy
from bpy.types import Context

from ..constants import Global


def export_plane(context: Context) -> None:
    """Export the grabdoc background plane for external use"""
    gd = context.scene.gd

    # Save original selection
    savedSelection = context.selected_objects

    # Deselect all objects
    bpy.ops.object.select_all(action='DESELECT')

    # Select bg plane, export and deselect bg plane
    bpy.data.collections[Global.COLL_CORE_NAME].hide_select = False
    bpy.data.objects[Global.BG_PLANE_NAME].hide_select = False
    bpy.data.objects[Global.BG_PLANE_NAME].select_set(True)

    bpy.ops.export_scene.fbx(
        filepath=os.path.join(gd.filepath, gd.filename + '_plane.fbx'),
        use_selection=True
    )

    bpy.data.objects[Global.BG_PLANE_NAME].select_set(False)

    # Refresh original selection
    for ob in savedSelection:
        ob.select_set(True)

    if not gd.coll_selectable:
        bpy.data.collections[Global.COLL_CORE_NAME].hide_select = False


def get_temp_path() -> str:
    """Gets or creates a temporary directory based on the extensions system."""
    return bpy.utils.extension_path_user(
        __package__.rsplit(".", maxsplit=1)[0], path="temp", create=True
    )


def get_format() -> str:
    """Get the correct file extension based on `format` attribute"""
    return f".{Global.IMAGE_FORMATS[bpy.context.scene.gd.format]}"
