
import bpy
from bpy.types import Operator
from random import random, randint
from .generic_utils import OpInfo
from .render_setup_utils import get_rendered_objects


class GRABDOC_OT_quick_id_setup(OpInfo, Operator):
    """Quickly sets up materials on all objects within the cameras view spectrum"""
    bl_idname = "grab_doc.quick_id_setup"
    bl_label = "Auto ID Full Scene"

    def execute(self, context):
        for mat in bpy.data.materials:
            if mat.name.startswith("GD_RANDOM"):
                bpy.data.materials.remove(mat)

        self.render_list = get_rendered_objects(context)

        for ob in context.view_layer.objects:
            add_mat = True

            if ob.name in self.render_list and not ob.name.startswith('GD_'):
                for slot in ob.material_slots:
                    if slot.name.startswith('GD_ID'):
                        add_mat = False
                        break

                if add_mat:
                    mat = bpy.data.materials.new(f"GD_RANDOM_ID.{randint(0, 100000000)}")
                    mat.use_nodes = True

                    # Set - viewport color
                    mat.diffuse_color = random(), random(), random(), 1

                    bsdf_node = mat.node_tree.nodes.get('Principled BSDF')
                    bsdf_node.inputs[0].default_value = mat.diffuse_color

                    ob.active_material_index = 0
                    ob.active_material = mat

        for mat in bpy.data.materials:
            if (mat.name.startswith('GD_ID') or mat.name.startswith('GD_RANDOM')) and not mat.users:
                bpy.data.materials.remove(mat)
        return{'FINISHED'}


class GRABDOC_OT_quick_id_selected(OpInfo, Operator):
    """Adds a new single material with a random color to the selected objects"""
    bl_idname = "grab_doc.quick_id_selected"
    bl_label = "Add ID to Selected"

    @classmethod
    def poll(cls, context):
        return context.selected_objects

    def execute(self, context):
        mat = bpy.data.materials.new(f"GD_ID.{randint(0, 100000000)}")
        mat.diffuse_color = random(), random(), random(), 1
        mat.use_nodes = True

        bsdf_node = mat.node_tree.nodes.get('Principled BSDF')
        bsdf_node.inputs[0].default_value = mat.diffuse_color

        for ob in context.selected_objects:
            if ob.type in {'MESH', 'CURVE'}:
                ob.active_material_index = 0
                ob.active_material = mat

        for mat in bpy.data.materials:
            if (mat.name.startswith('GD_ID') or mat.name.startswith('GD_RANDOM')) and not mat.users:
                bpy.data.materials.remove(mat)
        return{'FINISHED'}


class GRABDOC_OT_quick_remove_random_mats(OpInfo, Operator):
    """Remove all randomly generated GrabDoc ID materials from the scene"""
    bl_idname = "grab_doc.quick_remove_random_mats"
    bl_label = "All"

    def execute(self, context):
        for mat in bpy.data.materials:
            if mat.name.startswith("GD_RANDOM"):
                bpy.data.materials.remove(mat)
        return{'FINISHED'}


class GRABDOC_OT_quick_remove_manual_mats(OpInfo, Operator):
    """Remove all manually added GrabDoc ID materials from the scene"""
    bl_idname = "grab_doc.quick_remove_manual_mats"
    bl_label = "All"

    def execute(self, context):
        for mat in bpy.data.materials:
            if mat.name.startswith("GD_ID"):
                bpy.data.materials.remove(mat)
        return{'FINISHED'}


class GRABDOC_OT_quick_remove_selected_mats(OpInfo, Operator):
    """Remove all GrabDoc ID materials based on the selected objects from the scene"""
    bl_idname = "grab_doc.quick_remove_selected_mats"
    bl_label = "Selected"

    @classmethod
    def poll(cls, context):
        return context.selected_objects

    def execute(self, context):
        for ob in context.selected_objects:
            if ob.type in {'MESH', 'CURVE'}:
                for slot in ob.material_slots:
                    if slot.name.startswith('GD_ID'):
                        bpy.data.materials.remove(bpy.data.materials[slot.name])
                        break
        return{'FINISHED'}


################################################################################################################
# REGISTRATION
################################################################################################################


classes = (
    GRABDOC_OT_quick_id_setup,
    GRABDOC_OT_quick_id_selected,
    GRABDOC_OT_quick_remove_random_mats,
    GRABDOC_OT_quick_remove_manual_mats,
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
