
import bpy
from mathutils import Vector
from .gd_constants import *


def get_rendered_objects(context) -> set:
    '''Generate a list of all objects that will be rendered based on its origin position in world space'''
    rendered_obs = [BG_PLANE_NAME]

    if context.scene.grabDoc.onlyRenderColl:
        for coll in bpy.data.collections:
            if coll.is_gd_collection:
                for ob in coll.all_objects:
                    if (
                        not ob.hide_render
                        and ob.type not in {'EMPTY', 'VOLUME', 'ARMATURE', 'LATTICE', 'LIGHT', 'LIGHT_PROBE', 'CAMERA'}
                        and not ob.is_gd_object
                        ):
                        rendered_obs.append(ob.name)
    else:
        for ob in context.view_layer.objects:
            if (
                not ob.hide_render
                and ob.type not in {'EMPTY', 'VOLUME', 'ARMATURE', 'LATTICE', 'LIGHT', 'LIGHT_PROBE', 'CAMERA'}
                and not ob.is_gd_object
                ):
                local_bbox_center = .125 * sum((Vector(b) for b in ob.bound_box), Vector())
                global_bbox_center = ob.matrix_world @ local_bbox_center

                if is_in_viewing_spectrum(global_bbox_center):
                    rendered_obs.append(ob.name)
    return set(rendered_obs)


def is_in_viewing_spectrum(vec_check: Vector) -> bool:
    '''Decide whether a given object is within the cameras viewing spectrum'''
    bg_plane = bpy.data.objects[BG_PLANE_NAME]

    vec1 = Vector((bg_plane.dimensions.x * -1.25 + bg_plane.location[0], bg_plane.dimensions.y * -1.25 + bg_plane.location[1], -100))
    vec2 = Vector((bg_plane.dimensions.x * 1.25 + bg_plane.location[0], bg_plane.dimensions.y * 1.25 + bg_plane.location[1], 100))

    for i in range(0, 3):
        if (vec_check[i] < vec1[i] and vec_check[i] < vec2[i] or vec_check[i] > vec1[i] and vec_check[i] > vec2[i]):
            return False
    return True


def find_tallest_object(self, context) -> None:
    '''Find the tallest points in the viewlayer by looping through objects to find the highest vertex on the Z axis'''
    depsgraph = context.evaluated_depsgraph_get()

    all_tallest_verts = []
    for ob in context.view_layer.objects:
        if ob.name in self.rendered_obs and ob.type in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'} and not ob.name.startswith(GD_PREFIX):
            # Invoke to_mesh() for evaluated object.
            ob_eval = ob.evaluated_get(depsgraph)
            mesh_from_eval = ob_eval.to_mesh()

            # Get global coordinates of vertices
            global_vert_coords = [ob_eval.matrix_world @ v.co for v in mesh_from_eval.vertices]

            # Find the highest Z value amongst the object's verts and then append it to list
            if len(global_vert_coords):
                max_z_coord = max([co.z for co in global_vert_coords])

                all_tallest_verts.append(max_z_coord)

            # Remove temporary mesh.
            ob_eval.to_mesh_clear()

    # Set the heights guide to the tallest found point
    if len(all_tallest_verts):
        context.scene.grabDoc.guideHeight = max(all_tallest_verts) - bpy.data.objects.get(BG_PLANE_NAME).location[2]


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
