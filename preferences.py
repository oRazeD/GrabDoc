import bpy, os
from bpy.props import BoolProperty, PointerProperty, StringProperty, EnumProperty, IntProperty, FloatProperty
from bl_operators.presets import AddPresetBase
from bl_ui.utils import PresetPanel
from bpy.types import Panel, Menu
from .operators import scene_setup_and_refresh, find_tallest_object
from .render_setup_utils import get_rendered_objects
from .addon_updater import Updater as updater
from .__init__ import bl_info


################################################################################################################
# PRESETS
################################################################################################################


class GRABDOC_MT_presets(Menu):
    bl_label = ""
    preset_subdir = "grabDoc"
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


class GRABDOC_PT_presets(PresetPanel, Panel):
    bl_label = 'GrabDoc Presets'
    preset_subdir = 'grab_doc'
    preset_operator = 'script.execute_preset'
    preset_add_operator = 'grab_doc.preset_add'


class GRABDOC_OT_add_preset(AddPresetBase, bpy.types.Operator):
    bl_idname = "grab_doc.preset_add"
    bl_label = "Add a new preset"
    preset_menu = "GRABDOC_MT_presets"

    # Variable used for all preset values
    preset_defines = ["grabDoc=bpy.context.scene.grabDoc"]

    # Properties to store in the preset
    preset_values = [
        "grabDoc.collSelectable",
        "grabDoc.collVisible",
        "grabDoc.collRendered",
        "grabDoc.useGrid",
        "grabDoc.gridSubdivisions",
        "grabDoc.scalingSet",

        "grabDoc.bakerType",
        "grabDoc.exportPath",
        "grabDoc.exportName",
        "grabDoc.exportResX",
        "grabDoc.exportResY",
        "grabDoc.lockRes",
        "grabDoc.imageType",
        "grabDoc.colorDepth",
        "grabDoc.imageComp",
        "grabDoc.imageCompTIFF",

        "grabDoc.onlyRenderColl",
        "grabDoc.exportPlane",        
        "grabDoc.openFolderOnExport",
        "grabDoc.autoExitCamera",

        "grabDoc.uiVisibilityNormals",
        "grabDoc.uiVisibilityCurvature",
        "grabDoc.uiVisibilityOcclusion",
        "grabDoc.uiVisibilityHeight",
        "grabDoc.uiVisibilityAlpha",
        "grabDoc.uiVisibilityMatID",
        "grabDoc.uiVisibilityAlbedo",

        "grabDoc.exportNormals",
        "grabDoc.reimportAsMatNormals",
        "grabDoc.flipYNormals",
        "grabDoc.samplesNormals",
        "grabDoc.suffixNormals",

        "grabDoc.exportCurvature",
        "grabDoc.ridgeCurvature",
        "grabDoc.valleyCurvature",
        "grabDoc.samplesCurvature",
        "grabDoc.contrastCurvature",
        "grabDoc.suffixCurvature",

        "grabDoc.exportOcclusion",
        "grabDoc.reimportAsMatOcclusion",
        "grabDoc.gammaOcclusion",
        "grabDoc.distanceOcclusion",
        "grabDoc.samplesOcclusion",
        "grabDoc.contrastOcclusion",
        "grabDoc.suffixOcclusion",

        "grabDoc.exportHeight",
        "grabDoc.rangeTypeHeight",
        "grabDoc.guideHeight",
        "grabDoc.invertMaskHeight",
        "grabDoc.samplesHeight",
        "grabDoc.contrastHeight",
        "grabDoc.suffixHeight",
        
        "grabDoc.exportAlpha",
        "grabDoc.invertMaskAlpha",
        "grabDoc.samplesAlpha",
        "grabDoc.suffixAlpha",

        "grabDoc.exportMatID",
        "grabDoc.methodMatID",
        "grabDoc.samplesMatID",
        "grabDoc.suffixID",
        
        "grabDoc.exportAlbedo",
        "grabDoc.samplesAlbedo",
        "grabDoc.suffixAlbedo",

        "grabDoc.exportRoughness",
        "grabDoc.samplesRoughness",
        "grabDoc.suffixRoughness",

        "grabDoc.exportMetalness",
        "grabDoc.samplesMetalness",
        "grabDoc.suffixMetalness",

        "grabDoc.marmoEXE",
        "grabDoc.marmoAutoBake",
        "grabDoc.marmoClosePostBake",
        "grabDoc.marmoSamples",
        "grabDoc.marmoAORayCount"
    ]

    # Where to store the preset
    preset_subdir = "grab_doc"


############################################################
# USER PREFERENCES
############################################################


class GRABDOC_OT_check_for_update(bpy.types.Operator):
    bl_idname = "updater_gd.check_for_update"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        updater.check_for_update_now()
        return{'FINISHED'}


class GRABDOC_MT_addon_prefs(bpy.types.AddonPreferences):
    bl_idname=__package__

    def draw(self, context):
        layout=self.layout
        row=layout.row()

        if updater.update_ready == None:
            row.label(text="Checking for an update...")

            updater.check_for_update_now()

        elif updater.update_ready:
            row.alert=True
            row.label(text="There is a GrabDoc update available! Get it on Gumroad :D")

        elif not updater.update_ready:
            row.label(text="You have the latest version of GrabDoc! There are no new versions available.")

            row.operator("updater_gd.check_for_update", text="", icon="FILE_REFRESH")


############################################################
# PROPERTY GROUP
############################################################


class GRABDOC_property_group(bpy.types.PropertyGroup):
    ### UPDATE FUNCTIONS ###

    def update_scaling_set(self, context):
        scene_setup_and_refresh(self, context)
        
        if self.modalState:
            gd_camera_ob_z = bpy.data.objects.get('GD_Trim Camera').location[2]

            map_range_node = bpy.data.node_groups["GD_Height"].nodes.get('Map Range')
            map_range_node.inputs[1].default_value = -self.guideHeight + gd_camera_ob_z
            map_range_node.inputs[2].default_value = gd_camera_ob_z

            map_range_alpha_node = bpy.data.node_groups["GD_Alpha"].nodes.get('Map Range')
            map_range_alpha_node.inputs[1].default_value = gd_camera_ob_z - .00001
            map_range_alpha_node.inputs[2].default_value = gd_camera_ob_z

    def update_res_x(self, context):
        if self.lockRes:
            if self.exportResX != self.exportResY:
                self.exportResY = self.exportResX

        scene_setup_and_refresh(self, context)

    def update_res_y(self, context):
        if self.lockRes:
            if self.exportResY != self.exportResX:
                self.exportResX = self.exportResY

        scene_setup_and_refresh(self, context)

    def update_export_name(self, context):
        if not self.exportName:
            self.exportName = "untitled"

    def update_curvature(self, context):
        if self.modalState:
            scene_shading = bpy.data.scenes[str(context.scene.name)].display.shading

            scene_shading.cavity_ridge_factor = scene_shading.curvature_ridge_factor = self.ridgeCurvature
            scene_shading.curvature_valley_factor = self.valleyCurvature

    def update_flip_y(self, context):
        vec_multiply_node = bpy.data.node_groups["GD_Normal"].nodes.get('Vector Math')
        vec_multiply_node.inputs[1].default_value[1] = -.5 if self.flipYNormals else .5

    def update_occlusion_gamma(self, context):
        gamma_node = bpy.data.node_groups["GD_Ambient Occlusion"].nodes.get('Gamma')
        gamma_node.inputs[1].default_value = self.gammaOcclusion

    def update_occlusion_distance(self, context):
        ao_node = bpy.data.node_groups["GD_Ambient Occlusion"].nodes.get('Ambient Occlusion')
        ao_node.inputs[1].default_value = self.distanceOcclusion

    def update_manual_height_range(self, context):
        scene_setup_and_refresh(self, context)

        if self.modalState:
            if self.rangeTypeHeight == 'AUTO':
                self.render_list = get_rendered_objects(self, context)

                find_tallest_object(self, context)
                
            bpy.data.objects["GD_Background Plane"].active_material = bpy.data.materials['GD_Material (do not touch contents)']

    def update_height_guide(self, context):
        gd_camera_ob_z = bpy.data.objects.get('GD_Trim Camera').location[2]

        map_range_node = bpy.data.node_groups["GD_Height"].nodes.get('Map Range')
        map_range_node.inputs[1].default_value = gd_camera_ob_z + -self.guideHeight
        map_range_node.inputs[2].default_value = gd_camera_ob_z

        ramp_node = bpy.data.node_groups["GD_Height"].nodes.get('ColorRamp')
        ramp_node.color_ramp.elements[0].color = (0, 0, 0, 1) if self.invertMaskHeight else (1, 1, 1, 1)
        ramp_node.color_ramp.elements[1].color = (1, 1, 1, 1) if self.invertMaskHeight else (0, 0, 0, 1)
        ramp_node.location = (-400,0)

        if self.rangeTypeHeight == 'MANUAL':
            scene_setup_and_refresh(self, context)

        # Update here so that it refreshes live in the VP
        if self.modalState:
            bpy.data.objects["GD_Background Plane"].active_material = bpy.data.materials['GD_Material (do not touch contents)']

    def update_alpha(self, context):
        gd_camera_ob_z = bpy.data.objects.get('GD_Trim Camera').location[2]

        map_range_node = bpy.data.node_groups["GD_Alpha"].nodes.get('Map Range')
        map_range_node.inputs[1].default_value = gd_camera_ob_z - .00001
        map_range_node.inputs[2].default_value = gd_camera_ob_z
        
        invert_node = bpy.data.node_groups["GD_Alpha"].nodes.get('Invert')
        invert_node.inputs[0].default_value = 0 if self.invertMaskAlpha else 1

        # Update here so that it refreshes live in the VP
        if self.modalState:
            bpy.data.objects["GD_Background Plane"].active_material = bpy.data.materials['GD_Material (do not touch contents)']

    def update_export_path(self, context):
        if self.exportPath != '' and not os.path.exists(bpy.path.abspath(self.exportPath)):
            self.exportPath = ''

    ### PROPERTIES ###

    ## SETUP SETTINGS

    collSelectable: BoolProperty(update=scene_setup_and_refresh)
    collVisible: BoolProperty(default=True, update=scene_setup_and_refresh)
    collRendered: BoolProperty(default=True, update=scene_setup_and_refresh)
                                       
    scalingSet: FloatProperty(name="", default=2, min=.1, soft_max=100, precision=3, subtype='DISTANCE', update=update_scaling_set)
    
    refSelection: PointerProperty(type=bpy.types.Image, update=scene_setup_and_refresh)
    
    useGrid: BoolProperty(default=True, update=scene_setup_and_refresh)
    gridSubdivisions: IntProperty(name="", default=0, min=0, soft_max=64, update=scene_setup_and_refresh)

    ## BAKER SEETINGS

    bakerType: EnumProperty(
        items=(
            ('Blender', "Blender (Built-in)", "Set Baker: Blender (Built-in)"),
            ('Marmoset', "Toolbag 3 & 4", "Set Baker: Marmoset Toolbag 3&4")
        ),
        name="Baker"    
    )

    exportPath: StringProperty(name="", default=" ", description="", subtype='DIR_PATH', update=update_export_path)
    
    exportResX: IntProperty(name="", default=2048, min=4, soft_max=8192, update=update_res_x)
    exportResY: IntProperty(name="", default=2048, min=4, soft_max=8192, update=update_res_y)
    
    lockRes: BoolProperty(default=True, update=update_res_x)
    
    exportName: StringProperty(name="", description="File export name", default="untitled", update=update_export_name)
    
    imageType: EnumProperty(
        items=(
            ('PNG', "PNG", ""),
            ('TIFF', "TIFF", ""),
            ('TARGA', "TGA", "")
        ),
        name="Format"
    )

    imageType_marmo: EnumProperty(
        items=(
            ('PNG', "PNG", ""),
            ('PSD', "PSD", ""),
        ),
        name="Format"
    )
    
    colorDepth: EnumProperty(
        items=(
            ('16', "16", ""),
            ('8', "8", "")
        )
    )

    fakeColorDepth: EnumProperty(
        items=(
            ('16', "16", ""),
            ('8', "8", "")
        ),
        default='8'
    )

    imageComp: IntProperty(
        name="",
        default=50,
        min=0,
        max=100,
        description='Lossless Compression for smaller image sizes, but longer export times',
        subtype='PERCENTAGE'
    )
    
    imageCompTIFF: EnumProperty(
        items=(
            ('NONE', "None", ""),
            ('DEFLATE', "Deflate", ""),
            ('LZW', "LZW", ""),
            ('PACKBITS', "Pack Bits", "")
        ),
        name='Compression',
        default='DEFLATE'
    )

    onlyRenderColl: BoolProperty(
        update=scene_setup_and_refresh,
        description="This will add a collection to the scene which GrabDoc will ONLY render from, ignoring objects outside of it. This option is useful if objects aren't visible in the renders"
    )
    
    exportPlane: BoolProperty(name="Export Plane", description="Exports the background plane as an FBX for use externally")
    
    openFolderOnExport: BoolProperty(description="Open the folder path in your File Explorer on map export")

    uiVisibilityNormals: BoolProperty(default=True)
    uiVisibilityCurvature: BoolProperty(default=True)
    uiVisibilityOcclusion: BoolProperty(default=True)
    uiVisibilityHeight: BoolProperty(default=True)
    uiVisibilityMatID: BoolProperty(default=True)
    uiVisibilityAlpha: BoolProperty(default=True)
    uiVisibilityAlbedo: BoolProperty(default=False)
    uiVisibilityRoughness: BoolProperty(default=False)
    uiVisibilityMetalness: BoolProperty(default=False)

    ## BAKE MAP SETTINGS

    # Normals
    exportNormals: BoolProperty(default=True)

    reimportAsMatNormals: BoolProperty(description="Reimport the Normal map as a material for use in Blender")

    flipYNormals: BoolProperty(name="Flip Y (-Y)", description="Flip the normal map Y direction", options={'SKIP_SAVE'}, update=update_flip_y)

    suffixNormals: StringProperty(
        name="",
        description="The suffix of the exported bake map",
        default="normal"
    )

    samplesNormals: IntProperty(name="", default=128, min=1, max=512)

    # Curvature
    exportCurvature: BoolProperty(default=True)

    ridgeCurvature: FloatProperty(name="", default=2, min=0, max=2, precision=3, step=.1, update=update_curvature, subtype='FACTOR')

    valleyCurvature: FloatProperty(name="", default=1.5, min=0, max=2, precision=3, step=.1, update=update_curvature, subtype='FACTOR')

    suffixCurvature: StringProperty(
        name="",
        description="The suffix of the exported bake map",
        default="curvature"
    )

    contrastCurvature: EnumProperty(
        items=(
            ('None', "None (Medium)", ""),
            ('Very_High_Contrast', "Very High", ""),
            ('High_Contrast', "High", ""),
            ('Medium_High_Contrast', "Medium High", ""),
            ('Medium_Low_Contrast', "Medium Low", ""),
            ('Low_Contrast', "Low", ""),
            ('Very_Low_Contrast', "Very Low", "")
        ),
        name="Curvature Contrast"
    )

    samplesCurvature: EnumProperty(
        items=(
            ('OFF', "No Anti-Aliasing", ""),
            ('FXAA', "1 Sample", ""),
            ('5', "5 Samples", ""),
            ('8', "8 Samples", ""),
            ('11', "11 Samples", ""),
            ('16', "16 Samples", ""),
            ('32', "32 Samples", "")
        ),
        default="32",
        name="Curvature Samples"
    )

    # Occlusion
    exportOcclusion: BoolProperty(default=True)
    
    reimportAsMatOcclusion: BoolProperty(description="This will reimport the Occlusion map as a material for use in Blender")
    
    gammaOcclusion: FloatProperty(
        default=1,
        min=.001,
        soft_max=10,
        step=.17,
        name="",
        description="Intensity of AO (calculated with gamma)",
        update=update_occlusion_gamma
    )
    
    distanceOcclusion: FloatProperty(
        default=1,
        min=0,
        soft_max=100,
        step=.03,
        subtype='DISTANCE',
        name="",
        description="The distance AO rays travel",
        update=update_occlusion_distance
    )

    suffixOcclusion: StringProperty(
        name="",
        description="The suffix of the exported bake map",
        default="ao"
    )
    
    samplesOcclusion: IntProperty(name="", default=128, min=1, max=512)

    contrastOcclusion: EnumProperty(
        items=(
            ('None', "None (Medium)", ""),
            ('Very_High_Contrast', "Very High", ""),
            ('High_Contrast', "High", ""),
            ('Medium_High_Contrast', "Medium High", ""),
            ('Medium_Low_Contrast', "Medium Low", ""),
            ('Low_Contrast', "Low", ""),
            ('Very_Low_Contrast', "Very Low", "")
        ),
        name="Occlusion Contrast"
    )                      

    # Height
    exportHeight: BoolProperty(default=True, update=scene_setup_and_refresh)

    invertMaskHeight: BoolProperty(description="Invert the Height mask, this is useful if you are sculpting into a plane mesh", update=update_height_guide)

    guideHeight: FloatProperty(name="", default=1, min=.01, soft_max=100, step=.03, subtype='DISTANCE', update=update_height_guide)

    rangeTypeHeight: EnumProperty(
        items=(
            ('AUTO', "Auto", ""),
            ('MANUAL', "Manual", "")
        ),
        update=update_manual_height_range,
        description="Automatic or manual height range. Use manual if automatic is giving you incorrect results or if baking is really slow"
    )

    suffixHeight: StringProperty(
        name="",
        description="The suffix of the exported bake map",
        default="height"
    )

    samplesHeight: IntProperty(name="", default=128, min=1, max=512)

    contrastHeight: EnumProperty(
        items=(
            ('None', "None (Medium)", ""),
            ('Very_High_Contrast', "Very High", ""),
            ('High_Contrast', "High", ""),
            ('Medium_High_Contrast', "Medium High", ""),
            ('Medium_Low_Contrast', "Medium Low", ""),
            ('Low_Contrast', "Low", ""),
            ('Very_Low_Contrast', "Very Low", "")
        ),
        name="Height Contrast"
    ) 

    # Alpha
    exportAlpha: BoolProperty(update=scene_setup_and_refresh)

    invertMaskAlpha: BoolProperty(description="Invert the Alpha mask", update=update_alpha)

    suffixAlpha: StringProperty(
        name="",
        description="The suffix of the exported bake map",
        default="alpha"
    )

    samplesAlpha: IntProperty(name="", default=128, min=1, max=512)

    # MatID
    exportMatID: BoolProperty(default=True)

    methodMatID: EnumProperty(
        items=(
            ('RANDOM', "Random", ""),
            ('MATERIAL', "Material", "")
        )
    )

    fakeMethodMatID: EnumProperty( # Not actually used, just for UI representation
        items=(
            ('RANDOM', "Random", ""),
            ('MATERIAL', "Material", "")
        ),
        default="MATERIAL"
    )

    suffixID: StringProperty(
        name="",
        description="The suffix of the exported bake map",
        default="matID"
    )

    samplesMatID: EnumProperty(
        items=(
            ('OFF', "No Anti-Aliasing", ""),
            ('FXAA', "1 Sample", ""),
            ('5', "5 Samples", ""),
            ('8', "8 Samples", ""),
            ('11', "11 Samples", ""),
            ('16', "16 Samples", ""),
            ('32', "32 Samples", "")
        ),
        default="OFF",
        name="Mat ID Samples"
    )

    # Albedo
    exportAlbedo: BoolProperty(update=scene_setup_and_refresh)

    suffixAlbedo: StringProperty(
        name="",
        description="The suffix of the exported bake map",
        default="albedo"
    )

    samplesAlbedo: IntProperty(name="", default=128, min=1, max=512)

    # Roughness
    exportRoughness: BoolProperty(update=scene_setup_and_refresh)

    suffixRoughness: StringProperty(
        name="",
        description="The suffix of the exported bake map",
        default="roughness"
    )

    samplesRoughness: IntProperty(name="", default=128, min=1, max=512)

    # Metalness
    exportMetalness: BoolProperty(update=scene_setup_and_refresh)

    suffixMetalness: StringProperty(
        name="",
        description="The suffix of the exported bake map",
        default="metalness"
    )

    samplesMetalness: IntProperty(name="", default=128, min=1, max=512)
    
    ## MAP PREVIEW

    firstBakePreview: BoolProperty(default=True)
    
    autoExitCamera: BoolProperty()

    modalState: BoolProperty()

    modalPreviewType: EnumProperty(
        items=(
            ('none', "None", ""),
            ('normals', "Normals", ""),
            ('curvature', "Curvature", ""),
            ('occlusion', "Ambient Occlusion", ""),
            ('height', "Height", ""),
            ('ID', "Material ID", ""),
            ('alpha', "Alpha", ""),
            ('albedo', "Albedo", ""),
            ('roughness', "Roughness", ""),
            ('metalness', "Metalness", "")
        )
    )

    ## MARMOSET BAKING

    marmoEXE: StringProperty(
        name="",
        description="Changes the name of the exported file",
        default="",
        subtype="FILE_PATH"
    )

    marmoAutoBake: BoolProperty(name="Auto bake", default=True)

    marmoClosePostBake: BoolProperty(name="Close after baking")

    marmoSamples: EnumProperty(
        items=(
            ('1', "1x", ""),
            ('4', "4x", ""),
            ('16', "16x", ""),
            ('64', "64x", "")
        ),
        default="16",
        name="Marmoset Samples",
        description='The amount of samples rendered per pixel. 64x samples will NOT work in Marmoset 3 and will default to 16x samples'
    )

    marmoAORayCount: IntProperty(default=512, min=32, soft_max=4096)


##################################
# REGISTRATION
##################################


classes = (
    GRABDOC_MT_presets,
    GRABDOC_PT_presets,
    GRABDOC_OT_add_preset,
    GRABDOC_property_group,
    GRABDOC_MT_addon_prefs,
    GRABDOC_OT_check_for_update
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.grabDoc=PointerProperty(type=GRABDOC_property_group)

    # Set the updaters repo
    updater.user="oRazeD"
    updater.repo="grabdoc"
    updater.current_version=bl_info["version"]

    # Initial check for repo updates
    updater.check_for_update_now()

    if updater.update_ready:
        print("There is a GrabDoc update available!")


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


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
