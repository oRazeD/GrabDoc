
import os
import subprocess
import json

import bpy
from bpy.types import Context, Operator

from .operators import OpInfo
from ..constants import GlobalVariableConstants as Global
from ..constants import ErrorCodeConstants as Error
from ..utils.generic import (
    bad_setup_check,
    export_bg_plane,
    get_create_addon_temp_dir
)
from ..utils.render import set_guide_height


################################################
# MARMOSET EXPORTER
################################################


class GrabDoc_OT_send_to_marmo(OpInfo, Operator):
    """Export your models, open & bake (if turned on) in
    Marmoset Toolbag utilizing the settings set within
    the 'View / Edit Maps' tab"""
    bl_idname = "grab_doc.bake_marmoset"
    bl_label = "Open / Refresh in Marmoset"

    send_type: bpy.props.EnumProperty(
        items=(
            ('open',"Open",""),
            ('refresh', "Refresh", "")
        ),
        options={'HIDDEN'}
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        return os.path.exists(
            context.preferences.addons[__package__].preferences.marmoEXE
        )

    def open_marmoset(self, context: Context, temps_path, addon_path):
        gd = context.scene.grabDoc
        marmo_exe = context.preferences.addons[__package__].preferences.marmoEXE

        # Create a dictionary of variables to transfer into Marmoset
        marmo_vars = {
            'file_path': f'{bpy.path.abspath(gd.exportPath)}{gd.exportName}.{gd.imageType_marmo.lower()}',
            'file_ext': gd.imageType_marmo.lower(),
            'file_path_no_ext': bpy.path.abspath(gd.exportPath),
            'marmo_sky_path': f'{os.path.dirname(marmo_exe)}\\data\\sky\\Evening Clouds.tbsky',

            'resolution_x': gd.exportResX,
            'resolution_y': gd.exportResY,
            'bits_per_channel': int(gd.colorDepth),
            'samples': int(gd.marmoSamples),

            'auto_bake': gd.marmoAutoBake,
            'close_after_bake': gd.marmoClosePostBake,
            'open_folder': gd.openFolderOnExport,

            'export_normal': gd.exportNormals & gd.uiVisibilityNormals,
            'flipy_normal': gd.flipYNormals,
            'suffix_normal': gd.suffixNormals,

            'export_curvature': gd.exportCurvature & gd.uiVisibilityCurvature,
            'suffix_curvature': gd.suffixCurvature,

            'export_occlusion': gd.exportOcclusion & gd.uiVisibilityOcclusion,
            'ray_count_occlusion': gd.marmoAORayCount,
            'suffix_occlusion': gd.suffixOcclusion,

            'export_height': gd.exportHeight & gd.uiVisibilityHeight,
            'cage_height': gd.guideHeight * 100 * 2,
            'suffix_height': gd.suffixHeight,

            'export_alpha': gd.exportAlpha & gd.uiVisibilityAlpha,
            'suffix_alpha': gd.suffixAlpha,

            'export_matid': gd.exportMatID & gd.uiVisibilityMatID,
            'suffix_id': gd.suffixID
        }

        # Flip the slashes of the first Dict value (It's
        # gross but I don't know how to do it any other
        # way without an error in Marmoset)
        for key, value in marmo_vars.items():
            marmo_vars[key] = value.replace("\\", "/")
            break

        # Serializing
        marmo_json = json.dumps(marmo_vars, indent = 4)

        # Writing
        with open(
            os.path.join(temps_path, "marmo_vars.json"), "w", encoding="utf-8"
        ) as outfile:
            outfile.write(marmo_json)

        path_ext_only = os.path.basename(os.path.normpath(marmo_exe)).encode()

        if gd.exportPlane:
            export_bg_plane(context)

        subproc_args = [
            marmo_exe,
            os.path.join(addon_path, "marmoset_utils.py")
        ]

        if self.send_type == 'refresh':
            # TODO: don't use shell=True arg
            sub_proc = subprocess.check_output('tasklist', shell=True)

            if not path_ext_only in sub_proc:
                subprocess.Popen(subproc_args)

                self.report({'INFO'}, Error.MARMOSET_EXPORT_COMPLETE)
            else:
                self.report({'INFO'}, Error.MARMOSET_RE_EXPORT_COMPLETE)
        else:
            subprocess.Popen(subproc_args)

            self.report({'INFO'}, Error.MARMOSET_EXPORT_COMPLETE)
        return {'FINISHED'}

    def execute(self, context: Context):
        gd = context.scene.grabDoc

        report_value, report_string = bad_setup_check(self, context, active_export=True)
        if report_value:
            self.report({'ERROR'}, report_string)
            return {'CANCELLED'}

        addon_path, temps_path = get_create_addon_temp_dir()

        saved_selected = context.view_layer.objects.selected.keys()

        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        if gd.exportHeight and gd.rangeTypeHeight == 'AUTO':
            set_guide_height()

        # Set high poly naming
        for ob in context.view_layer.objects:
            ob.select_set(False)

            if ob.name in self.rendered_obs \
            and ob.visible_get() and ob.name != Global.BG_PLANE_NAME:
                ob.select_set(True)

                ob.name = f"{Global.GD_HIGH_PREFIX} {ob.name}"

        # Get background plane low and high poly
        bg_plane_ob = bpy.data.objects.get(Global.BG_PLANE_NAME)
        bg_plane_ob.name = f"{Global.GD_LOW_PREFIX} {Global.BG_PLANE_NAME}"
        bpy.data.collections[Global.COLL_NAME].hide_select = \
            bg_plane_ob.hide_select = False
        bg_plane_ob.select_set(True)

        # Copy the object, link into the scene & rename as high poly
        bg_plane_ob_copy = bg_plane_ob.copy()
        context.collection.objects.link(bg_plane_ob_copy)
        bg_plane_ob_copy.name = f"{Global.GD_HIGH_PREFIX} {Global.BG_PLANE_NAME}"
        bg_plane_ob_copy.select_set(True)

        # Remove reference material
        if Global.REFERENCE_NAME in bpy.data.materials:
            bpy.data.materials.remove(bpy.data.materials.get(Global.REFERENCE_NAME))

        # Export models
        bpy.ops.export_scene.fbx(
            filepath=f"{temps_path}\\GD_temp_model.fbx",
            use_selection=True,
            path_mode='ABSOLUTE'
        )

        # TODO: remove mesh instead? Verify
        # this doesn't leave floating data
        bpy.data.objects.remove(bg_plane_ob_copy)

        for ob in context.selected_objects:
            ob.select_set(False)

            if ob.name == f"{Global.GD_LOW_PREFIX} {Global.BG_PLANE_NAME}":
                ob.name = Global.BG_PLANE_NAME
            else:
                ob.name = ob.name[8:] # TODO: what does this represent?

        if not gd.collSelectable:
            bpy.data.collections[Global.COLL_NAME].hide_select = True

        for ob_name in saved_selected:
            ob = context.scene.objects.get(ob_name)

            if ob.visible_get():
                ob.select_set(True)

        self.open_marmoset(context, temps_path, addon_path)
        return {'FINISHED'}


################################################
# REGISTRATION
################################################


def register():
    bpy.utils.register_class(GrabDoc_OT_send_to_marmo)


def unregister():
    bpy.utils.unregister_class(GrabDoc_OT_send_to_marmo)


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
