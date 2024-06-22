
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

from .constants import Global
from .utils.scene import scene_setup
#from .utils.render import get_rendered_objects, set_guide_height
from .utils.baker import (
    Alpha,
    Color,
    Curvature,
    Height,
    Id,
    Metallic,
    Normals,
    Occlusion,
    Emissive,
    Roughness
)


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
        "gd.resolution_x",
        "gd.resolution_y",
        "gd.lock_res",
        "gd.format",
        "gd.depth",
        "gd.tga_depth",
        "gd.png_compression",

        "gd.use_bake_collections",
        "gd.export_plane",

        "gd.marmo_auto_bake",
        "gd.marmo_auto_close",
        "gd.marmo_samples",
        "gd.marmo_occlusion_ray_count",
        "gd.marmo_format",

        "gd.normals",
        "gd.curvature",
        "gd.occlusion",
        "gd.height",
        "gd.alpha",
        "gd.id",
        "gd.color",
        "gd.emissive",
        "gd.roughness",
        "gd.metallic",

        "gd.use_pack_maps",
        "gd.pack_name",
        "gd.channel_R",
        "gd.channel_G",
        "gd.channel_B",
        "gd.channel_A"
    ]

    # Where to store the preset
    preset_subdir = "grab_doc"


############################################################
# PROPERTY GROUP
############################################################


class GRABDOC_AP_preferences(AddonPreferences):
    bl_idname = __package__

    marmo_executable: StringProperty(
        name="",
        description="Path to Marmoset Toolbag 3 or 4 executable",
        default="",
        subtype="FILE_PATH"
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
        ('emissive',  "Emissive",          ""),
        ('roughness', "Roughness",         ""),
        ('metallic',  "Metallic",          "")
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
        if self.lock_res and self.resolution_x != self.resolution_y:
            self.resolution_y = self.resolution_x
        scene_setup(self, context)

    def update_res_y(self, context: Context):
        if self.lock_res and self.resolution_y != self.resolution_x:
            self.resolution_x = self.resolution_y
        scene_setup(self, context)

    def update_scale(self, context: Context):
        scene_setup(self, context)

        gd_camera_ob_z = bpy.data.objects.get(
            Global.TRIM_CAMERA_NAME
        ).location[2]
        height_ng = bpy.data.node_groups.get(Global.HEIGHT_NODE)

        map_range = height_ng.nodes.get('Map Range')
        map_range.inputs[1].default_value = \
            - self.height[0].distance + gd_camera_ob_z
        map_range.inputs[2].default_value = gd_camera_ob_z

        map_range_alpha = \
            bpy.data.node_groups[Global.ALPHA_NODE].nodes.get('Map Range')
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
            ('blender', "Blender", "Set Baker: Blender"),
            ('marmoset', "Toolbag", "Set Baker: Marmoset Toolbag")
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
    resolution_x: IntProperty(
        name="Res X",
        default=2048,
        min=4, soft_max=8192,
        update=update_res_x
    )
    resolution_y: IntProperty(
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
    # NOTE: The modal system relies on this
    # particular switch to control UI States
    preview_state: BoolProperty()
    preview_type: EnumProperty(items=MAP_TYPES)

    # Baking
    normals: CollectionProperty(type=Normals)
    curvature: CollectionProperty(type=Curvature)
    occlusion: CollectionProperty(type=Occlusion)
    height: CollectionProperty(type=Height)
    id: CollectionProperty(type=Id)
    alpha: CollectionProperty(type=Alpha)
    color: CollectionProperty(type=Color)
    emissive: CollectionProperty(type=Emissive)
    roughness: CollectionProperty(type=Roughness)
    metallic: CollectionProperty(type=Metallic)

    # Marmoset baking
    marmo_auto_bake: BoolProperty(name="Auto bake", default=True)
    marmo_auto_close: BoolProperty(name="Close after baking")
    marmo_samples: EnumProperty(
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
    marmo_occlusion_ray_count: IntProperty(
        default=512,
        min=32,
        soft_max=4096
    )
    marmo_format: EnumProperty(
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
    use_pack_maps: BoolProperty(
       name='Enable Packing on Export',
       default=False
    )

    pack_name : StringProperty (
        name= 'Pack map name',
        default= 'AORM')

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
       default="metallic",
       name='B'
    )
    channel_A: EnumProperty(
       items=MAP_TYPES,
       default="none",
       name='A'
    )
    


##################################
# REGISTRATION
##################################


classes = (
    GRABDOC_MT_presets,
    GRABDOC_PT_presets,
    GRABDOC_OT_add_preset,
    Normals,
    Curvature,
    Occlusion,
    Height,
    Id,
    Alpha,
    Color,
    Emissive,
    Roughness,
    Metallic,
    GRABDOC_property_group,
    GRABDOC_AP_preferences
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    Scene.gd = PointerProperty(type=GRABDOC_property_group)
    Collection.gd_bake_collection = BoolProperty(default=False)
    Object.gd_object = BoolProperty(default=False)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
