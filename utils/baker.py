
import os

import bpy
from bpy.types import Context

from ..constants import GlobalVariableConstants as Global
from .node import add_ng_to_mat
from .generic import get_format_extension
from .render import set_guide_height


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


def export_and_preview_setup(self, context: Context):
    scene = context.scene
    gd = scene.grabDoc
    render = scene.render

    # TODO: Preserve use_local_camera & original camera

    # Set - Active Camera
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                space.use_local_camera = False
                break

    scene.camera = bpy.data.objects.get(Global.TRIM_CAMERA_NAME)

        ## VIEW LAYER PROPERTIES ##

    # Save & Set - View layer
    self.savedViewLayerUse = context.view_layer.use
    self.savedUseSingleLayer = render.use_single_layer

    context.view_layer.use = True
    render.use_single_layer = True

        ## WORLD PROPERTIES ##

    if scene.world:
        scene.world.use_nodes = False

        ## RENDER PROPERTIES ##

    eevee = scene.eevee

    # Save - Render Engine (Set per bake map)
    self.savedRenderer = render.engine

    # Save - Sampling (Set per bake map)
    self.savedWorkbenchSampling = scene.display.render_aa
    self.savedWorkbenchVPSampling = scene.display.viewport_aa
    self.savedEeveeRenderSampling = eevee.taa_render_samples
    self.savedEeveeSampling = eevee.taa_samples

    self.savedCyclesSampling = context.scene.cycles.preview_samples
    self.savedCyclesRenderSampling = context.scene.cycles.samples

    # Save & Set - Bloom
    self.savedUseBloom = eevee.use_bloom

    eevee.use_bloom = False

    # Save & Set - Ambient Occlusion
    self.savedUseAO = eevee.use_gtao
    self.savedAODistance = eevee.gtao_distance
    self.savedAOQuality = eevee.gtao_quality

    eevee.use_gtao = False # Disable unless needed for AO bakes
    eevee.gtao_distance = .2
    eevee.gtao_quality = .5

    # Save & Set - Color Management
    view_settings = scene.view_settings

    self.savedDisplayDevice = scene.display_settings.display_device
    self.savedViewTransform = view_settings.view_transform
    self.savedContrastType = view_settings.look
    self.savedExposure = view_settings.exposure
    self.savedGamma = view_settings.gamma
    self.savedTransparency = render.film_transparent

    set_color_management('sRGB')

    # Save & Set - Performance
    if bpy.app.version >= (2, 83, 0):
        self.savedHQNormals = render.use_high_quality_normals
        render.use_high_quality_normals = True

    # Save & Set - Film
    self.savedFilterSize = render.filter_size
    render.filter_size = gd.widthFiltering

    self.savedFilterSizeCycles = context.scene.cycles.filter_width
    self.savedFilterSizeTypeCycles = context.scene.cycles.pixel_filter_type
    context.scene.cycles.filter_width = render.filter_size
    context.scene.cycles.pixel_filter_type = 'BLACKMAN_HARRIS'

        ## OUTPUT PROPERTIES ##

    image_settings = render.image_settings

    # Set - Dimensions (Don't bother saving these)
    render.resolution_x = gd.exportResX
    render.resolution_y = gd.exportResY
    render.resolution_percentage = 100

    # Save & Set - Output
    self.savedColorMode = image_settings.color_mode
    self.savedFileFormat = image_settings.file_format

    # If background plane not visible in render, create alpha channel
    if not gd.collRendered:
        render.film_transparent = True

        image_settings.color_mode = 'RGBA'
    else:
        image_settings.color_mode = 'RGB'

    image_settings.file_format = gd.imageType

    if gd.imageType == 'OPEN_EXR':
        image_settings.color_depth = gd.colorDepthEXR
    elif gd.imageType != 'TARGA':
        image_settings.color_depth = gd.colorDepth

    if gd.imageType == "PNG":
        image_settings.compression = gd.imageCompPNG

    self.savedColorDepth = image_settings.color_depth

    # Save & Set - Post Processing
    self.savedUseSequencer = render.use_sequencer
    self.savedUseCompositor = render.use_compositing
    self.savedDitherIntensity = render.dither_intensity

    render.use_sequencer = render.use_compositing = False
    render.dither_intensity = 0

        ## VIEWPORT SHADING ##

    scene_shading = bpy.data.scenes[str(scene.name)].display.shading

    # Save & Set
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

    self.savedRefSelection = gd.refSelection.name if gd.refSelection else None

        ## OBJECT VISIBILITY ##

    bg_plane = bpy.data.objects.get(Global.BG_PLANE_NAME)

    bg_plane.hide_viewport = not gd.collVisible
    bg_plane.hide_render = not gd.collRendered
    bg_plane.hide_set(False)


def export_refresh(self, context: Context) -> None:
    scene = context.scene
    gd = scene.grabDoc
    render = scene.render

        ## VIEW LAYER PROPERTIES ##

    # Refresh - View layer
    context.view_layer.use = self.savedViewLayerUse
    scene.render.use_single_layer = self.savedUseSingleLayer

        ## WORLD PROPERTIES ##

    if scene.world:
        scene.world.use_nodes = True

        ## RENDER PROPERTIES ##

    # Refresh - Render Engine
    render.engine = self.savedRenderer

    # Refresh - Sampling
    scene.display.render_aa = self.savedWorkbenchSampling
    scene.display.viewport_aa = self.savedWorkbenchVPSampling
    scene.eevee.taa_render_samples = self.savedEeveeRenderSampling
    scene.eevee.taa_samples = self.savedEeveeSampling

    self.savedCyclesSampling = context.scene.cycles.preview_samples
    self.savedCyclesRenderSampling = context.scene.cycles.samples

    # Refresh - Bloom
    scene.eevee.use_bloom = self.savedUseBloom

    # Refresh - Color Management
    view_settings = scene.view_settings

    view_settings.look = self.savedContrastType
    scene.display_settings.display_device = self.savedDisplayDevice
    view_settings.view_transform = self.savedViewTransform
    view_settings.exposure = self.savedExposure
    view_settings.gamma = self.savedGamma

    scene.render.film_transparent = self.savedTransparency

    # Refresh - Performance
    if bpy.app.version >= (2, 83, 0):
        render.use_high_quality_normals = self.savedHQNormals

    # Refresh - Film
    render.filter_size = self.savedFilterSize

    context.scene.cycles.filter_width = self.savedFilterSizeCycles
    context.scene.cycles.pixel_filter_type = self.savedFilterSizeTypeCycles

        ## OUTPUT PROPERTIES ##

    # Refresh - Output
    render.image_settings.color_depth = self.savedColorDepth
    render.image_settings.color_mode = self.savedColorMode
    render.image_settings.file_format = self.savedFileFormat

    # Refresh - Post Processing
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
        gd.refSelection = bpy.data.images[self.savedRefSelection]


def reimport_as_material(suffix) -> None:
    """Reimport an exported map as a material for further use inside of Blender"""
    gd = bpy.context.scene.grabDoc

    mat_name = f'{gd.exportName}_{suffix}'

    # TODO: don't remove the material and start
    # from scratch, but replace/update the image?

    # Remove pre-existing material
    if mat_name in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials.get(mat_name))

    # Remove original image
    if mat_name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images.get(mat_name))

    # Create material
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True

    output = mat.node_tree.nodes["Material Output"]
    output.location = (0,0)

    mat.node_tree.nodes.remove(mat.node_tree.nodes.get('Principled BSDF'))

    file_extension = get_format_extension()

    image = mat.node_tree.nodes.new('ShaderNodeTexImage')
    image.image = bpy.data.images.load(
        os.path.join(bpy.path.abspath(gd.exportPath),mat_name + file_extension)
    )
    image.name = mat_name
    image.location = (-300,0)

    # Context specific image settings (currently only uses Non-Color)
    image.image.colorspace_settings.name = 'Non-Color'

    # Make links
    mat.node_tree.links.new(output.inputs['Surface'], image.outputs['Color'])


################################################
# INDIVIDUAL MATERIAL SETUP & CLEANUP
################################################


# NORMALS
def normals_setup(self, context: Context) -> None:
    scene = context.scene
    render = scene.render

    if scene.grabDoc.engineNormals  == 'blender_eevee':
        scene.eevee.taa_render_samples = \
            scene.eevee.taa_samples = scene.grabDoc.samplesNormals
    else: # Cycles
        scene.cycles.samples = \
            scene.cycles.preview_samples = scene.grabDoc.samplesCyclesNormals

    render.engine = str(scene.grabDoc.engineNormals).upper()

    set_color_management('None')

    ng_normal = bpy.data.node_groups[Global.NG_NORMAL_NAME]
    vec_transform = ng_normal.nodes.get('Vector Transform')
    group_output = ng_normal.nodes.get('Group Output')

    links = ng_normal.links
    if context.scene.grabDoc.useTextureNormals:
        links.new(
            vec_transform.inputs["Vector"],
            ng_normal.nodes.get('Bevel').outputs["Normal"]
        )
        links.new(
            group_output.inputs["Output"],
            ng_normal.nodes.get('Mix Shader').outputs["Shader"]
        )
    else:
        links.new(
            vec_transform.inputs["Vector"],
            ng_normal.nodes.get('Bevel.001').outputs["Normal"]
        )
        links.new(
            group_output.inputs["Output"],
            ng_normal.nodes.get('Vector Math.001').outputs["Vector"]
        )

    add_ng_to_mat(self, context, setup_type=Global.NG_NORMAL_NAME)


# CURVATURE
def curvature_setup(self, context: Context) -> None:
    scene = context.scene
    gd = scene.grabDoc
    scene_shading = bpy.data.scenes[str(scene.name)].display.shading

    # Set - Render engine settings
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.render_aa = scene.display.viewport_aa = gd.samplesCurvature
    scene_shading.light = 'FLAT'
    scene_shading.color_type =  'SINGLE'
    set_color_management('sRGB')

    try:
        scene.view_settings.look = gd.contrastCurvature.replace('_', ' ')
    except TypeError:
        pass

    # Save & Set - Cavity
    self.savedCavityType = scene_shading.cavity_type
    self.savedCavityRidgeFactor = scene_shading.cavity_ridge_factor
    self.savedCurveRidgeFactor = scene_shading.curvature_ridge_factor
    self.savedCavityValleyFactor = scene_shading.cavity_valley_factor
    self.savedCurveValleyFactor = scene_shading.curvature_valley_factor
    self.savedRidgeDistance = scene.display.matcap_ssao_distance

    self.savedSingleList = [*scene_shading.single_color] # Unpack RGB values

    scene_shading.show_cavity = True
    scene_shading.cavity_type = 'BOTH'
    scene_shading.cavity_ridge_factor = \
        scene_shading.curvature_ridge_factor = gd.ridgeCurvature
    scene_shading.curvature_valley_factor = gd.valleyCurvature
    scene_shading.cavity_valley_factor = 0
    scene_shading.single_color = (.214041, .214041, .214041)

    scene.display.matcap_ssao_distance = .075


def curvature_refresh(self, context: Context) -> None:
    scene_shading = bpy.data.scenes[str(context.scene.name)].display.shading

    scene_shading.cavity_ridge_factor = self.savedCavityRidgeFactor
    scene_shading.curvature_ridge_factor = self.savedCurveRidgeFactor
    scene_shading.cavity_valley_factor = self.savedCavityValleyFactor
    scene_shading.curvature_valley_factor = self.savedCurveValleyFactor
    scene_shading.single_color =  self.savedSingleList
    scene_shading.cavity_type = self.savedCavityType
    scene_shading.show_cavity = self.savedCavity

    context.scene.display.matcap_ssao_distance = self.savedRidgeDistance

    bpy.data.objects[Global.BG_PLANE_NAME].color[3] = 1


# AMBIENT OCCLUSION
def occlusion_setup(self, context: Context) -> None:
    scene = context.scene
    gd = scene.grabDoc
    eevee = scene.eevee

    scene.render.engine = 'BLENDER_EEVEE'
    eevee.taa_render_samples = eevee.taa_samples = gd.samplesOcclusion
    set_color_management('None')

    try:
        scene.view_settings.look = gd.contrastOcclusion.replace('_', ' ')
    except TypeError:
        pass

    # Save & Set - Overscan (Can help with screenspace effects)
    self.savedUseOverscan = eevee.use_overscan
    self.savedOverscanSize = eevee.overscan_size

    eevee.use_overscan = True
    eevee.overscan_size = 10

    # Set - Ambient Occlusion
    eevee.use_gtao = True

    add_ng_to_mat(self, context, setup_type=Global.NG_AO_NAME)


def occlusion_refresh(self, context: Context) -> None:
    eevee = context.scene.eevee

    eevee.use_overscan = self.savedUseOverscan
    eevee.overscan_size = self.savedOverscanSize

    eevee.use_gtao = self.savedUseAO
    eevee.gtao_distance = self.savedAODistance
    eevee.gtao_quality = self.savedAOQuality


# HEIGHT
def height_setup(self, context: Context) -> None:
    scene = context.scene
    gd = scene.grabDoc

    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = scene.eevee.taa_samples = gd.samplesHeight
    set_color_management('None')

    try:
        scene.view_settings.look = gd.contrastHeight.replace('_', ' ')
    except TypeError:
        pass

    add_ng_to_mat(self, context, setup_type=Global.NG_HEIGHT_NAME)

    if gd.rangeTypeHeight == 'AUTO':
        set_guide_height()


# MATERIAL ID
def id_setup(_self, context: Context) -> None:
    scene = context.scene
    gd = scene.grabDoc
    render = scene.render
    scene_shading = bpy.data.scenes[str(scene.name)].display.shading

    render.engine = 'BLENDER_WORKBENCH'
    scene.display.render_aa = scene.display.viewport_aa = gd.samplesMatID
    scene_shading.light = 'FLAT'
    set_color_management('sRGB')

    # Choose the method of ID creation based on user preference
    scene_shading.color_type = gd.methodMatID


# ALPHA
def alpha_setup(self, context: Context) -> None:
    scene = context.scene
    render = scene.render

    render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = \
        scene.eevee.taa_samples = scene.grabDoc.samplesAlpha
    set_color_management('None')

    add_ng_to_mat(self, context, setup_type=Global.NG_ALPHA_NAME)


# ALBEDO
def albedo_setup(self, context: Context) -> None:
    scene = context.scene
    render = scene.render

    if scene.grabDoc.engineAlbedo  == 'blender_eevee':
        scene.eevee.taa_render_samples = \
            scene.eevee.taa_samples = scene.grabDoc.samplesAlbedo
    else: # Cycles
        scene.cycles.samples = \
            scene.cycles.preview_samples = scene.grabDoc.samplesCyclesAlbedo

    render.engine = str(scene.grabDoc.engineAlbedo).upper()

    set_color_management('sRGB')

    add_ng_to_mat(self, context, setup_type=Global.NG_ALBEDO_NAME)


# ROUGHNESS
def roughness_setup(self, context: Context) -> None:
    scene = context.scene
    render = scene.render

    if scene.grabDoc.engineRoughness == 'blender_eevee':
        scene.eevee.taa_render_samples = \
            scene.eevee.taa_samples = scene.grabDoc.samplesRoughness
    else: # Cycles
        scene.cycles.samples = \
            scene.cycles.preview_samples = scene.grabDoc.samplesCyclesRoughness

    render.engine = str(scene.grabDoc.engineRoughness).upper()

    set_color_management('sRGB')

    add_ng_to_mat(self, context, setup_type=Global.NG_ROUGHNESS_NAME)


# METALNESS
def metalness_setup(self, context: Context) -> None:
    scene = context.scene
    render = scene.render

    if scene.grabDoc.engineMetalness == 'blender_eevee':
        scene.eevee.taa_render_samples = \
            scene.eevee.taa_samples = scene.grabDoc.samplesMetalness
    else: # Cycles
        scene.cycles.samples = \
            scene.cycles.preview_samples = scene.grabDoc.samplesMetalness

    render.engine = str(scene.grabDoc.engineMetalness).upper()

    set_color_management('sRGB')

    add_ng_to_mat(self, context, setup_type=Global.NG_METALNESS_NAME)


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
