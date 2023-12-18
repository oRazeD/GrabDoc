import os

import bpy
from bl_operators.presets import AddPresetBase
from bl_ui.utils import PresetPanel
from bpy.types import (
    Menu,
    Panel,
    Operator,
    AddonPreferences,
    Context,
    PropertyGroup,
    Image,
    Scene,
    Collection,
    Object
)
from bpy.props import (
    BoolProperty,
    PointerProperty,
    StringProperty,
    EnumProperty,
    IntProperty,
    FloatProperty
)

from .constants import GlobalVariableConstants as Global
from .utils.scene import scene_setup
from .utils.render import get_rendered_objects, set_guide_height

from .addon_updater import Updater as updater
from .constants import VERSION


################################################
# PRESETS
################################################


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


class GRABDOC_OT_add_preset(AddPresetBase, Operator):
    bl_idname = "grab_doc.preset_add"
    bl_label = "Add a new preset"
    preset_menu = "GRABDOC_MT_presets"

    # Variable used for all preset values
    preset_defines = ["grabDoc=bpy.context.scene.grabDoc"]

    # TODO: Create a function that
    # generates this list below

    # Properties to store in the preset
    preset_values = [
        "gd.collSelectable",
        "gd.collVisible",
        "gd.collRendered",
        "gd.useGrid",
        "gd.gridSubdivisions",
        "gd.useFiltering",
        "gd.widthFiltering",
        "gd.scalingSet",

        "gd.bakerType",
        "gd.exportPath",
        "gd.exportName",
        "gd.exportResX",
        "gd.exportResY",
        "gd.lockRes",
        "gd.imageType",
        "gd.colorDepth",
        "gd.colorDepthTGA",
        "gd.imageCompPNG",

        "gd.useBakeCollection",
        "gd.exportPlane",
        "gd.openFolderOnExport",
        "gd.autoExitCamera",

        "gd.uiVisibilityNormals",
        "gd.uiVisibilityCurvature",
        "gd.uiVisibilityOcclusion",
        "gd.uiVisibilityHeight",
        "gd.uiVisibilityMatID",
        "gd.uiVisibilityAlpha",
        "gd.uiVisibilityAlbedo",
        "gd.uiVisibilityRoughness",
        "gd.uiVisibilityMetalness",

        "gd.exportNormals",
        "gd.reimportAsMatNormals",
        "gd.flipYNormals",
        "gd.useTextureNormals",
        "gd.samplesNormals",
        "gd.suffixNormals",
        "gd.samplesCyclesNormals",
        "gd.engineNormals",

        "gd.exportCurvature",
        "gd.ridgeCurvature",
        "gd.valleyCurvature",
        "gd.samplesCurvature",
        "gd.contrastCurvature",
        "gd.suffixCurvature",

        "gd.exportOcclusion",
        "gd.reimportAsMatOcclusion",
        "gd.gammaOcclusion",
        "gd.distanceOcclusion",
        "gd.samplesOcclusion",
        "gd.contrastOcclusion",
        "gd.suffixOcclusion",

        "gd.exportHeight",
        "gd.rangeTypeHeight",
        "gd.guideHeight",
        "gd.invertMaskHeight",
        "gd.samplesHeight",
        "gd.contrastHeight",
        "gd.suffixHeight",

        "gd.exportAlpha",
        "gd.invertMaskAlpha",
        "gd.samplesAlpha",
        "gd.suffixAlpha",

        "gd.exportMatID",
        "gd.methodMatID",
        "gd.samplesMatID",
        "gd.suffixID",

        "gd.exportAlbedo",
        "gd.samplesAlbedo",
        "gd.suffixAlbedo",
        "gd.samplesCyclesAlbedo",
        "gd.engineAlbedo",

        "gd.exportRoughness",
        "gd.invertMaskRoughness",
        "gd.samplesRoughness",
        "gd.suffixRoughness",
        "gd.samplesCyclesRoughness",
        "gd.engineRoughness",

        "gd.exportMetalness",
        "gd.samplesMetalness",
        "gd.suffixMetalness",
        "gd.samplesCyclesMetalness",
        "gd.engineMetalness",

        "gd.marmoAutoBake",
        "gd.marmoClosePostBake",
        "gd.marmoSamples",
        "gd.marmoAORayCount",
        "gd.imageType_marmo"
    ]

    # Where to store the preset
    preset_subdir = "grab_doc"


############################################################
# USER PREFERENCES
############################################################


class GRABDOC_OT_check_for_update(Operator):
    bl_idname = "updater_gd.check_for_update"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, _context: Context):
        updater.check_for_update_now()
        return {'FINISHED'}


class GRABDOC_MT_addon_preferences(AddonPreferences):
    bl_idname = __package__

    # Store this here so the value is saved across project files
    marmoEXE: StringProperty(
        name="",
        description="Changes the name of the exported file",
        default="",
        subtype="FILE_PATH"
    )

    def draw(self, _context: Context):
        layout = self.layout
        row = layout.row()

        if updater.update_ready is None:
            row.label(text="Checking for an update...")

            updater.check_for_update_now()

        elif updater.update_ready:
            row.alert = True
            row.label(
                text="There is a GrabDoc update available! Get it on Gumroad :D")

        elif not updater.update_ready:
            row.label(
                text="You have the latest version of GrabDoc! There are no new versions available."
            )
            row.operator("updater_gd.check_for_update",
                         text="", icon="FILE_REFRESH")


############################################################
# PROPERTY GROUP
############################################################


class GRABDOC_property_group(PropertyGroup):
    # UPDATE FUNCTIONS

    def update_scaling_set(self, context: Context):
        scene_setup(self, context)

        gd_camera_ob_z = bpy.data.objects.get(
            Global.TRIM_CAMERA_NAME
        ).location[2]
        height_ng = bpy.data.node_groups.get(Global.NG_HEIGHT_NAME)

        map_range = height_ng.nodes.get('Map Range')
        map_range.inputs[1].default_value = \
            - self.guideHeight + gd_camera_ob_z
        map_range.inputs[2].default_value = gd_camera_ob_z

        map_range_alpha = \
            bpy.data.node_groups[Global.NG_ALPHA_NAME].nodes.get('Map Range')
        map_range_alpha.inputs[1].default_value = gd_camera_ob_z - .00001
        map_range_alpha.inputs[2].default_value = gd_camera_ob_z

    def update_res_x(self, context: Context):
        if self.lockRes and self.exportResX != self.exportResY:
                self.exportResY = self.exportResX
        scene_setup(self, context)

    def update_res_y(self, context: Context):
        if self.lockRes and self.exportResY != self.exportResX:
            self.exportResX = self.exportResY
        scene_setup(self, context)

    def update_export_name(self, _context: Context):
        if not self.exportName:
            self.exportName = "untitled"

    def update_useTextureNormals(self, _context: Context) -> None:
        if not self.modalState:
            return
        ng_normal = bpy.data.node_groups[Global.NG_NORMAL_NAME]
        vec_transform = ng_normal.nodes.get('Vector Transform')
        group_output = ng_normal.nodes.get('Group Output')

        links = ng_normal.links
        if self.useTextureNormals:
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

    def update_curvature(self, context: Context):
        if self.modalState:
            scene_shading = bpy.data.scenes[str(
                context.scene.name)].display.shading

            scene_shading.cavity_ridge_factor = scene_shading.curvature_ridge_factor = self.ridgeCurvature
            scene_shading.curvature_valley_factor = self.valleyCurvature

    def update_flip_y(self, _context: Context):
        vec_multiply = bpy.data.node_groups[Global.NG_NORMAL_NAME].nodes.get(
            'Vector Math')
        vec_multiply.inputs[1].default_value[1] = -.5 if self.flipYNormals else .5

    def update_occlusion_gamma(self, _context: Context):
        gamma = bpy.data.node_groups[Global.NG_AO_NAME].nodes.get('Gamma')
        gamma.inputs[1].default_value = self.gammaOcclusion

    def update_occlusion_distance(self, _context: Context):
        ao = bpy.data.node_groups[Global.NG_AO_NAME].nodes.get(
            'Ambient Occlusion')
        ao.inputs[1].default_value = self.distanceOcclusion

    def update_manual_height_range(self, context: Context):
        scene_setup(self, context)
        if self.modalState:
            bpy.data.objects[Global.BG_PLANE_NAME].active_material = bpy.data.materials[Global.GD_MATERIAL_NAME]
            if self.rangeTypeHeight == 'AUTO':
                rendered_obs = get_rendered_objects(context)
                set_guide_height(rendered_obs)

    def update_height_guide(self, context: Context):
        gd_camera_ob_z = \
            bpy.data.objects.get(Global.TRIM_CAMERA_NAME).location[2]

        map_range = \
            bpy.data.node_groups[Global.NG_HEIGHT_NAME].nodes.get('Map Range')
        map_range.inputs[1].default_value = \
            gd_camera_ob_z + -self.guideHeight
        map_range.inputs[2].default_value = \
            gd_camera_ob_z

        ramp = bpy.data.node_groups[Global.NG_HEIGHT_NAME].nodes.get(
            'ColorRamp')
        ramp.color_ramp.elements[0].color = \
            (0, 0, 0, 1) if self.invertMaskHeight else (1, 1, 1, 1)
        ramp.color_ramp.elements[1].color = \
            (1, 1, 1, 1) if self.invertMaskHeight else (0, 0, 0, 1)
        ramp.location = \
            (-400, 0)

        if self.rangeTypeHeight == 'MANUAL':
            scene_setup(self, context)

        # Update here so that it refreshes live in the VP
        if self.modalState:
            bpy.data.objects[Global.BG_PLANE_NAME].active_material = bpy.data.materials[Global.GD_MATERIAL_NAME]

    def update_alpha(self, _context: Context):
        gd_camera_ob_z = bpy.data.objects.get(
            Global.TRIM_CAMERA_NAME).location[2]

        map_range = bpy.data.node_groups[Global.NG_ALPHA_NAME].nodes.get(
            'Map Range')
        map_range.inputs[1].default_value = gd_camera_ob_z - .00001
        map_range.inputs[2].default_value = gd_camera_ob_z

        invert = bpy.data.node_groups[Global.NG_ALPHA_NAME].nodes.get(
            'Invert')
        invert.inputs[0].default_value = 0 if self.invertMaskAlpha else 1

        # Update here so that it refreshes live in the VP
        if self.modalState:
            bpy.data.objects[Global.BG_PLANE_NAME].active_material = bpy.data.materials[Global.GD_MATERIAL_NAME]

    def update_roughness(self, _context: Context):
        invert = bpy.data.node_groups[Global.NG_ROUGHNESS_NAME].nodes.get(
            'Invert')
        invert.inputs[0].default_value = 1 if self.invertMaskRoughness else 0

        # Update here so that it refreshes live in the VP
        # if self.modalState:
        #    bpy.data.objects[BG_PLANE_NAME].active_material = bpy.data.materials[GD_MATERIAL_NAME]

    def update_engine(self, context: Context):
        if not self.modalState:
            return
        if self.modalPreviewType == 'normals':
            context.scene.render.engine = str(self.engineNormals).upper()
        elif self.modalPreviewType == 'albedo':
            context.scene.render.engine = str(self.engineAlbedo).upper()
        elif self.modalPreviewType == 'roughness':
            context.scene.render.engine = str(self.engineRoughness).upper()
        elif self.modalPreviewType == 'metalness':
            context.scene.render.engine = str(self.engineMetalness).upper()

    def update_export_path(self, _context: Context):
        export_path_exists = \
            os.path.exists(bpy.path.abspath(self.exportPath))
        if self.exportPath != '' and not export_path_exists:
            self.exportPath = ''

    # PROPERTIES

    # Setup settings
    collSelectable: BoolProperty(
        update=scene_setup,
        description='Sets the background plane selection capability'
    )
    collVisible: BoolProperty(default=True, update=scene_setup,
                              description='Sets the visibility in the viewport')
    collRendered: BoolProperty(
        default=True,
        update=scene_setup,
        description='Sets the visibility in exports, this will also enable transparency and alpha channel exports if visibility is turned off'
    )

    scalingSet: FloatProperty(
        name="Scaling Set",
        default=2,
        min=.1,
        soft_max=100,
        precision=3,
        subtype='DISTANCE',
        description='Sets the scaling of the background plane and camera (WARNING: This will be the scaling used in tandem with `Export Plane as FBX`)',
        update=update_scaling_set
    )
    useFiltering: BoolProperty(  # TODO: add to cycles
        name='Use Filtering',
        default=True,
        description='Use pixel filtering on render. Useful to turn OFF for when you want to avoid aliased edges on stuff like Normal stamps',
        update=scene_setup
    )
    widthFiltering: FloatProperty(
        name="Filter Amount",
        default=1.2,
        min=0,
        soft_max=10,
        subtype='PIXEL',
        description='The width in pixels used for filtering',
        update=scene_setup
    )

    refSelection: PointerProperty(
        name='Reference Selection',
        type=Image,
        description='Select an image reference to use on the background plane',
        update=scene_setup
    )
    useGrid: BoolProperty(
        name='Use Grid',
        default=True,
        description='Create a grid on the background plane for better usability while snapping',
        update=scene_setup
    )
    gridSubdivisions: IntProperty(
        name="Grid Subdivisions",
        default=0,
        min=0,
        soft_max=64,
        description='The amount of subdivisions the grid will have',
        update=scene_setup
    )

    # Baker settings
    bakerType: EnumProperty(
        items=(
            ('Blender', "Blender (Built-in)", "Set Baker: Blender (Built-in)"),
            ('Marmoset', "Toolbag 3 & 4", "Set Baker: Marmoset Toolbag 3&4")
        ),
        name="Baker"
    )

    exportPath: StringProperty(
        name="Export Filepath",
        default=" ",
        description="This is the path all files will be exported to",
        subtype='DIR_PATH',
        update=update_export_path
    )

    exportResX: IntProperty(
        name="Res X",
        default=2048,
        min=4, soft_max=8192,
        update=update_res_x
    )
    exportResY: IntProperty(
        name="Res Y",
        default=2048,
        min=4, soft_max=8192,
        update=update_res_y
    )

    lockRes: BoolProperty(
        name='Sync Resolution',
        default=True,
        update=update_res_x
    )

    exportName: StringProperty(
        name="",
        description="Export name used for all exported maps. You can also add a prefix here",
        default="untitled",
        update=update_export_name
    )

    imageType: EnumProperty(
        items=(
            ('PNG', "PNG", ""),
            ('TIFF', "TIFF", ""),
            ('TARGA', "TGA", ""),
            ('OPEN_EXR', "EXR", "")
        ),
        name="Format"
    )

    # PNG/ALL
    colorDepth: EnumProperty(
        items=(
            ('16', "16", ""),
            ('8', "8", "")
        )
    )

    imageCompPNG: IntProperty(  # Use our own property so we can assign a new default
        name="",
        default=50,
        min=0,
        max=100,
        description='Lossless Compression for smaller image sizes, but longer export times',
        subtype='PERCENTAGE'
    )

    # EXR
    colorDepthEXR: EnumProperty(
        items=(
            ('16', "16", ""),
            ('32', "32", "")
        )
    )

    # TGA
    colorDepthTGA: EnumProperty(
        items=(
            ('16', "16", ""),
            ('8', "8", "")
        ),
        default='8'
    )

    useBakeCollection: BoolProperty(
        description="This will add a collection to the scene which GrabDoc will ONLY render from, ignoring objects outside of it. This option is useful if objects aren't visible in the renders",
        update=scene_setup
    )

    exportPlane: BoolProperty(
        description="Exports the background plane as an FBX for use externally"
    )

    openFolderOnExport: BoolProperty(
        description="Open the folder path in your File Explorer on map export"
    )

    uiVisibilityNormals: BoolProperty(default=True)
    uiVisibilityCurvature: BoolProperty(default=True)
    uiVisibilityOcclusion: BoolProperty(default=True)
    uiVisibilityHeight: BoolProperty(default=True)
    uiVisibilityMatID: BoolProperty(default=True)
    uiVisibilityAlpha: BoolProperty(default=True)
    uiVisibilityAlbedo: BoolProperty(default=True)
    uiVisibilityRoughness: BoolProperty(default=True)
    uiVisibilityMetalness: BoolProperty(default=True)

    # Map packing settings TODO: ADD TO PRESETS
    packMaps: BoolProperty(
        name='Enable Packing on Export',
        default=False
    )

    MAP_TYPES = (
        ('curvature', "Curvature", ""),
        ('occlusion', "Occlusion", ""),
        ('height', "Height", ""),
        ('alpha', "Alpha", ""),
        ('roughness', "Roughness", ""),
        ('metalness', "Metalness", ""),
    )

    channel_R: EnumProperty(
        items=MAP_TYPES,
        default="occlusion",
        name='R'
    )
    channel_G: EnumProperty(
        items=MAP_TYPES,
        default="roughness",
        name='G'
    )
    channel_B: EnumProperty(
        items=MAP_TYPES,
        default="metalness",
        name='B'
    )
    channel_A: EnumProperty(
        items=MAP_TYPES,
        default="alpha",
        name='A'
    )

    # BAKE MAP SETTINGS

    # Normals
    exportNormals: BoolProperty(name='Export Normals', default=True)
    reimportAsMatNormals: BoolProperty(
        description="Reimport the Normal map as a material for use in Blender"
    )
    flipYNormals: BoolProperty(
        name="Flip Y (-Y)",
        description="Flip the normal map Y direction",
        options={'SKIP_SAVE'},
        update=update_flip_y
    )
    useTextureNormals: BoolProperty(
        name="Use Texture Normals",
        description="Use texture normals linked to the Principled BSDF",
        options={'SKIP_SAVE'},
        default=True,
        update=update_useTextureNormals
    )
    suffixNormals: StringProperty(
        name="",
        description="The suffix of the exported bake map",
        default="normal"
    )
    samplesNormals: IntProperty(name="", default=128, min=1, max=512)
    samplesCyclesNormals: IntProperty(name="", default=32, min=1, max=1024)
    engineNormals: EnumProperty(
        items=(
            ('blender_eevee', "Eevee", ""),
            ('cycles', "Cycles", "")
        ),
        default="blender_eevee",
        name='Render Engine',
        update=update_engine
    )

    # Curvature
    exportCurvature: BoolProperty(name='Export Curvature', default=True)
    ridgeCurvature: FloatProperty(
        name="",
        default=2,
        min=0,
        max=2,
        precision=3,
        step=.1,
        update=update_curvature,
        subtype='FACTOR'
    )
    valleyCurvature: FloatProperty(
        name="",
        default=1.5,
        min=0,
        max=2,
        precision=3,
        step=.1,
        update=update_curvature,
        subtype='FACTOR'
    )
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
    exportOcclusion: BoolProperty(name='Export Occlusion', default=True)
    reimportAsMatOcclusion: BoolProperty(
        description="This will reimport the Occlusion map as a material for use in Blender"
    )
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
    exportHeight: BoolProperty(
        name='Export Height', default=True, update=scene_setup)
    invertMaskHeight: BoolProperty(
        description="Invert the Height mask, this is useful if you are sculpting into a plane mesh",
        update=update_height_guide
    )
    guideHeight: FloatProperty(
        name="",
        default=1,
        min=.01,
        soft_max=100,
        step=.03,
        subtype='DISTANCE',
        update=update_height_guide
    )
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
    exportAlpha: BoolProperty(name='Export Alpha', update=scene_setup)
    invertMaskAlpha: BoolProperty(
        description="Invert the Alpha mask", update=update_alpha
    )
    suffixAlpha: StringProperty(
        name="",
        description="The suffix of the exported bake map",
        default="alpha"
    )
    samplesAlpha: IntProperty(name="", default=128, min=1, max=512)

    # MatID
    exportMatID: BoolProperty(name='Export Material ID', default=True)
    methodMatID: EnumProperty(
        items=(
            ('RANDOM', "Random", ""),
            ('MATERIAL', "Material", ""),
            ('VERTEX', "Object / Vertex", "")
        ),
        name='ID Method'
    )
    fakeMethodMatID: EnumProperty(  # Not actually used, just for UI representation
        items=(
            ('RANDOM', "Random", ""),
            ('MATERIAL', "Material", ""),
            ('VERTEX', "Object / Vertex", "")
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
    exportAlbedo: BoolProperty(name='Export Albedo', update=scene_setup)
    suffixAlbedo: StringProperty(
        name="",
        description="The suffix of the exported bake map",
        default="albedo"
    )
    samplesAlbedo: IntProperty(name="", default=128, min=1, max=512)
    samplesCyclesAlbedo: IntProperty(name="", default=32, min=1, max=1024)
    engineAlbedo: EnumProperty(
        items=(
            ('blender_eevee', "Eevee", ""),
            ('cycles', "Cycles", "")
        ),
        default="blender_eevee",
        name='Render Engine',
        update=update_engine
    )

    # Roughness
    exportRoughness: BoolProperty(name='Export Roughness', update=scene_setup)
    invertMaskRoughness: BoolProperty(
        description="Invert the Roughess (to make Glossines)", update=update_roughness
    )
    suffixRoughness: StringProperty(
        name="",
        description="The suffix of the exported bake map",
        default="roughness"
    )
    samplesRoughness: IntProperty(name="", default=128, min=1, max=512)
    samplesCyclesRoughness: IntProperty(name="", default=32, min=1, max=1024)
    engineRoughness: EnumProperty(
        items=(
            ('blender_eevee', "Eevee", ""),
            ('cycles', "Cycles", "")
        ),
        default="blender_eevee",
        name='Render Engine',
        update=update_engine
    )

    # Metalness
    exportMetalness: BoolProperty(name='Export Metalness', update=scene_setup)
    suffixMetalness: StringProperty(
        name="",
        description="The suffix of the exported bake map",
        default="metalness"
    )
    samplesCyclesMetalness: IntProperty(name="", default=32, min=1, max=1024)
    samplesMetalness: IntProperty(name="", default=128, min=1, max=512)
    engineMetalness: EnumProperty(
        items=(
            ('blender_eevee', "Eevee", ""),
            ('cycles', "Cycles", "")
        ),
        default="blender_eevee",
        name='Render Engine',
        update=update_engine
    )

    # MAP PREVIEW

    firstBakePreview: BoolProperty(default=True)
    autoExitCamera: BoolProperty(
        description='Whether or not the camera view will automatically be left when exiting a Map Preview'
    )
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

    # MARMOSET BAKING

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
    imageType_marmo: EnumProperty(
        items=(
            ('PNG', "PNG", ""),
            ('PSD', "PSD", "")
        ),
        name="Format"
    )


##################################
# REGISTRATION
##################################


classes = (
    GRABDOC_MT_presets,
    GRABDOC_PT_presets,
    GRABDOC_OT_add_preset,
    GRABDOC_property_group,
    GRABDOC_MT_addon_preferences,
    GRABDOC_OT_check_for_update
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    Scene.grabDoc = PointerProperty(type=GRABDOC_property_group)
    Collection.is_gd_collection = BoolProperty()
    Object.is_gd_object = BoolProperty()

    # Set the updaters repo
    updater.user = "oRazeD"
    updater.repo = "grabdoc"
    updater.current_version = VERSION

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
