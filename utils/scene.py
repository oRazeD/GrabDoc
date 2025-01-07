import os

import bpy
import bmesh
from bpy.types import Context, Object

from ..constants import Global, Error


# NOTE: Needs self for property update functions to register
def scene_setup(_self, context: Context) -> None:
    """Setup all relevant objects, collections, node groups, and properties."""
    gd = context.scene.gd
    context.scene.render.resolution_x = gd.resolution_x
    context.scene.render.resolution_y = gd.resolution_y

    view_layer              = context.view_layer
    saved_active_collection = view_layer.active_layer_collection
    saved_selected_obs      = view_layer.objects.selected.keys()

    activeCallback = None
    gd_coll = bpy.data.collections.get(Global.COLL_CORE_NAME)
    if context.object:
        active_ob = context.object
        activeCallback = active_ob.name
        modeCallback = active_ob.mode

        if active_ob.hide_viewport:
            active_ob.hide_viewport = False
        elif gd_coll is not None and gd_coll.hide_viewport:
            gd_coll.hide_viewport = False

        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

    for ob in context.selected_objects:
        ob.select_set(False)

    saved_plane_loc, saved_plane_rot, \
    saved_mat, was_viewing_camera, saved_bake_group_obs = \
        scene_cleanup(context, hard_reset=False)

    # Collections
    if gd.use_bake_collection:
        bake_group_coll = bpy.data.collections.new(Global.COLL_GROUP_NAME)
        bake_group_coll.gd_collection = True

        context.scene.collection.children.link(bake_group_coll)
        view_layer.active_layer_collection = \
            view_layer.layer_collection.children[-1]

        if len(saved_bake_group_obs):
            for ob in saved_bake_group_obs:
                bake_group_coll.objects.link(ob)

    gd_coll = bpy.data.collections.new(name=Global.COLL_CORE_NAME)
    gd_coll.gd_collection = True
    context.scene.collection.children.link(gd_coll)
    view_layer.active_layer_collection = \
        view_layer.layer_collection.children[-1]
    view_layer.active_layer_collection = \
        view_layer.layer_collection.children[gd_coll.name]

    # Background plane
    bpy.ops.mesh.primitive_plane_add(size=gd.scale,
                                     calc_uvs=True,
                                     align='WORLD',
                                     location=saved_plane_loc,
                                     rotation=saved_plane_rot)
    context.object.name = context.object.data.name = Global.BG_PLANE_NAME
    plane_ob = bpy.data.objects[Global.BG_PLANE_NAME]
    plane_ob.select_set(False)
    plane_ob.show_wire = True
    plane_ob.lock_scale[0] = \
    plane_ob.lock_scale[1] = \
    plane_ob.lock_scale[2] = True

    if gd.resolution_x != gd.resolution_y:
        if gd.resolution_x > gd.resolution_y:
            div_factor = gd.resolution_x / gd.resolution_y
            plane_ob.scale[1] /= div_factor
        else:
            div_factor = gd.resolution_y / gd.resolution_x
            plane_ob.scale[0] /= div_factor
        bpy.ops.object.transform_apply(location=False, rotation=False)

    # Reference
    if gd.reference and not gd.preview_state:
        for mat in bpy.data.materials:
            if mat.name == Global.REFERENCE_NAME:
                mat.node_tree.nodes.get('Image Texture').image = gd.reference
                break
        else:
            # Create a new material & turn on node use
            mat = bpy.data.materials.new(Global.REFERENCE_NAME)
            mat.use_nodes = True

            # Get / load nodes
            output = mat.node_tree.nodes['Material Output']
            output.location = (0,0)
            mat.node_tree.nodes.remove(
                mat.node_tree.nodes['Principled BSDF']
            )

            image = mat.node_tree.nodes.new('ShaderNodeTexImage')
            image.image = gd.reference
            image.location = (-300,0)

            mat.node_tree.links.new(output.inputs["Surface"],
                                    image.outputs["Color"])

        plane_ob.active_material = bpy.data.materials[Global.REFERENCE_NAME]

        for area in context.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for space in area.spaces:
                space.shading.color_type = 'TEXTURE'
    else:
        # Refresh original material and delete the reference material
        if saved_mat is not None:
            plane_ob.active_material = saved_mat
        # TODO: Removal operation inside of a setup function
        if Global.REFERENCE_NAME in bpy.data.materials:
            bpy.data.materials.remove(bpy.data.materials[Global.REFERENCE_NAME])

    # Grid
    if gd.use_grid and gd.grid_subdivs:
        bm = bmesh.new()
        bm.from_mesh(plane_ob.data)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges,
                                  cuts=gd.grid_subdivs,
                                  use_grid_fill=True)
        bm.to_mesh(plane_ob.data)

    # Camera
    camera_data = bpy.data.cameras.new(Global.TRIM_CAMERA_NAME)
    camera_data.type               = 'ORTHO'
    camera_data.display_size       = .01
    camera_data.ortho_scale        = gd.scale
    camera_data.clip_start         = 0.1
    camera_data.clip_end           = 1000 * (gd.scale / 25)
    camera_data.passepartout_alpha = 1

    camera_ob = bpy.data.objects.new(Global.TRIM_CAMERA_NAME, camera_data)
    camera_ob.parent      = plane_ob
    camera_object_z       = Global.CAMERA_DISTANCE * gd.scale
    camera_ob.location    = (0, 0, camera_object_z)
    camera_ob.hide_select = camera_ob.gd_object = True

    gd_coll.objects.link(camera_ob)
    context.scene.camera = camera_ob
    if was_viewing_camera:
        bpy.ops.view3d.view_camera()

    # Point cloud
    if gd.height[0].enabled and gd.height[0].method == 'MANUAL':
        generate_height_guide(Global.HEIGHT_GUIDE_NAME, plane_ob)
    generate_orientation_guide(Global.ORIENT_GUIDE_NAME, plane_ob)

    # Cleanup
    for ob_name in saved_selected_obs:
        ob = context.scene.objects.get(ob_name)
        ob.select_set(True)

    view_layer.active_layer_collection = saved_active_collection
    if activeCallback:
        view_layer.objects.active = bpy.data.objects[activeCallback]
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode=modeCallback)

    gd_coll.hide_select   = not gd.coll_selectable
    gd_coll.hide_viewport = not gd.coll_visible
    gd_coll.hide_render   = not gd.coll_rendered


def scene_cleanup(context: Context, hard_reset: bool=True) -> None | list:
    """Completely removes every element of GrabDoc from
    the scene, not including images reimported after bakes

    hard_reset: When refreshing a scene we may want to keep
    certain data-blocks that the user can manipulates"""
    # NOTE: Move objects contained inside the bake group collection
    # to the root collection level and delete the collection
    saved_bake_group_obs = []
    bake_group_coll = bpy.data.collections.get(Global.COLL_GROUP_NAME)
    if bake_group_coll is not None:
        for ob in bake_group_coll.all_objects:
            if hard_reset or not context.scene.gd.use_bake_collection:
                context.scene.collection.objects.link(ob)
            else:
                saved_bake_group_obs.append(ob)
            ob.users_collection[0].objects.unlink(ob)
        bpy.data.collections.remove(bake_group_coll)

    # NOTE: Compensate for objects accidentally placed in the core collection
    gd_coll = bpy.data.collections.get(Global.COLL_CORE_NAME)
    if gd_coll is not None:
        for ob in gd_coll.all_objects:
            if ob.name not in (Global.BG_PLANE_NAME,
                               Global.ORIENT_GUIDE_NAME,
                               Global.HEIGHT_GUIDE_NAME,
                               Global.TRIM_CAMERA_NAME):
                context.scene.collection.objects.link(ob)
                ob.gd_coll.objects.unlink(ob)
        bpy.data.collections.remove(gd_coll)

    if hard_reset:
        for ob_name in (Global.BG_PLANE_NAME,
                        Global.ORIENT_GUIDE_NAME,
                        Global.HEIGHT_GUIDE_NAME):
            if ob_name in bpy.data.objects:
                bpy.data.meshes.remove(bpy.data.meshes[ob_name])
        if Global.TRIM_CAMERA_NAME in bpy.data.objects:
            bpy.data.cameras.remove(bpy.data.cameras[Global.TRIM_CAMERA_NAME])
        if Global.REFERENCE_NAME in bpy.data.materials:
            bpy.data.materials.remove(bpy.data.materials[Global.REFERENCE_NAME])
        for group in bpy.data.node_groups:
            if group.name.startswith(Global.FLAG_PREFIX):
                bpy.data.node_groups.remove(group)
        return None

    saved_mat = None
    saved_plane_loc = saved_plane_rot = (0, 0, 0)
    if Global.BG_PLANE_NAME in bpy.data.objects:
        plane_ob = bpy.data.objects[Global.BG_PLANE_NAME]
        saved_mat = plane_ob.active_material
        saved_plane_loc = plane_ob.location.copy()
        saved_plane_rot = plane_ob.rotation_euler.copy()
        bpy.data.meshes.remove(plane_ob.data)

    # NOTE: Forcibly exit the camera before deleting it
    # so the original users camera position is retained
    was_viewing_camera = False
    if camera_in_3d_view():
        was_viewing_camera = True
        bpy.ops.view3d.view_camera()

    if Global.TRIM_CAMERA_NAME in bpy.data.cameras:
        bpy.data.cameras.remove(bpy.data.cameras[Global.TRIM_CAMERA_NAME])
    if Global.HEIGHT_GUIDE_NAME in bpy.data.meshes:
        bpy.data.meshes.remove(bpy.data.meshes[Global.HEIGHT_GUIDE_NAME])
    if Global.ORIENT_GUIDE_NAME in bpy.data.meshes:
        bpy.data.meshes.remove(bpy.data.meshes[Global.ORIENT_GUIDE_NAME])

    return saved_plane_loc, saved_plane_rot, saved_mat, \
           was_viewing_camera, saved_bake_group_obs


def validate_scene(
        context: Context,
        is_exporting: bool=True,
        report_value=False,
        report_string=""
    ) -> tuple[bool, str]:
    """Determine if specific parts of the scene
    are set up incorrectly and return a detailed
    explanation of things for the user to fix."""
    gd = context.scene.gd

    if not Global.TRIM_CAMERA_NAME in context.view_layer.objects \
    and not report_value:
        report_value = True
        report_string = Error.CAMERA_NOT_FOUND

    if gd.use_bake_collection and not report_value:
        if not len(bpy.data.collections[Global.COLL_GROUP_NAME].objects):
            report_value = True
            report_string = Error.BAKE_GROUPS_EMPTY

    if is_exporting is False:
        return report_value, report_string

    if not report_value \
    and not gd.filepath == "//" \
    and not os.path.exists(gd.filepath):
        report_value = True
        report_string = Error.NO_VALID_PATH_SET
    return report_value, report_string


def is_scene_valid() -> bool:
    """Validate all required objects to determine correct scene setup."""
    object_checks = (Global.COLL_CORE_NAME        in bpy.data.collections,
                     Global.BG_PLANE_NAME    in bpy.context.scene.objects,
                     Global.TRIM_CAMERA_NAME in bpy.context.scene.objects)
    return True in object_checks


def camera_in_3d_view() -> bool:
    """Check if the first found 3D View is currently viewing the camera."""
    for area in bpy.context.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        return area.spaces.active.region_3d.view_perspective == 'CAMERA'


def generate_height_guide(name: str, plane_ob: Object) -> None:
    """Generate a mesh that represents the height map range.

    Generally used for `Manual` Height method to visualize the 0-1 range."""
    scene = bpy.context.scene
    trim_camera = bpy.data.objects.get(Global.TRIM_CAMERA_NAME)
    camera_view_frame = trim_camera.data.view_frame(scene=scene)

    stems_vecs = [
        (v[0], v[1], scene.gd.height[0].distance) for v in camera_view_frame
    ]
    ring_vecs = [(v[0], v[1], v[2]+1) for v in camera_view_frame]
    ring_vecs += stems_vecs

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices=ring_vecs,
                     edges=[(0,4), (1,5), (2,6),
                            (3,7), (4,5), (5,6),
                            (6,7), (7,4)],
                     faces=[])
    mesh.update()

    ob = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(ob)
    ob.gd_object   = True
    ob.parent      = plane_ob
    ob.hide_select = True


def generate_orientation_guide(name: str, plane_ob: Object) -> None:
    """Generate a mesh object that sits beside the background plane
    to guide the user to the correct "up" orientation"""
    mesh = bpy.data.meshes.new(name)
    plane_y = plane_ob.dimensions.y / 2
    mesh.from_pydata(vertices=[(-.3, plane_y+.1,  0),
                               (.3,  plane_y+.1,  0),
                               (0,   plane_y+.35, 0)],
                     edges=[(0,2), (0,1), (1,2)],
                     faces=[])
    mesh.update()

    ob = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(ob)
    ob.parent      = plane_ob
    ob.hide_select = True
    ob.gd_object   = True
