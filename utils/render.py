import bpy
from mathutils import Vector
from bpy.types import Object

from ..constants import Global
from .generic import get_user_preferences


def is_object_gd_valid(
        ob: Object,
        has_prefix: bool=False,
        render_visible: bool=True,
        invalid_type: bool=True,
        is_gd_ob: bool=False
    ) -> bool:
    """Basic validation checks to detect if an object
    will work well within the GrabDoc environment"""
    # Default off
    if has_prefix and not ob.name.startswith(Global.PREFIX):
        return False
    if is_gd_ob and not ob.gd_object:
        return False
    if not is_gd_ob and ob.gd_object:
        return False

    # Default on
    if render_visible and ob.hide_render:
        return False
    if invalid_type and ob.type in Global.INVALID_BAKE_TYPES:
        return False
    return True


def in_viewing_frustrum(vector: Vector) -> bool:
    """Decide whether a given object is within the cameras viewing frustrum."""
    bg_plane = bpy.data.objects[Global.BG_PLANE_NAME]
    viewing_frustrum = (
        Vector((bg_plane.dimensions.x * -1.25 + bg_plane.location[0],
                bg_plane.dimensions.y * -1.25 + bg_plane.location[1],
                -100)),
        Vector((bg_plane.dimensions.x * 1.25 + bg_plane.location[0],
                bg_plane.dimensions.y * 1.25 + bg_plane.location[1],
                100))
    )
    for i in range(0, 3):
        if (vector[i] < viewing_frustrum[0][i] \
        and vector[i] < viewing_frustrum[1][i] \
        or  vector[i] > viewing_frustrum[0][i] \
        and vector[i] > viewing_frustrum[1][i]):
            return False
    return True


def get_rendered_objects() -> set | None:
    """Generate a list of all objects that will be rendered
    based on its origin position in world space"""
    objects = set()
    if bpy.context.scene.gd.use_bake_collection:
        for coll in bpy.data.collections:
            if coll.gd_collection is False:
                continue
            objects.update(
                [ob for ob in coll.all_objects if is_object_gd_valid(ob)]
            )
            # TODO: Old method; profile it
            #for ob in coll.all_objects:
            #    if is_valid_grabdoc_object(ob):
            #        rendered_obs.add(ob.name)
        return objects

    objects = bpy.context.view_layer.objects
    objects = [ob for ob in objects if is_object_gd_valid(ob)]

    if not get_user_preferences().render_within_frustrum:
        return objects

    # Distance based filter
    filtered_objects = set()
    for ob in objects:
        local_bbox_center = .125 * sum(
            (Vector(ob) for ob in ob.bound_box), Vector()
        )
        global_bbox_center = ob.matrix_world @ local_bbox_center
        if in_viewing_frustrum(global_bbox_center):
            filtered_objects.add(ob)
    return filtered_objects


def set_guide_height(objects: list[Object]=None) -> None:
    """Set guide height maximum property value
    based on a given list of objects"""
    tallest_vert = find_tallest_object(objects)
    bg_plane = bpy.data.objects.get(Global.BG_PLANE_NAME)
    bpy.context.scene.gd.height[0].distance = tallest_vert-bg_plane.location[2]


def find_tallest_object(objects: list[Object]=None) -> float:
    """Find the tallest points in the viewlayer by looping
    through objects to find the highest vertex on the Z axis"""
    if objects is None:
        objects = bpy.context.selectable_objects

    depsgraph = bpy.context.evaluated_depsgraph_get()
    tallest_verts = []
    objects = [
        ob for ob in objects if not ob.name.startswith(Global.PREFIX)
    ]
    for ob in objects:
        ob_eval = ob.evaluated_get(depsgraph)
        try:
            mesh_eval = ob_eval.to_mesh()
        except RuntimeError:
            # NOTE: Object can't be evaluates as mesh; maybe particle system
            continue

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
        bpy.context.scene.gd.height[0].method = 'MANUAL'
        # NOTE: Fallback to manual height value
        return bpy.context.scene.gd.height[0].distance
    return max(tallest_verts)


def set_color_management(
        view_transform: str = 'Standard',
        look:           str = 'None',
        display_device: str = 'sRGB'
    ) -> None:
    """Helper function for supporting custom color management
     profiles. Ignores anything that isn't compatible"""
    display_settings = bpy.context.scene.display_settings
    display_settings.display_device = display_device
    view_settings = bpy.context.scene.view_settings
    view_settings.view_transform    = view_transform
    view_settings.look              = look
    view_settings.exposure          = 0
    view_settings.gamma             = 1
    view_settings.use_curve_mapping = False
    view_settings.use_hdr_view      = False
