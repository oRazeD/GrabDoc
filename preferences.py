
import os

import bpy
from bl_operators.presets import AddPresetBase
from bl_ui.utils import PresetPanel
from bpy.types import (
    Menu, Panel, Operator, AddonPreferences,
    Context, PropertyGroup, Image, Scene,
    Collection, Object, Node
)
from bpy.props import (
    BoolProperty, PointerProperty, CollectionProperty,
    StringProperty, EnumProperty, IntProperty, FloatProperty
)

from .baker import Baker
from .utils.scene import scene_setup


class GRABDOC_AP_preferences(AddonPreferences):
    bl_idname = __package__

    mt_executable: StringProperty(
        description="Path to Marmoset Toolbag 3 / 4 executable",
        name="Marmoset EXE Path", default="", subtype="FILE_PATH"
    )
    render_within_frustrum: BoolProperty(
        description=\
"""Only render objects within the camera's viewing frustrum.

Improves render speed but it may apply materials incorrectly (void objects)""",
        name="Render Within Frustrum", default=False
    )
    exit_camera_preview: BoolProperty(
        description="Exit the camera when leaving Map Preview",
        name="Auto-exit Preview Camera", default=False
    )
    disable_preview_binds: BoolProperty(
        description=\
"""By default, pressing escape while in Map Preview automatically exits preview.

This can get in the way of other modal operators, causing some friction""",
        name="Disable Keybinds in Preview", default=False
    )

    def draw(self, _context: Context):
        for prop in self.__annotations__.keys():
            self.layout.prop(self, prop)


class GRABDOC_PG_properties(PropertyGroup):
    def update_filename(self, _context: Context):
        if not self.filename:
            self.filename = "untitled"

    def update_filepath(self, _context: Context):
        if self.filepath == '//':
            return
        if not os.path.exists(self.filepath):
            self.filepath = '//'

    def update_res_x(self, context: Context):
        if self.resolution_lock and self.resolution_x != self.resolution_y:
            self.resolution_y = self.resolution_x
        scene_setup(self, context)

    def update_res_y(self, context: Context):
        if self.resolution_lock and self.resolution_y != self.resolution_x:
            self.resolution_x = self.resolution_y
        scene_setup(self, context)

    def update_scale(self, context: Context):
        scene_setup(self, context)

    # Scene
    coll_selectable: BoolProperty(
        description="Sets the background plane selection capability",
        update=scene_setup
    )
    coll_visible: BoolProperty(default=True, update=scene_setup,
                              description="Sets the visibility in the viewport")
    coll_rendered: BoolProperty(
        description=\
"""Sets visibility of background plane in exports.

Enables transparency and alpha channel if disabled""",
        default=True, update=scene_setup
    )

    scale: FloatProperty(
        description="Background plane and camera; applied to exported plane",
        name="Scale", update=scene_setup,
        default=2, min=.1, soft_max=100, precision=3, subtype='DISTANCE'
    )
    use_filtering: BoolProperty(
        description=\
"""Blurs sharp edge shapes to reduce harsh, aliased edges.

When disabled, pixel filtering is reduced to .01px""",
        name='', default=True, update=scene_setup
    )
    filter_width: FloatProperty(
        description="The width in pixels used for filtering",
        name="Filter Amount", update=scene_setup,
        default=1.2, min=0, soft_max=10, subtype='PIXEL'
    )
    use_grid: BoolProperty(
        description="Wireframe grid on plane for better snapping usability",
        name='Use Grid', default=False, update=scene_setup
    )
    grid_subdivs: IntProperty(
        description="Subdivision count for the background plane's grid",
        name="Grid Subdivisions", update=scene_setup,
        default=2, min=0, soft_max=64
    )
    reference: PointerProperty(
        description="Select an image reference to use on the background plane",
        name='Reference Selection', type=Image, update=scene_setup
    )

    # Output
    engine: EnumProperty(
        description="The baking engine you would like to use",
        name="Engine",
        items=(('grabdoc', "GrabDoc", "Set Baker: GrabDoc (Blender)"),
               ('marmoset', "Toolbag", "Set Baker: Marmoset Toolbag"))
    )
    filepath: StringProperty(
        description="The path all textures will be exported to",
        name="Export Filepath", default="//", subtype='DIR_PATH',
        update=update_filepath
    )
    filename: StringProperty(
        description="Prefix name used for exported maps",
        name="", default="untitled", update=update_filename
    )
    resolution_x: IntProperty(name="X Resolution", update=update_res_x,
                              default=2048, min=4, soft_max=8192)
    resolution_y: IntProperty(name="Y Resolution", update=update_res_y,
                              default=2048, min=4, soft_max=8192)
    resolution_lock: BoolProperty(name='Lock Resolution',
                                  default=True, update=update_res_x)
    format: EnumProperty(name="Format",
                         items=(('PNG',      "PNG",  ""),
                                ('TIFF',     "TIFF", ""),
                                ('TARGA',    "TGA",  ""),
                                ('OPEN_EXR', "EXR",  "")))
    depth:     EnumProperty(items=(('16', "16", ""),
                                   ('8',  "8",  "")))
    exr_depth: EnumProperty(items=(('16', "16", ""),
                                   ('32', "32", "")))
    tga_depth: EnumProperty(items=(('8',  "8",  ""),
                                   ('16', "16", "")))
    png_compression: IntProperty(
        description="Lossless compression; lower file size, longer bake times",
        name="", default=50, min=0, max=100, subtype='PERCENTAGE'
    )
    use_bake_collection: BoolProperty(
        description="Add a collection to the scene for use as bake groups",
        update=scene_setup
    )

    # Bake maps
    MAP_TYPES = [('none', "None", "")]
    baker_props = {}
    for baker in Baker.__subclasses__():
        baker_props[baker.ID] = CollectionProperty(type=baker, name=baker.NAME)
        MAP_TYPES.append((baker.ID, baker.NAME, ""))
    __annotations__.update(baker_props)  # pylint: disable=E0602

    # Map preview
    preview_map_type: EnumProperty(items=MAP_TYPES)
    preview_index:    IntProperty()
    preview_state:    BoolProperty(
        description="Flags if the user is currently in Map Preview"
    )

    # Marmoset
    mt_auto_bake: BoolProperty(name="Auto bake", default=True)
    mt_auto_close: BoolProperty(name="Close after baking")
    mt_samples: EnumProperty(
        description=\
        "Samples rendered per pixel. 64x not supported in MT3 (defaults to 16)",
        items=(('1',  "1x",  ""),
               ('4',  "4x",  ""),
               ('16', "16x", ""),
               ('64', "64x", "")),
        default="16", name="Marmoset Samples"
    )
    mt_occlusion_samples: IntProperty(default=512, min=32, soft_max=4096)
    mt_format: EnumProperty(
        items=(('PNG', "PNG", ""),
               ('PSD', "PSD", "")),
        name="Format"
    )

    # Pack maps
    use_pack_maps: BoolProperty(
        description="Pack textures using the selected channels after exporting",
        name="Pack on Export", default=False
    )
    remove_original_maps: BoolProperty(
        description="Remove the original unpacked maps after exporting",
        name="Remove Original", default=False
    )
    pack_name: StringProperty(name="Packed Map Name", default="ORM")
    channel_r: EnumProperty(items=MAP_TYPES[1:], default="occlusion", name='R')
    channel_g: EnumProperty(items=MAP_TYPES[1:], default="roughness", name='G')
    channel_b: EnumProperty(items=MAP_TYPES[1:], default="metallic",  name='B')
    channel_a: EnumProperty(items=MAP_TYPES,     default="none",      name='A')


################################################
# PRESETS
################################################


class GRABDOC_MT_presets(Menu):
    bl_label        = ""
    preset_subdir   = "gd"
    preset_operator = "script.execute_preset"
    draw            = Menu.draw_preset


class GRABDOC_PT_presets(PresetPanel, Panel):
    bl_label            = 'Bake Presets'
    preset_subdir       = 'grab_doc'
    preset_operator     = 'script.execute_preset'
    preset_add_operator = 'grab_doc.preset_add'


class GRABDOC_OT_add_preset(AddPresetBase, Operator):
    bl_idname   = "grab_doc.preset_add"
    bl_label    = "Add a new preset"
    preset_menu = "GRABDOC_MT_presets"

    preset_subdir  = "grab_doc"
    preset_defines = ["gd=bpy.context.scene.gd"]
    preset_values  = []
    bakers         = [baker.ID for baker in Baker.__subclasses__()]
    for name in GRABDOC_PG_properties.__annotations__.keys():
        if name.startswith("preview_"):
            continue
        if name in bakers:
            preset_values.append(f"gd.{name}[0]")
            continue
        preset_values.append(f"gd.{name}")

    # TODO: Figure out a way to run register_baker_panels
    #       in order to support multi-baker presets
    #def execute(self, context: Context):
    #    super().execute(context)


##################################
# REGISTRATION
##################################


classes = [
    GRABDOC_AP_preferences,
    GRABDOC_MT_presets,
    GRABDOC_PT_presets,
    GRABDOC_OT_add_preset
]
# NOTE: Register properties last for collection generation
classes.extend([*Baker.__subclasses__(), GRABDOC_PG_properties])

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    Scene.gd                 = PointerProperty(type=GRABDOC_PG_properties)
    Node.gd_spawn            = BoolProperty()
    Object.gd_object         = BoolProperty()
    Collection.gd_collection = BoolProperty()

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
