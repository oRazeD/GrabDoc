import os
import re
from inspect import getframeinfo, stack

import bpy
from bpy.types import Context, Operator

from ..constants import GlobalVariableConstants as Global
from ..constants import ErrorCodeConstants as Error
from ..constants import NAME, VERSION


class PanelInfo:
    bl_category = 'GrabDoc'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = ""


class SubPanelInfo:
    bl_parent_id = "GRABDOC_PT_view_edit_maps"
    bl_options = {'HEADER_LAYOUT_EXPAND', 'DEFAULT_CLOSED'}


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


def is_camera_in_3d_view() -> bool:
    """Check if we are actively viewing
    through the camera in the 3D View"""
    return [
        area.spaces.active.region_3d.view_perspective for area in bpy.context.screen.areas if area.type == 'VIEW_3D'
    ] == ['CAMERA']


# NOTE: Basic DRM is best DRM
def is_pro_version() -> bool:
    return "Pro" in NAME


def format_bl_label(
        name: str=NAME,
        bl_version: str=VERSION
    ) -> str:
    tuples_version_pattern = r'\((\d+), (\d+), (\d+)\)'
    match = re.match(tuples_version_pattern, str(bl_version))
    result = '.'.join(match.groups()) if match else None
    formatted = f"{name} {result}"
    return formatted


def get_create_addon_temp_dir(
        dir_name: str="temp",
        create_dir: bool=True
    ) -> tuple[str, str]:
    """Creates a temporary files directory
    for automatically handled I/O"""
    addon_path = os.path.dirname(__file__)
    temps_path = os.path.join(addon_path, dir_name)
    if create_dir and not os.path.exists(temps_path):
        os.mkdir(temps_path)
    return (addon_path, temps_path)


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

    # Look for Trim Camera (only thing required to render)
    if not Global.TRIM_CAMERA_NAME in context.view_layer.objects \
    and not report_value:
        report_value = True
        report_string = Error.TRIM_CAM_NOT_FOUND

    # Check for no objects in manual collection
    if gd.use_bake_collections and not report_value:
        if not len(bpy.data.collections[Global.COLL_OB_NAME].objects):
            report_value = True
            report_string = Error.NO_OBJECTS_BAKE_GROUPS

    if active_export:
        # Check for export path
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
            gd.roughness[0].enabled,
            gd.metalness[0].enabled
        )

        bake_map_vis = (
            gd.normals[0].ui_visibility,
            gd.curvature[0].ui_visibility,
            gd.occlusion[0].ui_visibility,
            gd.height[0].ui_visibility,
            gd.id[0].ui_visibility,
            gd.alpha[0].ui_visibility,
            gd.color[0].ui_visibility,
            gd.roughness[0].ui_visibility,
            gd.metalness[0].ui_visibility
        )

        if True not in bake_maps or True not in bake_map_vis:
            report_value = True
            report_string = "No bake maps are turned on."
    return (report_value, report_string)


# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####
