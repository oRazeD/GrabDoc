
import bpy, os, subprocess, json
from .generic_utils import OpInfo, bad_setup_check, export_bg_plane
from .render_setup_utils import find_tallest_object


################################################################################################################
# MARMOSET EXPORTER
################################################################################################################


class GrabDoc_OT_send_to_marmo(OpInfo, bpy.types.Operator):
    """Export your models, open & bake (if turned on) in Marmoset Toolbag utilizing the settings set within the 'View / Edit Maps' tab"""
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
    def poll(cls, context):
        return os.path.exists(context.scene.grabDoc.marmoEXE)

    def open_marmoset(self, context, temps_path, addon_path):
        grabDoc = context.scene.grabDoc

        # Create a dictionary of variables to transfer into Marmoset
        marmo_vars = {
            'file_path': f'{bpy.path.abspath(grabDoc.exportPath)}{grabDoc.exportName}.{grabDoc.imageType_marmo.lower()}',
            'file_ext': grabDoc.imageType_marmo.lower(),
            'file_path_no_ext': bpy.path.abspath(grabDoc.exportPath),
            'marmo_sky_path': f'{os.path.dirname(grabDoc.marmoEXE)}\\data\\sky\\Evening Clouds.tbsky',

            'resolution_x': grabDoc.exportResX,
            'resolution_y': grabDoc.exportResY,
            'bits_per_channel': int(grabDoc.colorDepthPNG),
            'samples': int(grabDoc.marmoSamples),

            'auto_bake': grabDoc.marmoAutoBake,
            'close_after_bake': grabDoc.marmoClosePostBake,
            'open_folder': grabDoc.openFolderOnExport,

            'export_normal': grabDoc.exportNormals & grabDoc.uiVisibilityNormals,
            'flipy_normal': grabDoc.flipYNormals,
            'suffix_normal': grabDoc.suffixNormals,

            'export_curvature': grabDoc.exportCurvature & grabDoc.uiVisibilityCurvature,
            'suffix_curvature': grabDoc.suffixCurvature,

            'export_occlusion': grabDoc.exportOcclusion & grabDoc.uiVisibilityOcclusion,
            'ray_count_occlusion': grabDoc.marmoAORayCount,
            'suffix_occlusion': grabDoc.suffixOcclusion,

            'export_height': grabDoc.exportHeight & grabDoc.uiVisibilityHeight,
            'cage_height': grabDoc.guideHeight * 100 * 2,
            'suffix_height': grabDoc.suffixHeight,

            'export_alpha': grabDoc.exportAlpha & grabDoc.uiVisibilityAlpha,
            'suffix_alpha': grabDoc.suffixAlpha,

            'export_matid': grabDoc.exportMatID & grabDoc.uiVisibilityMatID,
            'suffix_id': grabDoc.suffixID
        }

        # Flip the slashes of the first Dict value (It's gross but I don't know how to do it any other way without an error in Marmoset)
        for key, value in marmo_vars.items():
            marmo_vars[key] = value.replace("\\", "/")
            break
        
        # Serializing
        marmo_json = json.dumps(marmo_vars, indent = 4)

        # Writing
        with open(os.path.join(temps_path, "marmo_vars.json"), "w") as outfile:
            outfile.write(marmo_json)
        
        path_ext_only = os.path.basename(os.path.normpath(grabDoc.marmoEXE)).encode()

        if grabDoc.exportPlane:
            export_bg_plane(self, context)

        subproc_args = [
            grabDoc.marmoEXE,
            os.path.join(addon_path, "marmoset_utils.py")
        ]

        if self.send_type == 'refresh':
            subproc = subprocess.check_output('tasklist', shell=True)
            if not path_ext_only in subproc:
                subprocess.Popen(subproc_args)

                self.report({'INFO'}, "Export completed! Opening Marmoset Toolbag...")
            else:
                self.report({'INFO'}, "Models re-exported! Check Marmoset Toolbag.")
        else:
            subprocess.Popen(subproc_args)

            self.report({'INFO'}, "Export completed! Opening Marmoset Toolbag...")
        return{'FINISHED'}

    def execute(self, context):
        grabDoc = context.scene.grabDoc

        report_value, report_string = bad_setup_check(self, context, active_export=True)

        if report_value:
            self.report({'ERROR'}, report_string)
            return{'CANCELLED'}

        # Add-on root path 
        addon_path = os.path.dirname(__file__)
        
        # Temporary model path 
        temps_path = os.path.join(addon_path, "temp")

        # Create the directory 
        if not os.path.exists(temps_path):
            os.mkdir(temps_path)

        selectedCallback = context.view_layer.objects.selected.keys()

        if context.active_object:
            bpy.ops.object.mode_set(mode = 'OBJECT')

        if grabDoc.exportHeight and grabDoc.rangeTypeHeight == 'AUTO':
            find_tallest_object(self, context)

        # Set high poly naming
        for ob in context.view_layer.objects:
            ob.select_set(False)

            if ob.name in self.render_list and ob.visible_get() and ob.name != 'GD_Background Plane':
                ob.select_set(True)
                
                ob.name = f"GD_high {ob.name}"

        # Get background plane low and high poly
        bg_plane_ob = bpy.data.objects.get('GD_Background Plane')
        bg_plane_ob.name = "GD_low GD_Background Plane"
        bpy.data.collections["GrabDoc (do not touch contents)"].hide_select = bg_plane_ob.hide_select = False
        bg_plane_ob.select_set(True)

        # Copy the object, link into the scene & rename as high poly
        bg_plane_ob_copy = bg_plane_ob.copy()
        context.collection.objects.link(bg_plane_ob_copy)
        bg_plane_ob_copy.name = "GD_high GD_Background Plane"
        bg_plane_ob_copy.select_set(True)

        # Remove reference material
        for mat in bpy.data.materials:
            if mat.name == "GD_Reference":
                bpy.data.materials.remove(mat)

        # Export models
        bpy.ops.export_scene.fbx(
            filepath=f"{temps_path}\\GD_temp_model.fbx",
            use_selection=True,
            path_mode='ABSOLUTE'
        )

        bpy.data.objects.remove(bg_plane_ob_copy)

        for ob in context.selected_objects:
            ob.select_set(False)

            if ob.name == "GD_low GD_Background Plane":
                ob.name = "GD_Background Plane"
            else:
                ob.name = ob.name[8:]

        if not grabDoc.collSelectable:
            bpy.data.collections["GrabDoc (do not touch contents)"].hide_select = True

        for o in selectedCallback:
            if ob.visible_get():
                ob = context.scene.objects.get(o)
                ob.select_set(True)

        self.open_marmoset(context, temps_path, addon_path)
        return{'FINISHED'}


################################################################################################################
# REGISTRATION
################################################################################################################


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
