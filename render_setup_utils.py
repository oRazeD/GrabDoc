
import bpy
from mathutils import Vector


# GENERATE A LIST OF ALL OBJECTS THAT WILL BE RENDERED BASED ON ITS ORIGINS POSITION IN WORLD SPACE
def get_rendered_objects(self, context):
    render_list = ['GD_Background Plane']

    if context.scene.grabDoc.onlyRenderColl:  
        for coll in bpy.data.collections:
            if coll.name in ("GrabDoc Objects (put objects here)", "GrabDoc (do not touch contents)"):
                for ob in coll.all_objects:
                    if not ob.hide_render and ob.type in ('MESH', 'CURVE') and not ob.name.startswith('GD_'):
                        render_list.append(ob.name)
    else:
        for ob in context.view_layer.objects:
            if not ob.hide_render and ob.type in ('MESH', 'CURVE') and not ob.name.startswith('GD_'):
                local_bbox_center = .125 * sum((Vector(b) for b in ob.bound_box), Vector())
                global_bbox_center = ob.matrix_world @ local_bbox_center

                if is_in_viewing_spectrum(global_bbox_center):
                    render_list.append(ob.name)
    return render_list


# DECIDE WHETHER A GIVEN OBJECT IS WITHIN THE CAMERAS VIEWING SPECTRUM
def is_in_viewing_spectrum(vec_check):
    bg_plane = bpy.data.objects["GD_Background Plane"]

    vec1 = Vector((bg_plane.dimensions.x * -1.25 + bg_plane.location[0], bg_plane.dimensions.y * -1.25 + bg_plane.location[1], -100))
    vec2 = Vector((bg_plane.dimensions.x * 1.25 + bg_plane.location[0], bg_plane.dimensions.y * 1.25 + bg_plane.location[1], 100))

    for i in range(0, 3):
        if (vec_check[i] < vec1[i] and vec_check[i] < vec2[i] or vec_check[i] > vec1[i] and vec_check[i] > vec2[i]):
            return False
    return True


# FIND THE TALLEST POINTS IN THE VIEW LAYER BY LOOPING THROUGH OBJECTS TO FIND THE HIGHEST VERTEX
#
# I hate this. Using vertices to find the tallest point is
# unnacceptable in the face of modifier geometry and curves
def find_tallest_object(self, context):
    tallest_vert = 0

    for ob in context.view_layer.objects:
        if ob.name in self.render_list and ob.type == 'MESH' and not ob.name.startswith('GD_'):
            # Get global coordinates of vertices
            global_vert_coords = [ob.matrix_world @ v.co for v in ob.data.vertices]

            # Find the highest Z value amongst the object's verts
            if len(global_vert_coords):
                max_z_co = max([co.z for co in global_vert_coords])
                
                if max_z_co > tallest_vert:
                    tallest_vert = max_z_co

    # Set the heights guide to the tallest found point
    if tallest_vert:
        context.scene.grabDoc.guideHeight = tallest_vert


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
