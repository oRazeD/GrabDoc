
import bpy, bmesh
from .node_group_utils import ng_setup
from .razeds_bpy_utils.utils import debug
from .gd_constants import *

def remove_setup(context, hard_reset: bool=True) -> None | list:
    '''Completely removes every element of GrabDoc from the scene, not including images reimported after bakes
    
hard_reset: When refreshing a scene we may want to keep certain data-blocks that the user can manipulates'''
    # COLLECTIONS

    # Move objects contained inside the bake group collection to the root collection level and delete the collection
    saved_bake_group_obs = []
    bake_group_coll = bpy.data.collections.get(COLL_OB_NAME)
    if bake_group_coll is not None:
        for ob in bake_group_coll.all_objects:
            # Move object to the master collection
            if hard_reset or not context.scene.grabDoc.onlyRenderColl:
                context.scene.collection.objects.link(ob)
            else:
                saved_bake_group_obs.append(ob)
            
            # Remove the objects from the grabdoc collection
            ob.users_collection[0].objects.unlink(ob)

        bpy.data.collections.remove(bake_group_coll)

    # Move objects accidentally placed in the GD collection to the master collection and then remove the collection
    gd_coll = bpy.data.collections.get(COLL_NAME)
    if gd_coll is not None:
        for ob in gd_coll.all_objects:
            if ob.name not in {BG_PLANE_NAME, ORIENT_GUIDE_NAME, HEIGHT_GUIDE_NAME, TRIM_CAMERA_NAME}:
                # Move object to the master collection
                context.scene.collection.objects.link(ob)

                # Remove object from the grabdoc collection
                ob.gd_coll.objects.unlink(ob)

        bpy.data.collections.remove(gd_coll)

    # HARD RESET - a simpler method for clearing all gd related object

    if hard_reset:
        for ob_name in {BG_PLANE_NAME, ORIENT_GUIDE_NAME, HEIGHT_GUIDE_NAME}:
            if ob_name in bpy.data.objects:
                bpy.data.meshes.remove(bpy.data.meshes[ob_name])

        if TRIM_CAMERA_NAME in bpy.data.objects:
            bpy.data.cameras.remove(bpy.data.cameras[TRIM_CAMERA_NAME])

        if REFERENCE_NAME in bpy.data.materials:
            bpy.data.materials.remove(bpy.data.materials[REFERENCE_NAME])

        for ngroup in bpy.data.node_groups:
            if ngroup.name.startswith(GD_PREFIX):
                bpy.data.node_groups.remove(ngroup)

        return None

    # SOFT RESET

    # Bg plane
    saved_mat = None
    saved_plane_loc = saved_plane_rot = (0, 0, 0)
    if BG_PLANE_NAME in bpy.data.objects:
        plane_ob = bpy.data.objects[BG_PLANE_NAME]

        # Save material/reference & transforms
        saved_mat = plane_ob.active_material
        saved_plane_loc = plane_ob.location.copy()
        saved_plane_rot = plane_ob.rotation_euler.copy()

        bpy.data.meshes.remove(plane_ob.data)

    # Camera
    # Forcibly exit the camera before deleting it so the original users camera position is retained
    reposition_cam = False
    if [area.spaces.active.region_3d.view_perspective for area in context.screen.areas if area.type == 'VIEW_3D'] == ['CAMERA']:
        reposition_cam = True
        bpy.ops.view3d.view_camera()

    if TRIM_CAMERA_NAME in bpy.data.cameras:
        bpy.data.cameras.remove(bpy.data.cameras[TRIM_CAMERA_NAME])
    if HEIGHT_GUIDE_NAME in bpy.data.objects:
        bpy.data.meshes.remove(bpy.data.objects[HEIGHT_GUIDE_NAME].data)
    if ORIENT_GUIDE_NAME in bpy.data.objects:
        bpy.data.meshes.remove(bpy.data.objects[ORIENT_GUIDE_NAME].data)

    return saved_plane_loc, saved_plane_rot, saved_mat, reposition_cam, saved_bake_group_obs


def scene_setup(self, context) -> None: # Needs self for update functions to register?
    '''Generate/setup all relevant GrabDoc object, collections, node groups and scene settings'''
    grabDoc = context.scene.grabDoc
    view_layer = context.view_layer

    # PRELIMINARY

    saved_active_collection = view_layer.active_layer_collection
    saved_selected_obs = view_layer.objects.selected.keys()

    gd_coll = bpy.data.collections.get(COLL_NAME)

    if context.object:
        active_ob = context.object
        activeCallback = active_ob.name
        modeCallback = active_ob.mode

        if active_ob.hide_viewport:
            active_ob.hide_viewport = False
        elif gd_coll is not None and gd_coll.hide_viewport:
            gd_coll.hide_viewport = False

        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode = 'OBJECT')

    # Deselect all objects
    for ob in context.selected_objects:
        ob.select_set(False)

    # Remove all related GrabDoc datablocks, keeping some necessary values
    saved_plane_loc, saved_plane_rot, saved_mat, reposition_cam, saved_bake_group_obs = remove_setup(context, hard_reset=False)

    # Set scene resolution (Trying to avoid destructively changing values, but these two need to be changed)
    context.scene.render.resolution_x = grabDoc.exportResX
    context.scene.render.resolution_y = grabDoc.exportResY

    # COLLECTIONS

    # Create a bake group collection if requested
    if grabDoc.onlyRenderColl:
        bake_group_coll = bpy.data.collections.new(name = COLL_OB_NAME)
        bake_group_coll.is_gd_collection = True

        context.scene.collection.children.link(bake_group_coll)
        view_layer.active_layer_collection = view_layer.layer_collection.children[-1]

        if len(saved_bake_group_obs):
            for ob in saved_bake_group_obs:
                bake_group_coll.objects.link(ob)

    # Create main GrabDoc collection
    gd_coll = bpy.data.collections.new(name = COLL_NAME)
    gd_coll.is_gd_collection = True

    context.scene.collection.children.link(gd_coll)
    view_layer.active_layer_collection = view_layer.layer_collection.children[-1]

    # Make the GrabDoc collection the active collection
    view_layer.active_layer_collection = view_layer.layer_collection.children[gd_coll.name]

    # BG PLANE
    
    bpy.ops.mesh.primitive_plane_add(
        size=grabDoc.scalingSet,
        calc_uvs=True,
        align='WORLD',
        location=saved_plane_loc,
        rotation=saved_plane_rot
    )

    # Rename newly made BG Plane & set a reference to it
    context.object.name = context.object.data.name = BG_PLANE_NAME
    plane_ob = bpy.data.objects[BG_PLANE_NAME]

    # Prepare proper plane scaling
    if grabDoc.exportResX != grabDoc.exportResY:
        if grabDoc.exportResX > grabDoc.exportResY:
            div_factor = grabDoc.exportResX / grabDoc.exportResY

            plane_ob.scale[1] /= div_factor
        else:
            div_factor = grabDoc.exportResY / grabDoc.exportResX

            plane_ob.scale[0] /= div_factor

        bpy.ops.object.transform_apply(location=False, rotation=False)
    
    plane_ob.select_set(False)
    plane_ob.is_gd_object = True
    plane_ob.show_wire = True
    plane_ob.lock_scale[0] = plane_ob.lock_scale[1] = plane_ob.lock_scale[2] = True

    # Add reference to the plane if one has been added, else find and remove any existing reference materials
    if grabDoc.refSelection and not grabDoc.modalState:
        for mat in bpy.data.materials:
            if mat.name == REFERENCE_NAME:
                mat.node_tree.nodes.get('Image Texture').image = grabDoc.refSelection
                break
        else:
            # Create a new material & turn on node use
            mat = bpy.data.materials.new(REFERENCE_NAME)
            mat.use_nodes = True

            # Get / load nodes
            output_node = mat.node_tree.nodes.get('Material Output')
            output_node.location = (0,0)

            mat.node_tree.nodes.remove(mat.node_tree.nodes.get('Principled BSDF'))

            image_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
            image_node.image = grabDoc.refSelection
            image_node.location = (-300,0)

            # Link materials
            mat.node_tree.links.new(output_node.inputs["Surface"], image_node.outputs["Color"])
            
        plane_ob.active_material = bpy.data.materials[REFERENCE_NAME]

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    space.shading.color_type = 'TEXTURE'
    else:
        # Refresh original material and then delete the reference material
        if saved_mat is not None:
            plane_ob.active_material = saved_mat

        # TODO This is the exception to splitting the setup and remove operations into separate functions, maybe can fix?
        if REFERENCE_NAME in bpy.data.materials:
            bpy.data.materials.remove(bpy.data.materials[REFERENCE_NAME])

    # Grid for better snapping and measurements
    if grabDoc.gridSubdivisions and grabDoc.useGrid:
        # Create & load new bmesh
        bm = bmesh.new()
        bm.from_mesh(plane_ob.data)

        # Subdivide
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=grabDoc.gridSubdivisions, use_grid_fill=True)

        # Write back to the mesh
        bm.to_mesh(plane_ob.data)

    # CAMERA

    # Add Trim Camera & change settings
    trim_cam_data = bpy.data.cameras.new(TRIM_CAMERA_NAME)
    trim_cam_ob = bpy.data.objects.new(TRIM_CAMERA_NAME, trim_cam_data)

    trim_cam_ob.location = (0, 0, 15 * grabDoc.scalingSet)
    trim_cam_ob.parent = plane_ob
    trim_cam_ob.is_gd_object = True
    #trim_cam_ob.hide_viewport = trim_cam_ob.hide_select = True  # TODO This occasionally causes visual errors when in camera view?

    trim_cam_data.type = 'ORTHO'
    trim_cam_data.display_size = .01
    trim_cam_data.passepartout_alpha = 1
    trim_cam_data.ortho_scale = grabDoc.scalingSet
    trim_cam_data.clip_start = 0.1
    trim_cam_data.clip_end = 1000 * (grabDoc.scalingSet / 25) # Match scale to cameras clipping distance 

    gd_coll.objects.link(trim_cam_ob)
    context.scene.camera = trim_cam_ob

    if reposition_cam:
        bpy.ops.view3d.view_camera() # Needed to do twice or else Blender decides where the users viewport camera is located when they exit

    # HEIGHT GUIDE

    if grabDoc.exportHeight and grabDoc.rangeTypeHeight == 'MANUAL':
        generate_manual_height_guide_mesh(HEIGHT_GUIDE_NAME, plane_ob)

    # ORIENT GUIDE

    generate_plane_orient_guide_mesh(ORIENT_GUIDE_NAME, plane_ob)
    
    # NODE GROUPS

    ng_setup()

    # CLEANUP

    # Select original object(s)
    for ob_name in saved_selected_obs:
        ob = context.scene.objects.get(ob_name)
        ob.select_set(True)

    # Select original active collection, active object & the context mode
    try:
        view_layer.active_layer_collection = saved_active_collection

        view_layer.objects.active = bpy.data.objects[activeCallback]

        if activeCallback:
            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode = modeCallback)
    except UnboundLocalError:
        pass

    # Hide collections & make unselectable if requested (run this after everything else)
    gd_coll.hide_select = not grabDoc.collSelectable
    gd_coll.hide_viewport = not grabDoc.collVisible
    gd_coll.hide_render = not grabDoc.collRendered


def generate_manual_height_guide_mesh(ob_name: str, plane_ob: bpy.types.Object) -> None:
    '''Generate a mesh that gauges the height map range. This is for the "Manual" height map mode and can better inform a correct 0-1 range'''
    # Make a tuple for the planes vertex positions
    camera_corner_vecs = bpy.data.objects[TRIM_CAMERA_NAME].data.view_frame(scene = bpy.context.scene)

    stems_vecs = [(vec[0], vec[1], bpy.context.scene.grabDoc.guideHeight) for vec in camera_corner_vecs]
    ring_vecs = [(vec[0], vec[1], vec[2] + 1) for vec in camera_corner_vecs]

    # Combine both tuples
    ring_vecs += stems_vecs

    # Create new mesh & object data blocks
    new_mesh = bpy.data.meshes.new(ob_name)
    new_ob = bpy.data.objects.new(ob_name, new_mesh)

    # Make a mesh from a list of vertices / edges / faces
    new_mesh.from_pydata(
        vertices=ring_vecs,
        edges=[(0,4), (1,5), (2,6), (3,7), (4,5), (5,6), (6,7), (7,4)],
        faces=[]
    )

    # Display name & update the mesh
    new_mesh.update()

    bpy.context.collection.objects.link(new_ob)

    # Parent the height guide to the BG Plane
    new_ob.is_gd_object = True
    new_ob.parent = plane_ob
    new_ob.hide_select = True


def generate_plane_orient_guide_mesh(ob_name: str, plane_ob: bpy.types.Object) -> None:
    '''Generate a mesh that sits beside the background plane to guide the user to the correct "up" orientation'''
    # Create new mesh & object data blocks
    new_mesh = bpy.data.meshes.new(ob_name)
    new_ob = bpy.data.objects.new(ob_name, new_mesh)

    plane_y = plane_ob.dimensions.y / 2

    # Make a mesh from a list of vertices / edges / faces
    new_mesh.from_pydata(
        vertices=[(-.3, plane_y + .1, 0), (.3, plane_y + .1, 0), (0, plane_y + .35, 0)],
        edges=[(0,2), (0,1), (1,2)],
        faces=[]
    )

    # Display name & update the mesh
    new_mesh.update()

    bpy.context.collection.objects.link(new_ob)

    # Parent the height guide to the BG Plane
    new_ob.parent = plane_ob
    new_ob.hide_select = True
    new_ob.is_gd_object = True


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
