
import bpy, traceback, os
from bpy.types import Operator
from .render_setup_utils import get_rendered_objects
from .gd_constants import *


def export_bg_plane(context) -> None:
    '''Export the grabdoc background plane for external use'''
    grabDoc = context.scene.grabDoc

    # Save original selection
    savedSelection = context.selected_objects

    # Deselect all objects
    bpy.ops.object.select_all(action='DESELECT')

    # Select bg plane, export and deselect bg plane
    bpy.data.collections[COLL_NAME].hide_select = bpy.data.objects[BG_PLANE_NAME].hide_select = False
    bpy.data.objects[BG_PLANE_NAME].select_set(True)
    
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(bpy.path.abspath(grabDoc.exportPath), grabDoc.exportName + '_plane.fbx'),
        use_selection=True
    )

    bpy.data.objects[BG_PLANE_NAME].select_set(False)

    # Refresh original selection
    for ob in savedSelection:
        ob.select_set(True)

    if not grabDoc.collSelectable:
        bpy.data.collections[COLL_NAME].hide_select = False


def proper_scene_setup() -> bool:
    '''Look for grabdoc objects to decide if the scene is setup correctly'''
    if COLL_NAME in bpy.data.collections and BG_PLANE_NAME in bpy.context.scene.objects:
        return True
    return False


def get_format_extension() -> str:
    '''Get the correct file extension
    
    TODO might just be able to integrate this directly into the property name/description'''
    grabDoc = bpy.context.scene.grabDoc

    if grabDoc.imageType == 'TIFF':
        file_extension = '.tif'
    elif grabDoc.imageType == 'TARGA':
        file_extension = '.tga'
    elif grabDoc.imageType == 'OPEN_EXR':
        file_extension = '.exr'
    else:
        file_extension = '.png'
    return file_extension


def bad_setup_check(self, context, active_export: bool, report_value=False, report_string="") -> tuple[bool, str]:
    '''Determine if specific parts of the scene are set up incorrectly and return a detailed explanation of things for the user to fix'''
    grabDoc = context.scene.grabDoc

    # Run this before other error checks as the following error checks contain dependencies
    self.rendered_obs = get_rendered_objects(context)

    # Look for Trim Camera (only thing required to render)
    if not TRIM_CAMERA_NAME in context.view_layer.objects and not report_value:
        report_value = True
        report_string = "Trim Camera not found, refresh the scene to set everything up properly."

    # Check for no objects in manual collection
    if grabDoc.onlyRenderColl and not report_value:
        if not len(bpy.data.collections[COLL_OB_NAME].objects):
            report_value = True
            report_string = "You have 'Use Bake Group' turned on, but no objects are inside the corresponding collection."

    if active_export:
        # Check for export path
        if not os.path.exists(bpy.path.abspath(grabDoc.exportPath)) and not report_value:
            report_value = True
            report_string = "There is no export path set"

        # Check if all bake maps are disabled
        bake_maps = [
            grabDoc.exportNormals,
            grabDoc.exportCurvature,
            grabDoc.exportOcclusion,
            grabDoc.exportHeight,
            grabDoc.exportMatID,
            grabDoc.exportAlpha,
            grabDoc.exportAlbedo,
            grabDoc.exportRoughness,
            grabDoc.exportMetalness
        ]

        bake_map_vis = [
            grabDoc.uiVisibilityNormals,
            grabDoc.uiVisibilityCurvature,
            grabDoc.uiVisibilityOcclusion,
            grabDoc.uiVisibilityHeight,
            grabDoc.uiVisibilityMatID,
            grabDoc.uiVisibilityAlpha,
            grabDoc.uiVisibilityAlbedo,
            grabDoc.uiVisibilityRoughness,
            grabDoc.uiVisibilityMetalness
        ]

        if not True in bake_maps or not True in bake_map_vis:
            report_value = True
            report_string = "No bake maps are turned on."

    return (report_value, report_string)


class OpInfo:
    bl_options = {'REGISTER', 'UNDO'}


class GRABDOC_OT_load_ref(OpInfo, Operator):
    """Import a reference onto the background plane"""
    bl_idname = "grab_doc.load_ref"
    bl_label = "Load Reference"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        # Load a new image into the main database
        bpy.data.images.load(self.filepath, check_existing=True)

        context.scene.grabDoc.refSelection = bpy.data.images[os.path.basename(os.path.normpath(self.filepath))]
        return{'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class GRABDOC_OT_open_folder(OpInfo, Operator):
    """Opens up the File Explorer to the designated folder location"""
    bl_idname = "grab_doc.open_folder"
    bl_label = "Open Folder"

    def execute(self, context):
        try:
            bpy.ops.wm.path_open(filepath = bpy.path.abspath(context.scene.grabDoc.exportPath))
        except RuntimeError:
            self.report({'ERROR'}, "No valid file path set")
        return{'FINISHED'}


class GRABDOC_OT_view_cam(OpInfo, Operator):
    """View the GrabDoc camera"""
    bl_idname = "grab_doc.view_cam"
    bl_label = ""

    from_modal: bpy.props.BoolProperty(default=False, options={'HIDDEN'})

    def execute(self, context):
        context.scene.camera = bpy.data.objects[TRIM_CAMERA_NAME]
        
        try:
            if self.from_modal:
                if [area.spaces.active.region_3d.view_perspective for area in context.screen.areas if area.type == 'VIEW_3D'] == ['CAMERA']:
                    bpy.ops.view3d.view_camera()
            else:
                bpy.ops.view3d.view_camera()
        except:
            traceback.print_exc()
            self.report({'ERROR'}, "Exit camera failed, please email the developer with the error code listed in the console @ ethan.simon.3d@gmail.com")

        self.from_modal = False
        return{'FINISHED'}


################################################################################################################
# REGISTRATION
################################################################################################################


classes = (
    GRABDOC_OT_open_folder,
    GRABDOC_OT_load_ref,
    GRABDOC_OT_view_cam
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


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
