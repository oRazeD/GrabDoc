
from ast import List
from mathutils import Vector

import bpy
from bpy.types import Context,  Object

from ..constants import GlobalVariableConstants as Global


def is_valid_grabdoc_object(
        ob: Object,
        has_prefix: bool=False,
        render_visible: bool=True,
        invalid_type: bool=True,
        is_gd_ob: bool=True
    ) -> bool:
    """Basic validation checks to detect if an object
    will work well within the GrabDoc environment"""
    # Default off
    if has_prefix and not ob.name.startswith(Global.GD_PREFIX):
        return False

    # Default on
    if render_visible and not ob.hide_render:
        return False
    if invalid_type and ob.type not in Global.INVALID_RENDER_TYPES:
        return False
    if is_gd_ob and not ob.is_gd_object:
        return False
    return True


def in_viewing_frustrum(vector: Vector) -> bool:
    """Decide whether a given object is
    within the cameras viewing frustrum"""
    bg_plane = bpy.data.objects[Global.BG_PLANE_NAME]
    viewing_frustrum = (
        Vector
        (
            (
                bg_plane.dimensions.x * -1.25 + bg_plane.location[0],
                bg_plane.dimensions.y * -1.25 + bg_plane.location[1],
                -100
            )
        ),
        Vector(
            (
                bg_plane.dimensions.x * -1.25 + bg_plane.location[0],
                bg_plane.dimensions.y * -1.25 + bg_plane.location[1],
                -100
            )
        )
    )
    for i in range(0, 3):
        if (
            vector[i]     < viewing_frustrum[0][i] \
            and vector[i] < viewing_frustrum[1][i] \
            or vector[i]  > viewing_frustrum[0][i] \
            and vector[i] > viewing_frustrum[1][i]
        ):
            return False
    return True


def get_rendered_objects(context: Context) -> set | None:
    """Generate a list of all objects that will be rendered
    based on its origin position in world space"""
    rendered_obs = {Global.BG_PLANE_NAME}
    if context.scene.grabDoc.useBakeCollection:
        for coll in bpy.data.collections:
            if coll.is_gd_collection is False:
                continue
            rendered_obs.update(
                [ob for ob in coll.all_objects if is_valid_grabdoc_object(ob)]
            )
            # TODO: Old method, maybe time it?
            #for ob in coll.all_objects:
            #    if is_valid_grabdoc_object(ob):
            #        rendered_obs.add(ob.name)
        return rendered_obs

    for ob in context.view_layer.objects:
        if is_valid_grabdoc_object(ob):
            local_bbox_center = .125 * sum(
                (Vector(b) for b in ob.bound_box), Vector()
            )
            global_bbox_center = ob.matrix_world @ local_bbox_center

            if in_viewing_frustrum(global_bbox_center):
                rendered_obs.add(ob.name)
    return rendered_obs


def set_guide_height(objects: List[Object]) -> None:
    """Set guide height maximum property value
    based on a given list of objects"""
    tallest_vert = find_tallest_object(objects)
    bg_plane = bpy.data.objects.get(Global.BG_PLANE_NAME)
    bpy.context.scene.grabDoc.guideHeight = \
        tallest_vert - bg_plane.location[2]


def find_tallest_object(objects: List[Object]) -> None:
    """Find the tallest points in the viewlayer by looping
    through objects to find the highest vertex on the Z axis"""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    tallest_verts = []
    objects = [ob for ob in objects if ob.name.startswith(Global.GD_PREFIX)]
    for ob in objects:
        ob_eval = ob.evaluated_get(depsgraph)
        mesh_eval = ob_eval.to_mesh()

        global_vert_co = [
            ob_eval.matrix_world @ v.co for v in mesh_eval.vertices
        ]

        # NOTE: Find highest Z-value amongst
        # object's vertices and append to list
        if len(global_vert_co):
            max_z_co = max(co.z for co in global_vert_co)
            tallest_verts.append(max_z_co)
        ob_eval.to_mesh_clear()
    if not tallest_verts:
        return None
    return max(tallest_verts)


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
