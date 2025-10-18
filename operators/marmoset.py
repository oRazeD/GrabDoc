
import os
import subprocess
import json
from pathlib import Path

import bpy
from bpy.types import Context, Operator, Object

from ..constants import Global, Error
from ..utils.io import get_temp_path, get_filepath
from ..utils.generic import get_user_preferences
from ..utils.baker import get_bakers
from ..utils.scene import validate_scene
from ..utils.render import set_guide_height, get_rendered_objects


class GrabDoc_OT_send_to_marmo(Operator):
    """Export your models, open and bake the enabled maps in Marmoset Toolbag"""
    bl_idname  = "grabdoc.bake_marmoset"
    bl_label   = "Open / Refresh in Marmoset"
    bl_options = {'REGISTER', 'INTERNAL'}

    send_type: bpy.props.EnumProperty(items=(('open',    "Open",    ""),
                                             ('refresh', "Refresh", "")),
                                      options={'HIDDEN'})

    @classmethod
    def poll(cls, _context: Context) -> bool:
        return os.path.exists(get_user_preferences().mt_executable)

    def open_marmoset(self, context: Context, temp_path, addon_path):
        executable = get_user_preferences().mt_executable

        # Create a dictionary of variables to transfer into Marmoset
        gd = context.scene.gd
        properties = {
            'file_path': \
            f'{get_filepath()}{gd.filename}.{gd.mt_format.lower()}',
            'format': gd.mt_format.lower(),
            'filepath': bpy.path.abspath(get_filepath()),
            'hdri_path': \
            f'{os.path.dirname(executable)}\\data\\sky\\Evening Clouds.tbsky',

            'resolution_x':     gd.resolution_x,
            'resolution_y':     gd.resolution_y,
            'bits_per_channel': int(gd.depth),
            'samples':          int(gd.mt_samples),

            'auto_bake':        gd.mt_auto_bake,
            'close_after_bake': gd.mt_auto_close,

            'export_normal': gd.normals[0].enabled and gd.normals[0].visibility,
            'flipy_normal':  gd.normals[0].flip_y,
            'suffix_normal': gd.normals[0].suffix,

            'export_curvature': gd.curvature[0].enabled and gd.curvature[0].visibility,
            'suffix_curvature': gd.curvature[0].suffix,

            'export_occlusion': gd.occlusion[0].enabled and gd.occlusion[0].visibility,
            'ray_count_occlusion': gd.mt_occlusion_samples,
            'suffix_occlusion': gd.occlusion[0].suffix,

            'export_height': gd.height[0].enabled and gd.height[0].visibility,
            'cage_height': gd.height[0].distance * 100 * 2,
            'suffix_height': gd.height[0].suffix,

            'export_alpha': gd.alpha[0].enabled and gd.alpha[0].visibility,
            'suffix_alpha': gd.alpha[0].suffix,

            'export_matid': gd.id[0].enabled and gd.id[0].visibility,
            'suffix_id': gd.id[0].suffix
        }

        # Flip the slashes of the first dict value
        # NOTE: This is gross but I don't
        # know another way to do it
        for key, value in properties.items():
            properties[key] = value.replace("\\", "/")
            break

        json_properties = json.dumps(properties, indent=4)
        json_path = os.path.join(temp_path, "mt_vars.json")
        with open(json_path, "w", encoding='utf-8') as file:
            file.write(json_properties)

        args = [
            executable,
            os.path.join(addon_path, "utils", "marmoset.py")
        ]

        if self.send_type == 'refresh':
            # TODO: don't use shell=True arg
            output = subprocess.check_output('tasklist', shell=True)
            path_ext_only = \
                os.path.basename(os.path.normpath(executable)).encode()
            if not path_ext_only in output:
                subprocess.Popen(args)
                self.report({'INFO'}, Error.MARMOSET_EXPORT_COMPLETE)
            else:
                self.report({'INFO'}, Error.MARMOSET_REFRESH_COMPLETE)
            return {'FINISHED'}
        subprocess.Popen(args)
        self.report({'INFO'}, Error.MARMOSET_EXPORT_COMPLETE)
        return {'FINISHED'}

    def execute(self, context: Context):
        report_value, report_string = validate_scene(context)
        if report_value:
            self.report({'ERROR'}, report_string)
            return {'CANCELLED'}
        if not get_bakers(filter_enabled=True):
            self.report({'ERROR'}, Error.ALL_MAPS_DISABLED)
            return {'CANCELLED'}

        saved_selected = context.view_layer.objects.selected.keys()

        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        rendered_obs = get_rendered_objects()
        gd = context.scene.gd
        if gd.height[0].enabled and gd.height[0].method == 'auto':
            set_guide_height(rendered_obs)

        # Attach _high suffix to all user assets
        # NOTE: Only supports single bake group for now
        for ob in context.view_layer.objects[:]:
            ob.select_set(False)
            if ob in rendered_obs \
            and Global.FLAG_PREFIX not in ob.name:
                ob.select_set(True)
                # NOTE: Add name to end of name for reuse later
                ob.name = \
                    Global.BG_PLANE_NAME + Global.HIGH_SUFFIX + ob.name

        # Get background plane low and high poly
        plane_low: Object = bpy.data.objects.get(Global.BG_PLANE_NAME)
        plane_low.name = Global.BG_PLANE_NAME + Global.LOW_SUFFIX
        bpy.data.collections[Global.COLL_CORE_NAME].hide_select = \
            plane_low.hide_select = False
        plane_low.select_set(True)
        plane_high: Object = plane_low.copy()
        context.collection.objects.link(plane_high)
        plane_high.name = Global.BG_PLANE_NAME + Global.HIGH_SUFFIX
        plane_high.select_set(True)

        # Remove reference material
        # TODO: Does this need to be re-added back?
        if Global.REFERENCE_NAME in bpy.data.materials:
            bpy.data.materials.remove(
                bpy.data.materials.get(Global.REFERENCE_NAME)
            )

        temp_path = get_temp_path()
        bpy.ops.export_scene.fbx(
            filepath=os.path.join(temp_path, "mesh_export.fbx"),
            use_selection=True, path_mode='ABSOLUTE'
        )

        # Cleanup
        for ob in context.view_layer.objects[:]:
            ob.select_set(False)
            if ob.name.endswith(Global.LOW_SUFFIX):
                ob.name = ob.name.replace(Global.LOW_SUFFIX, "")
            elif plane_high.name in ob.name:
                ob.name = ob.name.replace(plane_high.name, "")

        bpy.data.objects.remove(plane_high)

        if not gd.coll_selectable:
            bpy.data.collections[Global.COLL_CORE_NAME].hide_select = True

        for ob_name in saved_selected:
            ob = context.scene.objects.get(ob_name)
            ob.select_set(True)

        addon_path = os.path.dirname(Path(__file__).parent)
        addon_path = Path(__file__).parents[1]
        self.open_marmoset(context, temp_path, addon_path)
        return {'FINISHED'}


################################################
# REGISTRATION
################################################


def register():
    bpy.utils.register_class(GrabDoc_OT_send_to_marmo)

def unregister():
    bpy.utils.unregister_class(GrabDoc_OT_send_to_marmo)
