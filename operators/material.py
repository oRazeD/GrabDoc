from random import random, randint

import bpy
from bpy.types import Context, Operator

from ..constants import Global
from ..utils.generic import UseSelectedOnly
from ..utils.render import get_rendered_objects


class GRABDOC_OT_quick_id_setup(Operator):
    """Sets up materials on all objects within the cameras view frustrum"""
    bl_idname  = "grabdoc.quick_id_setup"
    bl_label   = "Auto ID Full Scene"
    bl_options = {'REGISTER', 'UNDO'}

    @staticmethod
    def generate_random_name(prefix: str,
                             minimum: int=1000,
                             maximum: int=100000) -> str:
        """Generates a random id map name based on a given prefix"""
        while True:
            name = prefix+str(randint(minimum, maximum))
            if name not in bpy.data.materials:
                break
        return name

    @staticmethod
    def quick_material_cleanup() -> None:
        for mat in bpy.data.materials:
            if mat.name.startswith(Global.ID_PREFIX) \
            and not mat.users \
            or mat.name.startswith(Global.RANDOM_ID_PREFIX) \
            and not mat.users:
                bpy.data.materials.remove(mat)

    def execute(self, _context: Context):
        for mat in bpy.data.materials:
            if mat.name.startswith(Global.RANDOM_ID_PREFIX):
                bpy.data.materials.remove(mat)

        rendered_obs = get_rendered_objects()
        for ob in rendered_obs:
            add_mat = True
            if ob.name.startswith(Global.FLAG_PREFIX):
                continue
            for slot in ob.material_slots:
                if slot.name.startswith(Global.ID_PREFIX):
                    add_mat = False
                    break
            if not add_mat:
                continue

            mat = bpy.data.materials.new(
                self.generate_random_name(Global.RANDOM_ID_PREFIX)
            )
            mat.use_nodes = True
            # NOTE: Viewport color
            mat.diffuse_color = (random(), random(), random(), 1)

            bsdf = mat.node_tree.nodes.get('Principled BSDF')
            bsdf.inputs[0].default_value = mat.diffuse_color

            ob.active_material_index = 0
            ob.active_material = mat
        self.quick_material_cleanup()
        return {'FINISHED'}


class GRABDOC_OT_quick_id_selected(UseSelectedOnly, Operator):
    """Adds a new single material with a random color to the selected objects"""
    bl_idname  = "grabdoc.quick_id_selected"
    bl_label   = "Add ID to Selected"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: Context):
        mat = bpy.data.materials.new(
            GRABDOC_OT_quick_id_setup.generate_random_name(Global.ID_PREFIX)
        )
        mat.use_nodes = True
        mat.diffuse_color = (random(), random(), random(), 1)

        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs[0].default_value = mat.diffuse_color

        for ob in context.selected_objects:
            if ob.type not in ('MESH', 'CURVE'):
                continue
            ob.active_material_index = 0
            ob.active_material = mat
        GRABDOC_OT_quick_id_setup.quick_material_cleanup()
        return {'FINISHED'}


class GRABDOC_OT_remove_mats_by_name(Operator):
    """Remove materials based on an internal prefixed name"""
    bl_idname  = "grabdoc.remove_mats_by_name"
    bl_label   = "Remove Mats by Name"
    bl_options = {'REGISTER', 'UNDO'}

    name: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, _context: Context):
        for mat in bpy.data.materials:
            if mat.name.startswith(self.name):
                bpy.data.materials.remove(mat)
        return {'FINISHED'}


class GRABDOC_OT_quick_remove_selected_mats(UseSelectedOnly, Operator):
    """Remove all GrabDoc ID materials based on the selected objects from the scene"""
    bl_idname  = "grabdoc.quick_remove_selected_mats"
    bl_label   = "Remove Selected Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: Context):
        for ob in context.selected_objects:
            if ob.type not in ('MESH', 'CURVE'):
                continue
            for slot in ob.material_slots:
                if not slot.name.startswith(Global.ID_PREFIX):
                    continue
                bpy.data.materials.remove(bpy.data.materials[slot.name])
                break
        return {'FINISHED'}


################################################
# REGISTRATION
################################################


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
