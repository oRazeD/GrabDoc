
import os
import subprocess
import json

import bpy
from bpy.types import Context, Operator

from .operators import OpInfo
from ..constants import Global, Error
from ..utils.generic import (
    bad_setup_check,
    export_plane,
    get_create_addon_temp_dir
)
from ..utils.render import set_guide_height, get_rendered_objects


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
        package = __package__.split('.', maxsplit=1)[0]
        return os.path.exists(
            context.preferences.addons[package].preferences.marmo_executable
        )

    def open_marmoset(self, context: Context, temp_path, addon_path):
        gd = context.scene.gd
        package = __package__.split('.', maxsplit=1)[0]
        executable = context.preferences.addons[package].preferences.marmo_executable

        # Create a dictionary of variables to transfer into Marmoset
        marmo_vars = {
            'file_path': f'{bpy.path.abspath(gd.export_path)}{gd.export_name}.{gd.marmo_format.lower()}',
            'file_ext': gd.marmo_format.lower(),
            'file_path_no_ext': bpy.path.abspath(gd.export_path),
            'marmo_sky_path': f'{os.path.dirname(executable)}\\data\\sky\\Evening Clouds.tbsky',

            'resolution_x': gd.resolution_x,
            'resolution_y': gd.resolution_y,
            'bits_per_channel': int(gd.depth),
            'samples': int(gd.marmo_samples),

            'auto_bake': gd.metalness_auto_bake,
            'close_after_bake': gd.marmo_auto_close,

            'export_normal': gd.normals[0].enabled & gd.normals[0].visibility,
            'flipy_normal': gd.normals[0].flip_y,
            'suffix_normal': gd.normals[0].suffix,

            'export_curvature': gd.curvature[0].enabled & gd.curvature[0].visibility,
            'suffix_curvature': gd.curvature[0].suffix,

            'export_occlusion': gd.occlusion[0].enabled & gd.occlusion[0].visibility,
            'ray_count_occlusion': gd.marmo_occlusion_ray_count,
            'suffix_occlusion': gd.occlusion[0].suffix,

            'export_height': gd.height[0].enabled & gd.height[0].visibility,
            'cage_height': gd.height[0].distance * 100 * 2,
            'suffix_height': gd.height[0].suffix,

            'export_alpha': gd.alpha[0].enabled & gd.alpha[0].visibility,
            'suffix_alpha': gd.alpha[0].suffix,

            'export_matid': gd.id[0].enabled & gd.id[0].visibility,
            'suffix_id': gd.id[0].suffix
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
            os.path.join(temp_path, "marmo_vars.json"), "w", encoding="utf-8"
        ) as outfile:
            outfile.write(marmo_json)

        path_ext_only = os.path.basename(os.path.normpath(executable)).encode()

        if gd.export_plane:
            export_plane(context)

        subproc_args = [
            executable,
            os.path.join(addon_path, "marmo_utils.py")
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
        gd = context.scene.gd

        report_value, report_string = \
            bad_setup_check(context, active_export=True)
        if report_value:
            self.report({'ERROR'}, report_string)
            return {'CANCELLED'}

        addon_path, temp_path = get_create_addon_temp_dir()

        saved_selected = context.view_layer.objects.selected.keys()

        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        rendered_obs = get_rendered_objects()
        if gd.height[0].enabled and gd.height[0].method == 'AUTO':
            set_guide_height(rendered_obs)

        # Set high poly naming
        for ob in context.view_layer.objects:
            ob.select_set(False)

            if ob.name in rendered_obs \
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
        bg_plane_ob_copy.name = \
            f"{Global.GD_HIGH_PREFIX} {Global.BG_PLANE_NAME}"
        bg_plane_ob_copy.select_set(True)

        # Remove reference material
        if Global.REFERENCE_NAME in bpy.data.materials:
            bpy.data.materials.remove(bpy.data.materials.get(Global.REFERENCE_NAME))

        # Export models
        bpy.ops.export_scene.fbx(
            filepath=f"{temp_path}\\GD_temp_model.fbx",
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

        if not gd.coll_selectable:
            bpy.data.collections[Global.COLL_NAME].hide_select = True

        for ob_name in saved_selected:
            ob = context.scene.objects.get(ob_name)

            if ob.visible_get():
                ob.select_set(True)

        self.open_marmoset(context, temp_path, addon_path)
        return {'FINISHED'}


################################################
# REGISTRATION
################################################


def register():
    bpy.utils.register_class(GrabDoc_OT_send_to_marmo)


def unregister():
    bpy.utils.unregister_class(GrabDoc_OT_send_to_marmo)



