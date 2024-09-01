import os
import re
import tomllib
from pathlib import Path
from inspect import getframeinfo, stack

import bpy
from bpy.types import Context, Operator

from ..constants import Global, Error


class OpInfo:
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = ""


class PanelInfo:
    bl_category = 'GrabDoc'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = ""


class UseSelectedOnly():
    @classmethod
    def poll(cls, context: Context) -> bool:
        return True if len(context.selected_objects) else poll_message_error(
            cls, Error.NO_OBJECTS_SELECTED
        )


def export_plane(context: Context) -> None:
    """Export the grabdoc background plane for external use"""
    gd = context.scene.gd

    # Save original selection
    savedSelection = context.selected_objects

    # Deselect all objects
    bpy.ops.object.select_all(action='DESELECT')

    # Select bg plane, export and deselect bg plane
    bpy.data.collections[Global.COLL_NAME].hide_select = False
    bpy.data.objects[Global.BG_PLANE_NAME].hide_select = False
    bpy.data.objects[Global.BG_PLANE_NAME].select_set(True)

    bpy.ops.export_scene.fbx(
        filepath=os.path.join(
            bpy.path.abspath(gd.export_path),
            gd.export_name + '_plane.fbx'
        ),
        use_selection=True
    )

    bpy.data.objects[Global.BG_PLANE_NAME].select_set(False)

    # Refresh original selection
    for ob in savedSelection:
        ob.select_set(True)

    if not gd.coll_selectable:
        bpy.data.collections[Global.COLL_NAME].hide_select = False


def proper_scene_setup() -> bool:
    """Look for grabdoc objects to decide
    if the scene is setup correctly"""
    object_checks = (
        Global.COLL_NAME in bpy.data.collections,
        Global.BG_PLANE_NAME in bpy.context.scene.objects,
        Global.TRIM_CAMERA_NAME in bpy.context.scene.objects
    )
    return True in object_checks


def camera_in_3d_view() -> bool:
    """Check if we are actively viewing
    through the camera in the 3D View"""
    return [
        area.spaces.active.region_3d.view_perspective for area in bpy.context.screen.areas if area.type == 'VIEW_3D'
    ] == ['CAMERA']


def get_version(version: tuple[int, int, int] | None = None) -> str | None:
    if version is None:
        with open("blender_manifest.toml", "rb") as f:
            data = tomllib.load(f)
            return data.get("version", None)
    # NOTE: Since 4.2 this pattern is deprecated
    version_pattern = r'\((\d+), (\d+), (\d+)\)'
    match = re.match(version_pattern, str(version))
    return '.'.join(match.groups()) if match else None


def get_temp_path() -> str:
    """Gets or creates a temporary directory based on the extensions system."""
    return bpy.utils.extension_path_user(
        __package__.rsplit(".", maxsplit=1)[0], path="temp", create=True
    )


def get_debug_line_no() -> str:
    """Simple method of getting the
    line number of a particular error"""
    caller = getframeinfo(stack()[2][0])
    file_name = caller.filename.split("\\", -1)[-1]
    line_num = caller.lineno
    return f"{file_name}:{line_num}"


def poll_message_error(
        cls: Operator,
        error_message: str,
        print_err_line: bool=True
    ) -> bool:
    """Calls the poll_message_set function, for use in operator polls.
    This ALWAYS returns a False boolean value if called.

    Parameters
    ----------
    error_message : str
        Error message to print to the user
    print_err_line : bool, optional
        Whether the error line will be printed or not, by default True
    """
    cls.poll_message_set(
        f"{error_message}. ({get_debug_line_no()})'" \
            if print_err_line else f"{error_message}."
    )
    return False


def get_format() -> str:
    """Get the correct file extension based on `format` attribute"""
    return f".{Global.IMAGE_FORMATS[bpy.context.scene.gd.format]}"


def bad_setup_check(
        context: Context,
        active_export: bool,
        report_value=False,
        report_string=""
    ) -> tuple[bool, str]:
    """Determine if specific parts of the scene
    are set up incorrectly and return a detailed
    explanation of things for the user to fix"""
    gd = context.scene.gd

    if not Global.TRIM_CAMERA_NAME in context.view_layer.objects \
    and not report_value:
        report_value = True
        report_string = Error.TRIM_CAM_NOT_FOUND

    if gd.use_bake_collections and not report_value:
        if not len(bpy.data.collections[Global.COLL_OB_NAME].objects):
            report_value = True
            report_string = Error.NO_OBJECTS_BAKE_GROUPS

    if not active_export:
        return report_value, report_string

    if not os.path.exists(bpy.path.abspath(gd.export_path)) \
    and not report_value:
        report_value = True
        report_string = Error.NO_VALID_PATH_SET

    # Check if all bake maps are disabled
    bake_maps = (
        gd.normals[0].enabled,
        gd.curvature[0].enabled,
        gd.occlusion[0].enabled,
        gd.height[0].enabled,
        gd.id[0].enabled,
        gd.alpha[0].enabled,
        gd.color[0].enabled,
        gd.emissive[0].enabled,
        gd.roughness[0].enabled,
        gd.metallic[0].enabled
    )
    bake_map_vis = (
        gd.normals[0].visibility,
        gd.curvature[0].visibility,
        gd.occlusion[0].visibility,
        gd.height[0].visibility,
        gd.id[0].visibility,
        gd.alpha[0].visibility,
        gd.color[0].visibility,
        gd.emissive[0].visibility,
        gd.roughness[0].visibility,
        gd.metallic[0].visibility
    )

    if True not in bake_maps or True not in bake_map_vis:
        report_value = True
        report_string = "No bake maps are turned on."
    return report_value, report_string
