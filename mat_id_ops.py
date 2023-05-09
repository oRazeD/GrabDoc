
import bpy, bpy.types as types
from random import random, randint
from .generic_utils import OpInfo, UseSelectedOnly
from .render_setup_utils import get_rendered_objects
from .constants import GlobalVariableConstants as GlobalVarConst


def generate_random_id_name(id_prefix: str='ID') -> str:
    """Generates a random id map name based on a given prefix"""
    while True:
        new_mat_name = f"{id_prefix}.{randint(1000, 100000)}"
        if new_mat_name not in bpy.data.materials:
            break
    return new_mat_name


class GRABDOC_OT_quick_id_setup(OpInfo, types.Operator):
    """Sets up materials on all objects within the cameras view frustrum"""
    bl_idname = "grab_doc.quick_id_setup"
    bl_label = "Auto ID Full Scene"

    def execute(self, context: types.Context):
        for mat in bpy.data.materials:
            if mat.name.startswith(GlobalVarConst.MAT_ID_RAND_PREFIX):
                bpy.data.materials.remove(mat)

        self.rendered_obs = get_rendered_objects(context)
        for ob in context.view_layer.objects:
            add_mat = True

            if not ob.name.startswith(GlobalVarConst.GD_PREFIX) and ob.name in self.rendered_obs:
                for slot in ob.material_slots:
                    # If a manual ID exists on the object, ignore it
                    if slot.name.startswith(GlobalVarConst.MAT_ID_PREFIX):
                        add_mat = False
                        break

                if not add_mat:
                    continue

                mat = bpy.data.materials.new(generate_random_id_name(GlobalVarConst.MAT_ID_RAND_PREFIX))
                mat.use_nodes = True
                mat.diffuse_color = (random(), random(), random(), 1) # Viewport color

                bsdf_node = mat.node_tree.nodes.get('Principled BSDF')
                bsdf_node.inputs[0].default_value = mat.diffuse_color

                ob.active_material_index = 0
                ob.active_material = mat

        for mat in bpy.data.materials:
            if (mat.name.startswith(GlobalVarConst.MAT_ID_PREFIX) or mat.name.startswith(GlobalVarConst.MAT_ID_RAND_PREFIX)) and not mat.users:
                bpy.data.materials.remove(mat)
        return {'FINISHED'}


class GRABDOC_OT_quick_id_selected(OpInfo, UseSelectedOnly, types.Operator):
    """Adds a new single material with a random color to the selected objects"""
    bl_idname = "grab_doc.quick_id_selected"
    bl_label = "Add ID to Selected"

    def execute(self, context: types.Context):
        mat = bpy.data.materials.new(generate_random_id_name(GlobalVarConst.MAT_ID_PREFIX))
        mat.use_nodes = True
        mat.diffuse_color = (random(), random(), random(), 1)

        bsdf_node = mat.node_tree.nodes.get('Principled BSDF')
        bsdf_node.inputs[0].default_value = mat.diffuse_color

        for ob in context.selected_objects:
            if ob.type in ('MESH', 'CURVE'):
                ob.active_material_index = 0
                ob.active_material = mat

        for mat in bpy.data.materials:
            if (mat.name.startswith(GlobalVarConst.MAT_ID_PREFIX) or mat.name.startswith(GlobalVarConst.MAT_ID_RAND_PREFIX)) and not mat.users:
                bpy.data.materials.remove(mat)
        return {'FINISHED'}


class GRABDOC_OT_remove_mats_by_name(OpInfo, types.Operator):
    """Remove materials based on an internal prefixed name"""
    bl_idname = "grab_doc.remove_mats_by_name"
    bl_label = "Remove Mats by Name"

    mat_name: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, _context: types.Context):
        for mat in bpy.data.materials:
            if mat.name.startswith(self.mat_name):
                bpy.data.materials.remove(mat)
        return {'FINISHED'}


class GRABDOC_OT_quick_remove_selected_mats(OpInfo, UseSelectedOnly, types.Operator):
    """Remove all GrabDoc ID materials based on the selected objects from the scene"""
    bl_idname = "grab_doc.quick_remove_selected_mats"
    bl_label = "Remove Selected Materials"

    def execute(self, context: types.Context):
        for ob in context.selected_objects:
            if ob.type in ('MESH', 'CURVE'):
                for slot in ob.material_slots:
                    if slot.name.startswith(GlobalVarConst.MAT_ID_PREFIX):
                        bpy.data.materials.remove(bpy.data.materials[slot.name])
                        break
        return {'FINISHED'}


################################################################################################################
# REGISTRATION
################################################################################################################


classes = (
    GRABDOC_OT_quick_id_setup,
    GRABDOC_OT_quick_id_selected,
    GRABDOC_OT_remove_mats_by_name,
    GRABDOC_OT_quick_remove_selected_mats
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
