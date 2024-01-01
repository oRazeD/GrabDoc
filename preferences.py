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
    CollectionProperty,
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
    preset_subdir = "gd"
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
    preset_defines = [
        "gd = bpy.context.scene.gd"
    ]

    # Properties to store
    # TODO: Create a function
    # to generate list
    preset_values = [
        "gd.coll_selectable",
        "gd.coll_visible",
        "gd.coll_rendered",
        "gd.use_grid",
        "gd.grid_subdivs",
        "gd.filter",
        "gd.filter_width",
        "gd.scale",

        "gd.baker_type",
        "gd.export_path",
        "gd.export_name",
        "gd.export_res_x",
        "gd.export_res_y",
        "gd.lock_res",
        "gd.format",
        "gd.depth",
        "gd.tga_depth",
        "gd.png_compression",

        "gd.use_bake_collections",
        "gd.export_plane",
        "gd.preview_auto_exit_camera",

        "gd.marmoset_auto_bake",
        "gd.marmoset_auto_close",
        "gd.marmoset_samples",
        "gd.marmoset_occlusion_ray_count",
        "gd.marmoset_format",

        "gd.normals",
        "gd.curvature",
        "gd.occlusion",
        "gd.height",
        "gd.alpha",
        "gd.id",
        "gd.color",
        "gd.roughness",
        "gd.metalness",
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

    # NOTE: Special properties stored
    # here are saved in User Preferences
    # AKA across project files

    marmoset_executable: StringProperty(
        name="",
        description="",
        default="Path to Marmoset Toolbag 3 or 4 executable",
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
            row.label(text="There is a GrabDoc update available!")
        elif not updater.update_ready:
            row.label(text="You have the latest version of GrabDoc!")
            row.operator(
                "updater_gd.check_for_update",
                text="",
                icon="FILE_REFRESH"
            )


############################################################
# PROPERTY GROUP
############################################################


class GRABDOC_baker_defaults():
    NAME = ""
    ALIAS = NAME.capitalize()
    MARMOSET_COMPATIBLE = True
    SUPPORTED_ENGINES = (
        ('blender_eevee', "Eevee",     ""),
        ('cycles',        "Cycles",    ""),
        ('workbench',     "Workbench", "")
    )

    def update_engine(self, context: Context):
        if not context.scene.gd.preview_state:
            return
        context.scene.render.engine = str(self.engine).upper()

    enabled: BoolProperty(name="Export Enabled", default=True)
    ui_visibility: BoolProperty(default=True)
    reimport: BoolProperty(
        name="Reimport Texture",
        description="Reimport bake map texture into a Blender material"
    )
    suffix: StringProperty(
        name="Suffix",
        description="The suffix of the exported bake map",
        default=NAME # NOTE: Set on item creation
    )
    contrast: EnumProperty(
        items=(
            ('None', "None (Medium)", ""),
            ('Very_High_Contrast', "Very High", ""),
            ('High_Contrast', "High", ""),
            ('Medium_High_Contrast', "Medium High", ""),
            ('Medium_Low_Contrast', "Medium Low", ""),
            ('Low_Contrast', "Low", ""),
            ('Very_Low_Contrast', "Very Low", "")
        ),
        name="Contrast"
    )
    samples: IntProperty(
        name="Eevee Samples", default=128, min=1, soft_max=512
    )
    samples_workbench: EnumProperty(
        items=(
            ('OFF', "No Anti-Aliasing", ""),
            ('FXAA', "1 Sample", ""),
            ('5', "5 Samples", ""),
            ('8', "8 Samples", ""),
            ('11', "11 Samples", ""),
            ('16', "16 Samples", ""),
            ('32', "32 Samples", "")
        ),
        default="16",
        name="Workbench Samples"
    )
    samples_cycles: IntProperty(
        name="Cycles Samples", default=32, min=1, soft_max=1024
    )
    engine: EnumProperty( # NOTE: Add property to all subclasses
        items=SUPPORTED_ENGINES,
        name='Render Engine',
        update=update_engine
    )


class GRABDOC_normals(GRABDOC_baker_defaults, PropertyGroup):
    NAME = "normals"
    ALIAS = NAME.capitalize()
    SUPPORTED_ENGINES = (
        ('blender_eevee', "Eevee",     ""),
        ('cycles',        "Cycles",    "")
    )

    def update_flip_y(self, _context: Context):
        vec_multiply = \
            bpy.data.node_groups[Global.NORMAL_NG_NAME].nodes.get('Vector Math')
        vec_multiply.inputs[1].default_value[1] = -.5 if self.flip_y else .5

    def update_use_texture_normals(self, _context: Context) -> None:
        if not self.preview_state:
            return
        tree = bpy.data.node_groups[Global.NORMAL_NG_NAME]
        vec_transform = tree.nodes.get('Vector Transform')
        group_output = tree.nodes.get('Group Output')

        links = tree.links
        if self.use_texture:
            links.new(
                vec_transform.inputs["Vector"],
                tree.nodes.get('Bevel').outputs["Normal"]
            )
            links.new(
                group_output.inputs["Shader"],
                tree.nodes.get('Mix Shader').outputs["Shader"]
            )
        else:
            links.new(
                vec_transform.inputs["Vector"],
                tree.nodes.get('Bevel.001').outputs["Normal"]
            )
            links.new(
                group_output.inputs["Shader"],
                tree.nodes.get('Vector Math.001').outputs["Vector"]
            )

    flip_y: BoolProperty(
        name="Flip Y (-Y)",
        description="Flip the normal map Y direction",
        options={'SKIP_SAVE'},
        update=update_flip_y
    )
    use_texture: BoolProperty(
        name="Use Texture Normals",
        description="Use texture normals linked to the Principled BSDF",
        options={'SKIP_SAVE'},
        default=True,
        update=update_use_texture_normals
    )
    engine: EnumProperty(
        items=SUPPORTED_ENGINES,
        name='Render Engine',
        update=GRABDOC_baker_defaults.update_engine
    )


class GRABDOC_curvature(GRABDOC_baker_defaults, PropertyGroup):
    NAME = "curvature"
    ALIAS = NAME.capitalize()
    SUPPORTED_ENGINES = (
        ('workbench',     "Workbench", ""),
    )

    def update_curvature(self, context: Context):
        if not self.preview_state:
            return
        scene_shading = \
            bpy.data.scenes[str(context.scene.name)].display.shading
        scene_shading.cavity_ridge_factor = \
        scene_shading.curvature_ridge_factor = self.ridge
        scene_shading.curvature_valley_factor = self.valley

    ridge: FloatProperty(
        name="",
        default=2,
        min=0,
        max=2,
        precision=3,
        step=.1,
        update=update_curvature,
        subtype='FACTOR'
    )
    valley: FloatProperty(
        name="",
        default=1.5,
        min=0,
        max=2,
        precision=3,
        step=.1,
        update=update_curvature,
        subtype='FACTOR'
    )
    engine: EnumProperty(
        items=SUPPORTED_ENGINES,
        name='Render Engine',
        update=GRABDOC_baker_defaults.update_engine
    )


class GRABDOC_occlusion(GRABDOC_baker_defaults, PropertyGroup):
    NAME = "occlusion"
    ALIAS = "Ambient Occlusion"
    SUPPORTED_ENGINES = (
        ('blender_eevee', "Eevee",     ""),
        ('cycles',        "Cycles",    "")
    )

    def update_gamma(self, _context: Context):
        gamma = bpy.data.node_groups[Global.AO_NG_NAME].nodes.get('Gamma')
        gamma.inputs[1].default_value = self.gamma

    def update_distance(self, _context: Context):
        ao = bpy.data.node_groups[Global.AO_NG_NAME].nodes.get(
            'Ambient Occlusion')
        ao.inputs[1].default_value = self.distance

    gamma: FloatProperty(
        default=1,
        min=.001,
        soft_max=10,
        step=.17,
        name="",
        description="Intensity of AO (calculated with gamma)",
        update=update_gamma
    )
    distance: FloatProperty(
        default=1,
        min=0,
        soft_max=100,
        step=.03,
        subtype='DISTANCE',
        name="",
        description="The distance AO rays travel",
        update=update_distance
    )
    engine: EnumProperty(
        items=SUPPORTED_ENGINES,
        name='Render Engine',
        update=GRABDOC_baker_defaults.update_engine
    )


class GRABDOC_height(GRABDOC_baker_defaults, PropertyGroup):
    NAME = "height"
    ALIAS = NAME.capitalize()
    SUPPORTED_ENGINES = (
        ('blender_eevee', "Eevee",     ""),
        ('cycles',        "Cycles",    "")
    )

    def update_method(self, context: Context):
        scene_setup(self, context)
        if not self.preview_state:
            return
        bpy.data.objects[Global.BG_PLANE_NAME].active_material = \
            bpy.data.materials[Global.GD_MATERIAL_NAME]
        if self.method == 'AUTO':
            rendered_obs = get_rendered_objects()
            set_guide_height(rendered_obs)

    def update_guide(self, context: Context):
        gd_camera_ob_z = \
            bpy.data.objects.get(Global.TRIM_CAMERA_NAME).location[2]

        map_range = \
            bpy.data.node_groups[Global.HEIGHT_NG_NAME].nodes.get('Map Range')
        map_range.inputs[1].default_value = \
            gd_camera_ob_z + -self.distance
        map_range.inputs[2].default_value = \
            gd_camera_ob_z

        ramp = bpy.data.node_groups[Global.HEIGHT_NG_NAME].nodes.get(
            'ColorRamp')
        ramp.color_ramp.elements[0].color = \
            (0, 0, 0, 1) if self.invert else (1, 1, 1, 1)
        ramp.color_ramp.elements[1].color = \
            (1, 1, 1, 1) if self.invert else (0, 0, 0, 1)
        ramp.location = \
            (-400, 0)

        if self.method == 'MANUAL':
            scene_setup(self, context)

        # Update here so that it refreshes live in the VP
        if not self.preview_state:
            return
        bpy.data.objects[Global.BG_PLANE_NAME].active_material = \
            bpy.data.materials[Global.GD_MATERIAL_NAME]

    invert: BoolProperty(
        description="Invert height mask, useful for sculpting negatively",
        update=update_guide
    )
    distance: FloatProperty(
        name="",
        default=1,
        min=.01,
        soft_max=100,
        step=.03,
        subtype='DISTANCE',
        update=update_guide
    )
    method: EnumProperty(
        items=(
            ('AUTO', "Auto", ""),
            ('MANUAL', "Manual", "")
        ),
        update=update_method,
        description="Height method, use manual if auto produces range errors"
    )
    engine: EnumProperty(
        items=SUPPORTED_ENGINES,
        name='Render Engine',
        update=GRABDOC_baker_defaults.update_engine
    )


class GRABDOC_alpha(GRABDOC_baker_defaults, PropertyGroup):
    NAME = "alpha"
    ALIAS = NAME.capitalize()
    SUPPORTED_ENGINES = (
        ('blender_eevee', "Eevee",     ""),
        ('cycles',        "Cycles",    "")
    )

    def update_alpha(self, _context: Context):
        gd_camera_ob_z = bpy.data.objects.get(
            Global.TRIM_CAMERA_NAME
        ).location[2]
        map_range = \
            bpy.data.node_groups[Global.ALPHA_NG_NAME].nodes.get('Map Range')
        map_range.inputs[1].default_value = gd_camera_ob_z - .00001
        map_range.inputs[2].default_value = gd_camera_ob_z
        invert = \
            bpy.data.node_groups[Global.ALPHA_NG_NAME].nodes.get('Invert')
        invert.inputs[0].default_value = 0 if self.invert else 1

        # NOTE: Update here so that it refreshes live in the VP
        if self.preview_state:
            bpy.data.objects[Global.BG_PLANE_NAME].active_material = \
                bpy.data.materials[Global.GD_MATERIAL_NAME]

    invert: BoolProperty(
        description="Invert the Alpha mask",
        update=update_alpha
    )
    engine: EnumProperty(
        items=SUPPORTED_ENGINES,
        name='Render Engine',
        update=GRABDOC_baker_defaults.update_engine
    )


class GRABDOC_id(GRABDOC_baker_defaults, PropertyGroup):
    NAME = "id"
    ALIAS = "Material ID"
    SUPPORTED_ENGINES = (
        ('workbench',     "Workbench", ""),
    )

    method_list = (
        ('RANDOM', "Random", ""),
        ('MATERIAL', "Material", ""),
        ('VERTEX', "Object / Vertex", "")
    )
    method: EnumProperty(
        items=method_list,
        name=f"{ALIAS} Method"
    )
    ui_method: EnumProperty(
        items=method_list,
        default="MATERIAL"
    )
    engine: EnumProperty(
        items=SUPPORTED_ENGINES,
        name='Render Engine',
        update=GRABDOC_baker_defaults.update_engine
    )


class GRABDOC_color(GRABDOC_baker_defaults, PropertyGroup):
    NAME = "color"
    ALIAS = "Base Color"
    MARMOSET_COMPATIBLE = False
    SUPPORTED_ENGINES = (
        ('blender_eevee', "Eevee",     ""),
        ('cycles',        "Cycles",    "")
    )

    engine: EnumProperty(
        items=SUPPORTED_ENGINES,
        name='Render Engine',
        update=GRABDOC_baker_defaults.update_engine
    )


class GRABDOC_roughness(GRABDOC_baker_defaults, PropertyGroup):
    NAME = "roughness"
    ALIAS = NAME.capitalize()
    MARMOSET_COMPATIBLE = False
    SUPPORTED_ENGINES = (
        ('blender_eevee', "Eevee",     ""),
        ('cycles',        "Cycles",    "")
    )

    def update_roughness(self, _context: Context):
        invert = \
            bpy.data.node_groups[Global.ROUGHNESS_NG_NAME].nodes.get('Invert')
        invert.inputs[0].default_value = 1 if self.invert else 0

        # Update here so that it refreshes live in the VP
        # if self.preview_state:
        #    bpy.data.objects[BG_PLANE_NAME].active_material = \
        #       bpy.data.materials[GD_MATERIAL_NAME]

    invert: BoolProperty(
        description="Invert the Roughness (AKA Glossiness)",
        update=update_roughness
    )
    engine: EnumProperty(
        items=SUPPORTED_ENGINES,
        name='Render Engine',
        update=GRABDOC_baker_defaults.update_engine
    )



class GRABDOC_metalness(GRABDOC_baker_defaults, PropertyGroup):
    NAME = "metalness"
    ALIAS = NAME.capitalize()
    MARMOSET_COMPATIBLE = False
    SUPPORTED_ENGINES = (
        ('blender_eevee', "Eevee",     ""),
        ('cycles',        "Cycles",    "")
    )

    engine: EnumProperty(
        items=SUPPORTED_ENGINES,
        name='Render Engine',
        update=GRABDOC_baker_defaults.update_engine
    )

class GRABDOC_property_group(PropertyGroup):
    MAP_TYPES = (
        ('none',      "None",              ""),
        ('normals',   "Normals",           ""),
        ('curvature', "Curvature",         ""),
        ('occlusion', "Ambient Occlusion", ""),
        ('height',    "Height",            ""),
        ('id',        "Material ID",       ""),
        ('alpha',     "Alpha",             ""),
        ('color',     "Base Color",        ""),
        ('roughness', "Roughness",         ""),
        ('metalness', "Metalness",         "")
    )

    def update_export_name(self, _context: Context):
        if not self.export_name:
            self.export_name = "untitled"

    def update_export_path(self, _context: Context):
        export_path_exists = \
            os.path.exists(bpy.path.abspath(self.export_path))
        if self.export_path != '' and not export_path_exists:
            self.export_path = ''

    def update_res_x(self, context: Context):
        if self.lock_res and self.export_res_x != self.export_res_y:
            self.export_res_y = self.export_res_x
        scene_setup(self, context)

    def update_res_y(self, context: Context):
        if self.lock_res and self.export_res_y != self.export_res_x:
            self.export_res_x = self.export_res_y
        scene_setup(self, context)

    def update_scale(self, context: Context):
        scene_setup(self, context)

        gd_camera_ob_z = bpy.data.objects.get(
            Global.TRIM_CAMERA_NAME
        ).location[2]
        height_ng = bpy.data.node_groups.get(Global.HEIGHT_NG_NAME)

        map_range = height_ng.nodes.get('Map Range')
        map_range.inputs[1].default_value = \
            - self.height[0].distance + gd_camera_ob_z
        map_range.inputs[2].default_value = gd_camera_ob_z

        map_range_alpha = \
            bpy.data.node_groups[Global.ALPHA_NG_NAME].nodes.get('Map Range')
        map_range_alpha.inputs[1].default_value = gd_camera_ob_z - .00001
        map_range_alpha.inputs[2].default_value = gd_camera_ob_z

    # Project Setup
    coll_selectable: BoolProperty(
        update=scene_setup,
        description="Sets the background plane selection capability"
    )
    coll_visible: BoolProperty(default=True, update=scene_setup,
                              description="Sets the visibility in the viewport")
    coll_rendered: BoolProperty(
        default=True,
        update=scene_setup,
        description=\
            "Sets the visibility in exports, this will also enable transparency and alpha channel exports if visibility is turned off"
    )

    scale: FloatProperty(
        name="Scale",
        default=2,
        min=.1,
        soft_max=100,
        precision=3,
        subtype='DISTANCE',
        description=\
            "Background plane & camera scale, also applies to exported plane",
        update=update_scale
    )
    filter: BoolProperty(  # TODO: add to cycles
        name='Use Filtering',
        default=True,
        description=\
            "Pixel filtering, useful for avoiding aliased edges on bake maps",
        update=scene_setup
    )
    filter_width: FloatProperty(
        name="Filter Amount",
        default=1.2,
        min=0,
        soft_max=10,
        subtype='PIXEL',
        description="The width in pixels used for filtering",
        update=scene_setup
    )

    reference: PointerProperty(
        name='Reference Selection',
        type=Image,
        description="Select an image reference to use on the background plane",
        update=scene_setup
    )
    use_grid: BoolProperty(
        name='Use Grid',
        default=True,
        description=\
            "Wireframe grid on plane for better snapping usability",
        update=scene_setup
    )
    grid_subdivs: IntProperty(
        name="Grid Subdivisions",
        default=0,
        min=0,
        soft_max=64,
        description="Subdivision count for grid",
        update=scene_setup
    )

    # Baker
    baker_type: EnumProperty(
        items=(
            ('Blender', "Blender", "Set Baker: Blender"),
            ('Marmoset', "Toolbag", "Set Baker: Marmoset Toolbag")
        ),
        name="Baker"
    )
    export_path: StringProperty(
        name="Export Filepath",
        default=" ",
        description="This is the path all files will be exported to",
        subtype='DIR_PATH',
        update=update_export_path
    )
    export_res_x: IntProperty(
        name="Res X",
        default=2048,
        min=4, soft_max=8192,
        update=update_res_x
    )
    export_res_y: IntProperty(
        name="Res Y",
        default=2048,
        min=4, soft_max=8192,
        update=update_res_y
    )
    lock_res: BoolProperty(
        name='Sync Resolution',
        default=True,
        update=update_res_x
    )
    export_name: StringProperty(
        name="",
        description="Prefix name used for exported maps",
        default="untitled",
        update=update_export_name
    )
    use_bake_collections: BoolProperty(
        description="Add a collection to the scene for use as bake groups",
        update=scene_setup
    )
    export_plane: BoolProperty(
        description="Export the background plane as an unwrapped FBX"
    )

    # Image Formats
    format: EnumProperty(
        items=(
            ('PNG', "PNG", ""),
            ('TIFF', "TIFF", ""),
            ('TARGA', "TGA", ""),
            ('OPEN_EXR', "EXR", "")
        ),
        name="Format"
    )
    depth: EnumProperty(
        items=(
            ('16', "16", ""),
            ('8', "8", "")
        )
    )
    # NOTE: Wrapper property so we can assign a new default
    png_compression: IntProperty(
        name="",
        default=50,
        min=0,
        max=100,
        description=\
            "Lossless compression for lower file size but longer bake times",
        subtype='PERCENTAGE'
    )
    exr_depth: EnumProperty(
        items=(
            ('16', "16", ""),
            ('32', "32", "")
        )
    )
    tga_depth: EnumProperty(
        items=(
            ('16', "16", ""),
            ('8', "8", "")
        ),
        default='8'
    )

    # Map preview
    preview_first_time: BoolProperty(default=True)
    preview_auto_exit_camera: BoolProperty(
        description=\
            "Automatically leave camera view when exiting a Map Preview"
    )
    preview_state: BoolProperty()
    preview_type: EnumProperty(items=MAP_TYPES)

    # Baking
    normals: CollectionProperty(type=GRABDOC_normals)
    curvature: CollectionProperty(type=GRABDOC_curvature)
    occlusion: CollectionProperty(type=GRABDOC_occlusion)
    height: CollectionProperty(type=GRABDOC_height)
    id: CollectionProperty(type=GRABDOC_id)
    alpha: CollectionProperty(type=GRABDOC_alpha)
    color: CollectionProperty(type=GRABDOC_color)
    roughness: CollectionProperty(type=GRABDOC_roughness)
    metalness: CollectionProperty(type=GRABDOC_metalness)

    # Marmoset baking
    marmoset_auto_bake: BoolProperty(name="Auto bake", default=True)
    marmoset_auto_close: BoolProperty(name="Close after baking")
    marmoset_samples: EnumProperty(
        items=(
            ('1', "1x", ""),
            ('4', "4x", ""),
            ('16', "16x", ""),
            ('64', "64x", "")
        ),
        default="16",
        name="Marmoset Samples",
        description=\
            "Samples rendered per pixel. 64 samples is not supported in Marmoset 3 (defaults to 16 samples)"
    )
    marmoset_occlusion_ray_count: IntProperty(
        default=512,
        min=32,
        soft_max=4096
    )
    marmoset_format: EnumProperty(
        items=(
            ('PNG', "PNG", ""),
            ('PSD', "PSD", "")
        ),
        name="Format"
    )

    # Channel packing
    # TODO:
    # - Implement core functionality
    # - Add all properties to presets
    #use_pack_maps: BoolProperty(
    #    name='Enable Packing on Export',
    #    default=False
    #)
    #channel_R: EnumProperty(
    #    items=MAP_TYPES,
    #    default="occlusion",
    #    name='R'
    #)
    #channel_G: EnumProperty(
    #    items=MAP_TYPES,
    #    default="roughness",
    #    name='G'
    #)
    #channel_B: EnumProperty(
    #    items=MAP_TYPES,
    #    default="metalness",
    #    name='B'
    #)
    #channel_A: EnumProperty(
    #    items=MAP_TYPES,
    #    default="alpha",
    #    name='A'
    #)


##################################
# REGISTRATION
##################################


classes = (
    GRABDOC_MT_presets,
    GRABDOC_PT_presets,
    GRABDOC_OT_add_preset,
    GRABDOC_normals,
    GRABDOC_curvature,
    GRABDOC_occlusion,
    GRABDOC_height,
    GRABDOC_id,
    GRABDOC_alpha,
    GRABDOC_color,
    GRABDOC_roughness,
    GRABDOC_metalness,
    GRABDOC_property_group,
    GRABDOC_MT_addon_preferences,
    GRABDOC_OT_check_for_update
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    Scene.gd = PointerProperty(type=GRABDOC_property_group)
    Collection.gd_bake_collection = BoolProperty(default=False)
    Object.gd_object = BoolProperty(default=False)

    # Git release tracking
    updater.user = "oRazeD"
    updater.repo = "grabdoc"
    updater.current_version = VERSION
    updater.check_for_update_now()
    if updater.update_ready:
        print("GrabDoc update available!")


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
