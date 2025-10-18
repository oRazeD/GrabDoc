import os

import bpy
from bpy.types import Context
from bpy.props import CollectionProperty

from ..baker import Baker
from ..constants import Global
from .io import get_filepath, get_format
from .generic import load_properties, save_properties


def baker_setup(context: Context) -> dict:
    """Baker scene bootstrapper."""
    scene            = context.scene
    gd               = scene.gd
    render           = scene.render
    eevee            = scene.eevee
    cycles           = scene.cycles
    view_layer       = context.view_layer
    display          = scene.display
    shading          = scene.display.shading
    view_settings    = scene.view_settings
    display_settings = scene.display_settings
    image_settings   = render.image_settings

    properties = (view_layer, render, eevee, cycles,
                  shading, display, view_settings,
                  display_settings, image_settings)
    saved_properties = save_properties(properties)
    saved_properties['bpy.context.scene.camera']       = scene.camera
    saved_properties['bpy.context.scene.gd.reference'] = gd.reference

    # Active Camera
    for area in context.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        for space in area.spaces:
            space.use_local_camera = False
            break
    scene.camera = bpy.data.objects.get(Global.TRIM_CAMERA_NAME)
    if scene.world:
        scene.world.use_nodes = False

    view_layer.use = render.use_single_layer = True
    eevee.use_taa_reprojection = False

    cycles.pixel_filter_type = 'BLACKMAN_HARRIS'

    render.resolution_x          = gd.resolution_x
    render.resolution_y          = gd.resolution_y
    render.resolution_percentage = 100
    render.use_sequencer = render.use_compositing = False
    render.dither_intensity = 0

    # Output
    # NOTE: If background plane not visible in render, create alpha channel
    image_settings.color_mode = 'RGB'
    if not gd.coll_rendered or gd.use_transparent:
        image_settings.color_mode = 'RGBA'
        render.film_transparent   = True

    # Format
    image_settings.file_format = gd.format
    if gd.format == 'OPEN_EXR':
        image_settings.color_depth = gd.exr_depth
    elif gd.format != 'TARGA':
        image_settings.color_depth = gd.depth
    if gd.format == "PNG":
        image_settings.compression = gd.png_compression

    # Viewport shading
    shading.show_backface_culling   = \
    shading.show_xray               = \
    shading.show_shadows            = \
    shading.show_cavity             = \
    shading.use_dof                 = \
    shading.show_object_outline     = \
    shading.show_specular_highlight = False

    # Background plane visibility
    bg_plane = bpy.data.objects.get(Global.BG_PLANE_NAME)
    bg_plane.hide_viewport = not gd.coll_visible
    bg_plane.hide_render   = not gd.coll_rendered or gd.use_transparent
    bg_plane.hide_set(False)

    return saved_properties


def baker_cleanup(context: Context, properties: dict) -> None:
    """Baker core cleanup, reverses any values changed by `baker_setup`."""
    if context.scene.world:
        context.scene.world.use_nodes = True
    load_properties(properties)


def get_baker_by_index(
        collection: CollectionProperty, index: int
    ) -> Baker | None:
    """Get a specific baker based on a given collection
    property and custom index property value."""
    for baker in collection:
        if baker.index == index:
            return baker
    return None


def get_bakers(filter_enabled: bool = False) -> list[Baker]:
    """Get all bakers in the current scene."""
    all_bakers = []
    for baker_id in [baker.ID for baker in Baker.__subclasses__()]:
        baker = getattr(bpy.context.scene.gd, baker_id)
        # NOTE: Flatten collections into single list
        for bake_map in baker:
            if filter_enabled \
            and (not bake_map.enabled or not bake_map.visibility):
                continue
            all_bakers.append(bake_map)
    return all_bakers


def get_baker_collections() -> list[CollectionProperty]:
    """Get all baker collection properties in the current scene."""
    bakers = []
    for baker_id in [baker.ID for baker in Baker.__subclasses__()]:
        baker = getattr(bpy.context.scene.gd, baker_id)
        bakers.append(baker)
    return bakers


def import_baker_textures(bakers: list[Baker]) -> None:
    """Import last exported textures as a material for use inside of Blender."""
    mat = bpy.data.materials.get(Global.REIMPORT_MAT_NAME)
    if mat is None:
        mat = bpy.data.materials.new(Global.REIMPORT_MAT_NAME)
    mat.use_nodes = True

    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs["Emission Color"].default_value    = (0,0,0,1)
    bsdf.inputs["Emission Strength"].default_value = 1

    y_offset = 256
    gd = bpy.context.scene.gd
    for baker in bakers:
        image = mat.node_tree.nodes.get(baker.ID)
        if image is None:
            image = mat.node_tree.nodes.new('ShaderNodeTexImage')
        image.hide = True
        image.name = image.label = baker.ID
        image.location = (-300, y_offset)
        y_offset -= 32

        filename = f'{gd.filename}_{baker.ID}'
        filepath = os.path.join(get_filepath(), filename + get_format())
        if not os.path.exists(filepath):
            continue
        image.image = bpy.data.images.load(filepath, check_existing=True)
        if baker.VIEW_TRANSFORM == 'Raw':
            image.image.colorspace_settings.name = 'Non-Color'

        baker.reimport_setup(mat, image)
