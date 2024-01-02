import os
from typing import Iterable

import bpy
from bpy.types import Context, Object

from ..constants import GlobalVariableConstants as Global
from .node import add_ng_to_mat
from .generic import get_format
from .render import set_guide_height, get_rendered_objects


################################################
# BAKER SETUP & CLEANUP
################################################


def set_color_management(display_device: str='None') -> None:
    """Helper function for supporting custom color management
     profiles. Ignores anything that isn't compatible"""
    display_settings = bpy.context.scene.display_settings
    view_settings = bpy.context.scene.view_settings

    if display_device not in display_settings.display_device:
        if display_device == 'sRGB':
            alt_display_device = 'Blender Display'
            alt_view_transform = 'sRGB'
        else: # None
            alt_display_device = 'Blender Display'
            alt_view_transform = 'Raw'

        try:
            display_settings.display_device = alt_display_device
            view_settings.view_transform = alt_view_transform
        except TypeError:
            pass
    else:
        display_settings.display_device = display_device
        view_settings.view_transform = 'Standard'

    view_settings.look = 'None'
    view_settings.exposure = 0
    view_settings.gamma = 1


def setup_baker(self, context: Context):
    scene = context.scene
    gd = scene.gd
    render = scene.render

    # TODO: Preserve use_local_camera & original camera

    # Active Camera
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                space.use_local_camera = False
                break

    scene.camera = bpy.data.objects.get(Global.TRIM_CAMERA_NAME)

        ## VIEW LAYER PROPERTIES ##

    # View layer
    self.savedViewLayerUse = context.view_layer.use
    self.savedUseSingleLayer = render.use_single_layer

    context.view_layer.use = True
    render.use_single_layer = True

    # World
    if scene.world:
        scene.world.use_nodes = False

    # Render Engine (Set per bake map)
    eevee = scene.eevee
    self.savedRenderer = render.engine

    # Sampling (Set per bake map)
    self.savedWorkbenchSampling = scene.display.render_aa
    self.savedWorkbenchVPSampling = scene.display.viewport_aa
    self.savedEeveeRenderSampling = eevee.taa_render_samples
    self.savedEeveeSampling = eevee.taa_samples
    self.savedCyclesSampling = context.scene.cycles.preview_samples
    self.savedCyclesRenderSampling = context.scene.cycles.samples

    # Bloom
    self.savedUseBloom = eevee.use_bloom
    eevee.use_bloom = False

    # Ambient Occlusion
    self.savedUseAO = eevee.use_gtao
    self.savedAODistance = eevee.gtao_distance
    self.savedAOQuality = eevee.gtao_quality
    eevee.use_gtao = False # Disable unless needed for AO bakes
    eevee.gtao_distance = .2
    eevee.gtao_quality = .5

    # Color Management
    view_settings = scene.view_settings

    self.savedDisplayDevice = scene.display_settings.display_device
    self.savedViewTransform = view_settings.view_transform
    self.savedContrastType = view_settings.look
    self.savedExposure = view_settings.exposure
    self.savedGamma = view_settings.gamma
    self.savedTransparency = render.film_transparent

    # Performance
    if bpy.app.version >= (2, 83, 0):
        self.savedHQNormals = render.use_high_quality_normals
        render.use_high_quality_normals = True

    # Film
    self.savedFilterSize = render.filter_size
    render.filter_size = gd.filter_width

    self.savedFilterSizeCycles = context.scene.cycles.filter_width
    self.savedFilterSizeTypeCycles = context.scene.cycles.pixel_filter_type
    context.scene.cycles.filter_width = render.filter_size
    context.scene.cycles.pixel_filter_type = 'BLACKMAN_HARRIS'

        ## OUTPUT PROPERTIES ##

    image_settings = render.image_settings

    # Dimensions (don't bother saving these)
    render.resolution_x = gd.export_res_x
    render.resolution_y = gd.export_res_y
    render.resolution_percentage = 100

    # Output
    self.savedColorMode = image_settings.color_mode
    self.savedFileFormat = image_settings.file_format

    # If background plane not visible in render, create alpha channel
    if not gd.coll_rendered:
        render.film_transparent = True

        image_settings.color_mode = 'RGBA'
    else:
        image_settings.color_mode = 'RGB'

    image_settings.file_format = gd.format

    if gd.format == 'OPEN_EXR':
        image_settings.color_depth = gd.exr_depth
    elif gd.format != 'TARGA':
        image_settings.color_depth = gd.depth

    if gd.format == "PNG":
        image_settings.compression = gd.png_compression

    self.savedColorDepth = image_settings.color_depth

    # Post Processing
    self.savedUseSequencer = render.use_sequencer
    self.savedUseCompositor = render.use_compositing
    self.savedDitherIntensity = render.dither_intensity

    render.use_sequencer = render.use_compositing = False
    render.dither_intensity = 0

        ## VIEWPORT SHADING ##

    scene_shading = bpy.data.scenes[str(scene.name)].display.shading

    self.savedLight = scene_shading.light
    self.savedColorType = scene_shading.color_type
    self.savedBackface = scene_shading.show_backface_culling
    self.savedXray = scene_shading.show_xray
    self.savedShadows = scene_shading.show_shadows
    self.savedCavity = scene_shading.show_cavity
    self.savedDOF = scene_shading.use_dof
    self.savedOutline = scene_shading.show_object_outline
    self.savedShowSpec = scene_shading.show_specular_highlight

    scene_shading.show_backface_culling = \
        scene_shading.show_xray = scene_shading.show_shadows = False
    scene_shading.show_cavity = \
        scene_shading.use_dof = scene_shading.show_object_outline = False
    scene_shading.show_specular_highlight = False

        ## PLANE REFERENCE ##

    self.savedRefSelection = gd.reference.name if gd.reference else None

        ## OBJECT VISIBILITY ##

    bg_plane = bpy.data.objects.get(Global.BG_PLANE_NAME)

    bg_plane.hide_viewport = not gd.coll_visible
    bg_plane.hide_render = not gd.coll_rendered
    bg_plane.hide_set(False)


def export_refresh(self, context: Context) -> None:
    scene = context.scene
    gd = scene.gd
    render = scene.render

        ## VIEW LAYER PROPERTIES ##

    # View layer
    context.view_layer.use = self.savedViewLayerUse
    scene.render.use_single_layer = self.savedUseSingleLayer

        ## WORLD PROPERTIES ##

    if scene.world:
        scene.world.use_nodes = True

        ## RENDER PROPERTIES ##

    # Render Engine
    render.engine = self.savedRenderer

    # Sampling
    scene.display.render_aa = self.savedWorkbenchSampling
    scene.display.viewport_aa = self.savedWorkbenchVPSampling
    scene.eevee.taa_render_samples = self.savedEeveeRenderSampling
    scene.eevee.taa_samples = self.savedEeveeSampling

    self.savedCyclesSampling = context.scene.cycles.preview_samples
    self.savedCyclesRenderSampling = context.scene.cycles.samples

    # Bloom
    scene.eevee.use_bloom = self.savedUseBloom

    # Color Management
    view_settings = scene.view_settings

    view_settings.look = self.savedContrastType
    scene.display_settings.display_device = self.savedDisplayDevice
    view_settings.view_transform = self.savedViewTransform
    view_settings.exposure = self.savedExposure
    view_settings.gamma = self.savedGamma

    scene.render.film_transparent = self.savedTransparency

    # Performance
    if bpy.app.version >= (2, 83, 0):
        render.use_high_quality_normals = self.savedHQNormals

    # Film
    render.filter_size = self.savedFilterSize

    context.scene.cycles.filter_width = self.savedFilterSizeCycles
    context.scene.cycles.pixel_filter_type = self.savedFilterSizeTypeCycles

        ## OUTPUT PROPERTIES ##

    # Output
    render.image_settings.color_depth = self.savedColorDepth
    render.image_settings.color_mode = self.savedColorMode
    render.image_settings.file_format = self.savedFileFormat

    # Post Processing
    render.use_sequencer = self.savedUseSequencer
    render.use_compositing = self.savedUseCompositor

    render.dither_intensity = self.savedDitherIntensity

        ## VIEWPORT SHADING ##

    scene_shading = bpy.data.scenes[str(scene.name)].display.shading

    # Refresh
    scene_shading.show_cavity = self.savedCavity
    scene_shading.color_type = self.savedColorType
    scene_shading.show_backface_culling = self.savedBackface
    scene_shading.show_xray = self.savedXray
    scene_shading.show_shadows = self.savedShadows
    scene_shading.use_dof = self.savedDOF
    scene_shading.show_object_outline = self.savedOutline
    scene_shading.show_specular_highlight = self.savedShowSpec
    scene_shading.light = self.savedLight

        ## PLANE REFERENCE ##

    if self.savedRefSelection:
        gd.reference = bpy.data.images[self.savedRefSelection]


# TODO: OK this is a stupid function
#
# Lets just create a grabdoc render result materials and assign matching texture names to each slot. Think of it like how Marmoset has a bake result shader. This will increase initial shader complexity but will avoid needing to make a material for every baked image
def reimport_as_material(suffix, map_names: list) -> None:
    """Reimport baked textures as a material for further use inside of Blender"""
    gd = bpy.context.scene.gd

    # Create material
    mat = bpy.data.materials.get(Global.REIMPORT_MAT_NAME)
    if mat is None:
        mat = bpy.data.materials.new(Global.REIMPORT_MAT_NAME)
    mat.use_nodes = True
    links = mat.node_tree.links

    # Create nodes
    bsdf = mat.node_tree.nodes['Principled BSDF']

    # Import images
    # TODO: Create function for getting enabled maps
    y_offset = 0
    for name in map_names:
        image_name = Global.GD_PREFIX + name
        if image_name in bpy.data.images:
            bpy.data.images.remove(bpy.data.images.get(image_name))

        image = mat.node_tree.nodes.get(image_name)
        if image is None:
            image = mat.node_tree.nodes.new('ShaderNodeTexImage')
            image.name = image_name
            image.location = (-300, y_offset)
        y_offset -= 200

        export_name = f'{gd.export_name}_{suffix}'
        export_path = os.path.join(
            bpy.path.abspath(gd.export_path), export_name + get_format()
        )
        if not os.path.exists(export_path):
            continue
        image.image = bpy.data.images.load(export_path)

        if name not in ("color"):
            image.image.colorspace_settings.name = 'Non-Color'

        # Link image to matching bsdf socket
        try:
            links.new(bsdf.inputs[name], image.outputs[name])
        except KeyError:
            pass


################################################
# INDIVIDUAL MATERIAL SETUP & CLEANUP
################################################


# NORMALS
def normals_setup(objects: Iterable[Object]) -> None:
    scene = bpy.context.scene
    #render = scene.render

    if scene.gd.normals[0].engine  == 'blender_eevee':
        scene.eevee.taa_render_samples = \
            scene.eevee.taa_samples = scene.gd.normals[0].samples
    else: # Cycles
        scene.cycles.samples = \
            scene.cycles.preview_samples = scene.gd.normals[0].samples_cycles

    #render.engine = str(scene.gd.normals[0].engine).upper()

    set_color_management('None')

    ng_normal = bpy.data.node_groups[Global.NORMAL_NG_NAME]
    vec_transform = ng_normal.nodes.get('Vector Transform')
    group_output = ng_normal.nodes.get('Group Output')

    links = ng_normal.links
    if scene.gd.normals[0].use_texture:
        links.new(
            vec_transform.inputs["Vector"],
            ng_normal.nodes.get('Bevel').outputs["Normal"]
        )
        links.new(
            group_output.inputs["Shader"],
            ng_normal.nodes.get('Mix Shader').outputs["Shader"]
        )
    else:
        links.new(
            vec_transform.inputs["Vector"],
            ng_normal.nodes.get('Bevel.001').outputs["Normal"]
        )
        links.new(
            group_output.inputs["Shader"],
            ng_normal.nodes.get('Vector Math.001').outputs["Vector"]
        )

    add_ng_to_mat(name=Global.NORMAL_NG_NAME, objects=objects)


def curvature_setup(self) -> None:
    scene = bpy.context.scene
    gd = scene.gd
    scene_shading = bpy.data.scenes[str(scene.name)].display.shading

    # Render engine settings
    #scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.render_aa = \
    scene.display.viewport_aa = \
        gd.curvature[0].samples_workbench
    scene_shading.light = 'FLAT'
    scene_shading.color_type =  'SINGLE'
    set_color_management('sRGB')

    try:
        scene.view_settings.look = \
            gd.curvature[0].contrast.replace('_', ' ')
    except TypeError:
        pass

    # Cavity
    self.savedCavityType = scene_shading.cavity_type
    self.savedCavityRidgeFactor = scene_shading.cavity_ridge_factor
    self.savedCurveRidgeFactor = scene_shading.curvature_ridge_factor
    self.savedCavityValleyFactor = scene_shading.cavity_valley_factor
    self.savedCurveValleyFactor = scene_shading.curvature_valley_factor
    self.savedRidgeDistance = scene.display.matcap_ssao_distance
    self.savedSingleColor = [*scene_shading.single_color]

    scene_shading.show_cavity = True
    scene_shading.cavity_type = 'BOTH'
    scene_shading.cavity_ridge_factor = \
        scene_shading.curvature_ridge_factor = gd.curvature[0].ridge
    scene_shading.curvature_valley_factor = gd.curvature[0].valley
    scene_shading.cavity_valley_factor = 0
    scene_shading.single_color = (.214041, .214041, .214041)

    scene.display.matcap_ssao_distance = .075


def curvature_refresh(self) -> None:
    display = \
        bpy.data.scenes[str(bpy.context.scene.name)].display
    display.shading.cavity_ridge_factor = self.savedCavityRidgeFactor
    display.shading.curvature_ridge_factor = self.savedCurveRidgeFactor
    display.shading.cavity_valley_factor = self.savedCavityValleyFactor
    display.shading.curvature_valley_factor = self.savedCurveValleyFactor
    display.shading.single_color =  self.savedSingleColor
    display.shading.cavity_type = self.savedCavityType
    display.shading.show_cavity = self.savedCavity
    display.matcap_ssao_distance = self.savedRidgeDistance

    bpy.data.objects[Global.BG_PLANE_NAME].color[3] = 1


def occlusion_setup(self, objects: Iterable[Object]) -> None:
    scene = bpy.context.scene
    gd = scene.gd

    eevee = scene.eevee
    self.savedUseOverscan = eevee.use_overscan
    self.savedOverscanSize = eevee.overscan_size
    if scene.render.engine == "BLENDER_EEVEE":
        eevee.taa_render_samples = \
        eevee.taa_samples = gd.occlusion[0].samples
        eevee.use_gtao = True
        # NOTE: Overscan helps with screenspace effects
        eevee.use_overscan = True
        eevee.overscan_size = 10

    set_color_management('None')
    try:
        scene.view_settings.look = \
            gd.occlusion[0].contrast.replace('_', ' ')
    except TypeError:
        pass

    add_ng_to_mat(name=Global.AO_NG_NAME, objects=objects)


def occlusion_refresh(self) -> None:
    eevee = bpy.context.scene.eevee
    eevee.use_overscan = self.savedUseOverscan
    eevee.overscan_size = self.savedOverscanSize
    eevee.use_gtao = self.savedUseAO
    eevee.gtao_distance = self.savedAODistance
    eevee.gtao_quality = self.savedAOQuality


def height_setup(objects: Iterable[Object]) -> None:
    scene = bpy.context.scene
    gd = scene.gd

    if scene.render.engine == 'BLENDER_EEVEE':
        scene.eevee.taa_render_samples = \
        scene.eevee.taa_samples = gd.height[0].samples

    set_color_management('None')
    try:
        scene.view_settings.look = gd.height[0].contrast.replace('_', ' ')
    except TypeError:
        pass

    add_ng_to_mat(name=Global.HEIGHT_NG_NAME, objects=objects)

    if gd.height[0].method == 'AUTO':
        rendered_obs = get_rendered_objects()
        set_guide_height(rendered_obs)


def id_setup() -> None:
    scene = bpy.context.scene
    if scene.render.engine == 'BLENDER_WORKBENCH':
        display = scene.display
        display.render_aa = \
        display.viewport_aa = scene.gd.id[0].samples_workbench
        display.shading.light = 'FLAT'
        display.shading.color_type = scene.gd.id[0].method

    set_color_management('sRGB')


def alpha_setup(objects: Iterable[Object]) -> None:
    scene = bpy.context.scene

    if scene.render.engine == 'BLENDER_EEVEE':
        scene.eevee.taa_render_samples = \
            scene.eevee.taa_samples = scene.gd.alpha[0].samples

    set_color_management('None')

    add_ng_to_mat(name=Global.ALPHA_NG_NAME, objects=objects)


def color_setup(objects: Iterable[Object]) -> None:
    scene = bpy.context.scene
    if scene.gd.color[0].engine  == 'blender_eevee':
        scene.eevee.taa_render_samples = \
        scene.eevee.taa_samples = scene.gd.color[0].samples
    else: # Cycles
        scene.cycles.samples = \
        scene.cycles.preview_samples = scene.gd.color[0].samples_cycles

    set_color_management('sRGB')

    add_ng_to_mat(name=Global.COLOR_NG_NAME, objects=objects)


# ROUGHNESS
def roughness_setup(objects: Iterable[Object]) -> None:
    scene = bpy.context.scene
    render = scene.render

    if scene.gd.roughness[0].engine == 'blender_eevee':
        scene.eevee.taa_render_samples = \
            scene.eevee.taa_samples = scene.gd.roughness[0].samples
    else: # Cycles
        scene.cycles.samples = \
            scene.cycles.preview_samples = scene.gd.roughness[0].samples_cycles

    set_color_management('sRGB')

    add_ng_to_mat(name=Global.ROUGHNESS_NG_NAME, objects=objects)


# METALNESS
def metalness_setup(objects: Iterable[Object]) -> None:
    scene = bpy.context.scene
    #render = scene.render

    if scene.gd.metalness[0].engine == 'blender_eevee':
        scene.eevee.taa_render_samples = \
            scene.eevee.taa_samples = scene.gd.metalness[0].samples
    else: # Cycles
        scene.cycles.samples = \
            scene.cycles.preview_samples = scene.gd.metalness[0].samples

    set_color_management('sRGB')

    add_ng_to_mat(name=Global.METALNESS_NG_NAME, objects=objects)
