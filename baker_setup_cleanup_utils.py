
import bpy, os
from .node_group_utils import add_ng_to_mat
from .render_setup_utils import find_tallest_object
from .generic_utils import get_format_extension


################################################################################################################
# BAKER SETUP & CLEANUP
################################################################################################################


def export_and_preview_setup(self, context):
    grabDoc = context.scene.grabDoc
    render = context.scene.render

    # TODO Preserve use_local_camera & original camera

    # Set - Active Camera
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                space.use_local_camera = False
                break

    context.scene.camera = bpy.data.objects.get("GD_Trim Camera")

        ## VIEW LAYER PROPERTIES ##

    # Save & Set - View layer
    self.savedViewLayerUse = context.view_layer.use
    self.savedUseSingleLayer = render.use_single_layer

    context.view_layer.use = True
    render.use_single_layer = True

        ## WORLD PROPERTIES ##

    context.scene.world.use_nodes = False

        ## RENDER PROPERTIES ##

    eevee = context.scene.eevee

    # Save - Render Engine (Set per bake map)
    self.savedRenderer = render.engine

    # Save - Sampling (Set per bake map)
    self.savedWorkbenchSampling = context.scene.display.render_aa
    self.savedWorkbenchVPSampling = context.scene.display.viewport_aa
    self.savedEeveeRenderSampling = eevee.taa_render_samples
    self.savedEeveeSampling = eevee.taa_samples

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
    view_settings = context.scene.view_settings

    self.savedDisplayDevice = context.scene.display_settings.display_device
    self.savedViewTransform = view_settings.view_transform
    self.savedContrastType = view_settings.look
    self.savedExposure = view_settings.exposure
    self.savedGamma = view_settings.gamma 
    self.savedTransparency = render.film_transparent

    view_settings.view_transform = 'Standard'
    view_settings.look = 'None'
    view_settings.exposure = 0
    view_settings.gamma = 1

    # Save & Set - Performance 
    if bpy.app.version >= (2, 83, 0):
        self.savedHQNormals = render.use_high_quality_normals
        render.use_high_quality_normals = True

        ## OUTPUT PROPERTIES ##

    image_settings = render.image_settings

    # Set - Dimensions (Don't bother saving these)
    render.resolution_x = grabDoc.exportResX
    render.resolution_y = grabDoc.exportResY
    render.resolution_percentage = 100

    # Save & Set - Output
    self.savedColorMode = image_settings.color_mode
    self.savedFileFormat = image_settings.file_format

    if not grabDoc.collRendered: # If background plane not visible in render, create alpha channel
        render.film_transparent = True
        
        image_settings.color_mode = 'RGBA'
    else:
        image_settings.color_mode = 'RGB'

    image_settings.file_format = grabDoc.imageType

    if grabDoc.imageType == 'OPEN_EXR':
        image_settings.color_depth = grabDoc.colorDepthEXR
    elif grabDoc.imageType != 'TARGA':
        image_settings.color_depth = grabDoc.colorDepth

    if grabDoc.imageType == "PNG":
        image_settings.compression = grabDoc.imageCompPNG
    
    self.savedColorDepth = image_settings.color_depth

    # Save & Set - Post Processing
    self.savedUseSequencer = render.use_sequencer
    self.savedUseCompositer = render.use_compositing
    self.savedDitherIntensity = render.dither_intensity

    render.use_sequencer = render.use_compositing = False
    render.dither_intensity = 0

        ## VIEWPORT SHADING ##

    scene_shading = bpy.data.scenes[str(context.scene.name)].display.shading

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

    scene_shading.show_backface_culling = scene_shading.show_xray = scene_shading.show_shadows = False
    scene_shading.show_cavity = scene_shading.use_dof = scene_shading.show_object_outline = False
    scene_shading.show_specular_highlight = False

        ## PLANE REFERENCE ##

    self.savedRefSelection = grabDoc.refSelection.name if grabDoc.refSelection else None
    
        ## OBJECT VISIBILITY ##

    bg_plane = bpy.data.objects.get("GD_Background Plane")
   
    bg_plane.hide_viewport = not grabDoc.collVisible
    bg_plane.hide_render = not grabDoc.collRendered
    bg_plane.hide_set(False)

    self.ob_hidden_render_list = []
    self.ob_hidden_vp_list = []
    
    # Save & Set - Non-rendered objects visibility (self.render_list defined in bad_setup_check)
    for ob in context.view_layer.objects:
        if ob.type in {'MESH', 'CURVE'} and not ob.name in self.render_list:
            if not ob.hide_render:
                self.ob_hidden_render_list.append(ob.name)
            ob.hide_render = True

            if not ob.hide_viewport:
                self.ob_hidden_vp_list.append(ob.name)
            ob.hide_viewport = True


def export_refresh(self, context) -> None:
    scene = context.scene
    grabDoc = scene.grabDoc
    render = scene.render

        ## VIEW LAYER PROPERTIES ##

    # Refresh - View layer
    context.view_layer.use = self.savedViewLayerUse
    scene.render.use_single_layer = self.savedUseSingleLayer

        ## WORLD PROPERTIES ##

    scene.world.use_nodes = True

        ## RENDER PROPERTIES ##

    # Refresh - Render Engine
    render.engine = self.savedRenderer

    # Refresh - Sampling
    scene.display.render_aa = self.savedWorkbenchSampling
    scene.display.viewport_aa = self.savedWorkbenchVPSampling
    scene.eevee.taa_render_samples = self.savedEeveeRenderSampling
    scene.eevee.taa_samples = self.savedEeveeSampling

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

        ## OUTPUT PROPERTIES ##

    # Refresh - Output
    render.image_settings.color_depth = self.savedColorDepth
    render.image_settings.color_mode = self.savedColorMode
    render.image_settings.file_format = self.savedFileFormat

    # Refresh - Post Processing
    render.use_sequencer = self.savedUseSequencer
    render.use_compositing = self.savedUseCompositer

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
        grabDoc.refSelection = bpy.data.images[self.savedRefSelection]

        ## OBJECT VISIBILITY ##

    # Refresh - Non-rendered objects visibility
    for ob in context.view_layer.objects:
        # Unhide in render
        if ob.name in self.ob_hidden_render_list:
            ob.hide_render = False
        
        # Unhide in viewport
        if ob.name in self.ob_hidden_vp_list:
            ob.hide_viewport = False


def reimport_as_material(suffix) -> None:
    '''Reimport an exported map as a material for further use inside of Blender'''
    grabDoc = bpy.context.scene.grabDoc

    mat_name = f'{grabDoc.exportName}_{suffix}'

    # TODO don't remove the material and start from scratch, but replace/update the image?

    # Remove pre-existing material
    if mat_name in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials.get(mat_name))

    # Remove original image
    if mat_name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images.get(mat_name))

    # Create material
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True

    output_node = mat.node_tree.nodes["Material Output"]
    output_node.location = (0,0)

    mat.node_tree.nodes.remove(mat.node_tree.nodes.get('Principled BSDF'))

    file_extension = get_format_extension()

    image_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    image_node.image = bpy.data.images.load(os.path.join(bpy.path.abspath(grabDoc.exportPath), mat_name + file_extension))
    image_node.name = mat_name
    image_node.location = (-300,0)

    # Context specific image settings (currently only uses Non-Color)
    image_node.image.colorspace_settings.name = 'Non-Color'

    # Make links
    mat.node_tree.links.new(output_node.inputs['Surface'], image_node.outputs['Color'])


################################################################################################################
# INDIVIDUAL MATERIAL SETUP & CLEANUP
################################################################################################################


# NORMALS
def normals_setup(self, context) -> None:
    scene = context.scene
    render = scene.render

    render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = scene.eevee.taa_samples = scene.grabDoc.samplesNormals
    scene.display_settings.display_device = 'None'

    ng_normal = bpy.data.node_groups["GD_Normal"]
    vec_transform_node = ng_normal.nodes.get('Vector Transform')
    group_output_node = ng_normal.nodes.get('Group Output')

    link = ng_normal.links

    if context.scene.grabDoc.useTextureNormals:
        link.new(vec_transform_node.inputs["Vector"], ng_normal.nodes.get('Bevel').outputs["Normal"])
        link.new(group_output_node.inputs["Output"], ng_normal.nodes.get('Mix Shader').outputs["Shader"])
    else:
        link.new(vec_transform_node.inputs["Vector"], ng_normal.nodes.get('Bevel.001').outputs["Normal"])
        link.new(group_output_node.inputs["Output"], ng_normal.nodes.get('Vector Math.001').outputs["Vector"])

    add_ng_to_mat(self, context, setup_type='GD_Normal')


# CURVATURE
def curvature_setup(self, context) -> None:
    scene = context.scene
    grabDoc = scene.grabDoc
    scene_shading = bpy.data.scenes[str(scene.name)].display.shading
    
    # Set - Render engine settings
    scene.view_settings.look = grabDoc.contrastCurvature.replace('_', ' ')

    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.render_aa = scene.display.viewport_aa = grabDoc.samplesCurvature
    scene_shading.light = 'FLAT'
    scene_shading.color_type =  'SINGLE'
    scene.display_settings.display_device = 'sRGB'

    # Save & Set - Cavity
    self.savedCavityType = scene_shading.cavity_type
    self.savedCavityRidgeFactor = scene_shading.cavity_ridge_factor
    self.savedCurveRidgeFactor = scene_shading.curvature_ridge_factor
    self.savedCavityValleyFactor = scene_shading.cavity_valley_factor
    self.savedCurveValleyFactor = scene_shading.curvature_valley_factor
    self.savedRidgeDistance = scene.display.matcap_ssao_distance

    self.savedSingleList = [] # List for single_color because saving the variable on its own isn't enough for whatever reason

    for i in scene_shading.single_color:
        self.savedSingleList.append(i)
    
    scene_shading.show_cavity = True
    scene_shading.cavity_type = 'BOTH'
    scene_shading.cavity_ridge_factor = scene_shading.curvature_ridge_factor = grabDoc.ridgeCurvature
    scene_shading.curvature_valley_factor = grabDoc.valleyCurvature
    scene_shading.cavity_valley_factor = 0
    scene_shading.single_color = (.214041, .214041, .214041)

    scene.display.matcap_ssao_distance = .075


def curvature_refresh(self, context) -> None:
    scene_shading = bpy.data.scenes[str(context.scene.name)].display.shading

    scene_shading.cavity_ridge_factor = self.savedCavityRidgeFactor
    scene_shading.curvature_ridge_factor = self.savedCurveRidgeFactor
    scene_shading.cavity_valley_factor = self.savedCavityValleyFactor
    scene_shading.curvature_valley_factor = self.savedCurveValleyFactor
    scene_shading.single_color =  self.savedSingleList
    scene_shading.cavity_type = self.savedCavityType
    scene_shading.show_cavity = self.savedCavity

    context.scene.display.matcap_ssao_distance = self.savedRidgeDistance
    
    bpy.data.objects["GD_Background Plane"].color[3] = 1


# AMBIENT OCCLUSION
def occlusion_setup(self, context) -> None:
    scene = context.scene
    grabDoc = scene.grabDoc
    eevee = scene.eevee
    
    scene.render.engine = 'BLENDER_EEVEE'
    eevee.taa_render_samples = eevee.taa_samples = grabDoc.samplesOcclusion
    scene.display_settings.display_device = 'None'

    # Save & Set - Overscan (Can help with screenspace effects)
    self.savedUseOverscan = eevee.use_overscan
    self.savedOverscanSize = eevee.overscan_size

    eevee.use_overscan = True
    eevee.overscan_size = 10

    # Set - Ambient Occlusion
    eevee.use_gtao = True

    scene.view_settings.look = grabDoc.contrastOcclusion.replace('_', ' ')

    add_ng_to_mat(self, context, setup_type='GD_Ambient Occlusion')


def occlusion_refresh(self, context) -> None:
    eevee = context.scene.eevee

    eevee.use_overscan = self.savedUseOverscan
    eevee.overscan_size = self.savedOverscanSize

    eevee.use_gtao = self.savedUseAO
    eevee.gtao_distance = self.savedAODistance
    eevee.gtao_quality = self.savedAOQuality


# HEIGHT
def height_setup(self, context) -> None:
    scene = context.scene
    grabDoc = scene.grabDoc

    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = scene.eevee.taa_samples = grabDoc.samplesHeight
    scene.display_settings.display_device = 'None'

    scene.view_settings.look = grabDoc.contrastHeight.replace('_', ' ')

    add_ng_to_mat(self, context, setup_type='GD_Height')

    if grabDoc.rangeTypeHeight == 'AUTO':
        find_tallest_object(self, context)


# MATERIAL ID
def id_setup(self, context) -> None:
    scene = context.scene
    grabDoc = scene.grabDoc
    render = scene.render
    scene_shading = bpy.data.scenes[str(scene.name)].display.shading

    render.engine = 'BLENDER_WORKBENCH'
    scene.display.render_aa = scene.display.viewport_aa = grabDoc.samplesMatID
    scene_shading.light = 'FLAT'
    scene.display_settings.display_device = 'sRGB'

    # Choose the method of ID creation based on user preference
    scene_shading.color_type = grabDoc.methodMatID


# ALPHA
def alpha_setup(self, context) -> None:
    scene = context.scene
    render = scene.render

    render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = scene.eevee.taa_samples = scene.grabDoc.samplesAlpha
    scene.display_settings.display_device = 'None'

    add_ng_to_mat(self, context, setup_type='GD_Alpha')


# ALBEDO
def albedo_setup(self, context) -> None:
    scene = context.scene
    render = scene.render

    render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = scene.eevee.taa_samples = scene.grabDoc.samplesAlbedo
    scene.display_settings.display_device = 'sRGB'

    add_ng_to_mat(self, context, setup_type='GD_Albedo')


# ROUGHNESS
def roughness_setup(self, context) -> None:
    scene = context.scene
    render = scene.render

    render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = scene.eevee.taa_samples = scene.grabDoc.samplesRoughness
    scene.display_settings.display_device = 'sRGB'

    add_ng_to_mat(self, context, setup_type='GD_Roughness')


# METALNESS
def metalness_setup(self, context) -> None:
    scene = context.scene
    render = scene.render

    render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = scene.eevee.taa_samples = scene.grabDoc.samplesMetalness
    scene.display_settings.display_device = 'sRGB'

    add_ng_to_mat(self, context, setup_type='GD_Metalness')


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
