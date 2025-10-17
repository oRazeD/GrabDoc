import bpy
from bpy.types import PropertyGroup, UILayout, Context, NodeTree
from bpy.props import (
    BoolProperty, StringProperty, EnumProperty,
    IntProperty, FloatProperty, PointerProperty,
    CollectionProperty
)

from .constants import Global
from .utils.scene import scene_setup
from .utils.node import (
    generate_shader_interface, get_group_inputs, get_material_output_sockets
)
from .utils.render import (
    set_guide_height, get_rendered_objects, set_color_management
)


class Baker(PropertyGroup):
    """A Blender shader and render settings automation system with
    efficient setup and clean up of desired render targets non-destructively.

    This system is designed for rapid development of new
    bake map types with minimal unique implementation.

    The most minimal examples of subclasses require the following:
    - Core shader properties (e.g. ID, Name, etc.)
    - BPY code for re-creating the desired shader / node group"""
    ID:                         str = ''
    NAME:                       str = ID.capitalize()
    VIEW_TRANSFORM:             str = 'Standard'
    MARMOSET_COMPATIBLE:       bool = True
    REQUIRED_SOCKETS:    tuple[str] = ()
    OPTIONAL_SOCKETS:    tuple[str] = ('Alpha',)
    SUPPORTED_ENGINES               = ((Global.EEVEE_ENGINE_NAME, "EEVEE", ""),
                                       ('cycles', "Cycles", ""),
                                       ('blender_workbench', "Workbench", ""))

    def initialize(self):
        """Initialize baker instance after creation in PropertyCollection."""
        self.node_input  = None
        self.node_output = None
        # NOTE: Unique due to dynamic SUPPORTED_ENGINES enum
        self.__class__.engine = EnumProperty(
            name='Render Engine',
            items=self.__class__.SUPPORTED_ENGINES,
            update=self.__class__.apply_render_settings
        )

        self.suffix = self.ID
        if len(self.REQUIRED_SOCKETS) > 0 or self.ID == 'custom':
            self.enabled = False

        if self.index == -1:
            try:
                gd = bpy.context.scene.gd
                self.index = self.get_unique_index(getattr(gd, self.ID))
            except (AttributeError, RuntimeError):
                # Handle cases where context or gd is not available
                self.index = 0
        if self.index > 0:
            self.node_name = self.get_node_name(self.NAME, self.index+1)
            if hasattr(self, 'suffix') and self.suffix \
            and not self.suffix[-1].isdigit():
                self.suffix = f"{self.suffix}_{self.index+1}"

    @staticmethod
    def get_unique_index(collection: CollectionProperty) -> int:
        """Get a unique index value based on a given `CollectionProperty`."""
        indices = [baker.index for baker in collection]
        index   = 0
        while True:
            if index not in indices:
                break
            index += 1
        return index

    @staticmethod
    def get_node_name(name: str, idx: int=0):
        """Set node name based on given base `name` and optional `idx`."""
        node_name = Global.FLAG_PREFIX + name.replace(" ", "")
        if idx:
            node_name += f"_{idx}"
        return node_name

    def get_display_name(self) -> str:
        baker_name = self.NAME
        if self.index > 0:
            baker_name += f" {self.index+1}"
        return baker_name

    def setup(self):
        """General operations to run before bake export."""
        self.apply_render_settings(requires_preview=False)

    def node_setup(self):
        """Shader logic to generate a node group.

        Base method logic gets/creates a new group with
        valid sockets and adds I/O nodes to the tree."""
        if not self.node_name:
            self.node_name = self.get_node_name(self.NAME)
        self.node_tree = bpy.data.node_groups.get(self.node_name)
        if self.node_tree is None:
            self.node_tree = \
                bpy.data.node_groups.new(self.node_name, 'ShaderNodeTree')
            # NOTE: Default alpha socket for pre-built bakers
            self.node_tree.interface.new_socket(
                name='Alpha', socket_type='NodeSocketFloat'
            ).default_value = 1

        self.node_tree.use_fake_user = True
        self.node_input = self.node_tree.nodes.new('NodeGroupInput')
        self.node_input.location = (-1500, 0)
        self.node_output = self.node_tree.nodes.new('NodeGroupOutput')
        generate_shader_interface(self.node_tree, get_material_output_sockets())

    def reimport_setup(self, material, image):
        """Shader logic to link an imported image texture a generic BSDF."""
        links = material.node_tree.links
        bsdf  = material.node_tree.nodes['Principled BSDF']
        try:
            links.new(bsdf.inputs[self.ID.capitalize()], image.outputs["Color"])
        except KeyError:
            pass

    def cleanup(self):
        """Operations to revert unique scene modifications after bake export."""

    def apply_render_settings(self, requires_preview: bool=True) -> None:
        """Apply global baker render and color management settings."""
        if requires_preview and not bpy.context.scene.gd.preview_state:
            return

        scene  = bpy.context.scene
        render = scene.render
        cycles = scene.cycles
        if scene.gd.use_filtering and not self.disable_filtering:
            render.filter_size = cycles.filter_width = scene.gd.filter_width
        else:
            render.filter_size = cycles.filter_width = .01

        eevee   = scene.eevee
        display = scene.display
        render.engine = str(self.engine).upper()
        if render.engine == Global.EEVEE_ENGINE_NAME.upper():
            eevee.taa_render_samples = eevee.taa_samples = self.samples
        elif render.engine == 'CYCLES':
            cycles.samples = cycles.preview_samples = self.samples_cycles
        elif render.engine == 'BLENDER_WORKBENCH':
            display.render_aa = display.viewport_aa = self.samples_workbench

        set_color_management(self.VIEW_TRANSFORM,
                             self.contrast.replace('_', ' '))

    def filter_required_sockets(self, sockets: list[str]) -> str:
        """Filter out optional sockets from a list of socket names."""
        required_sockets = []
        for socket in sockets:
            if socket in self.REQUIRED_SOCKETS:
                required_sockets.append(socket)
        return ", ".join(required_sockets)

    def draw_properties(self, context: Context, layout: UILayout):
        """Dedicated layout for specific bake map properties."""

    def draw(self, context: Context, layout: UILayout):
        """Dropdown layout for bake map properties and operators."""
        layout.use_property_split    = True
        layout.use_property_decorate = False
        col = layout.column()

        box = col.box()
        box.label(text="Properties", icon='PROPERTIES')
        self.draw_properties(context, box)

        box = col.box()
        box.label(text="Settings", icon='SETTINGS')
        col_set = box.column()
        gd = context.scene.gd
        if gd.engine == 'grabdoc':
            row = col_set.row(align=True)
            if len(self.SUPPORTED_ENGINES) < 2:
                row.enabled = False
            row.prop(self, 'engine')
            col_set.prop(self, 'reimport')
            col_set.prop(self, 'disable_filtering')
            prop = 'samples'
            if self.engine == 'blender_workbench':
                prop = 'samples_workbench'
            elif self.engine == 'cycles':
                prop = 'samples_cycles'
            col_set.prop(self, prop, text='Samples')
            col_set.prop(self, 'contrast')
        col_set.prop(self, 'suffix')

        col_info = col.column(align=True)
        col_info.scale_y = .9
        if not self.MARMOSET_COMPATIBLE:
            box = col_info.box()
            col2 = box.column(align=True)
            col2.label(text="Marmoset not supported", icon='INFO')
        if self.node_tree and self.REQUIRED_SOCKETS:
            box = col_info.box()
            col2 = box.column(align=True)
            col2.label(text="Requires socket(s):", icon='WARNING_LARGE')
            row = col2.row(align=True)
            inputs_fmt = ", ".join(self.REQUIRED_SOCKETS)
            row.label(text=f"  {inputs_fmt}", icon='BLANK1')
        if self.node_tree and self.OPTIONAL_SOCKETS:
            box = col_info.box()
            col2 = box.column(align=True)
            col2.label(text="Supports socket(s):", icon='INFO')
            row = col2.row(align=True)
            inputs_fmt = ", ".join(self.OPTIONAL_SOCKETS)
            row.label(text=f"  {inputs_fmt}", icon='BLANK1')

    # NOTE: Internal properties
    index:     IntProperty(default=-1)
    node_name: StringProperty()
    node_tree: PointerProperty(type=NodeTree)

    # NOTE: Default properties
    suffix: StringProperty(
        description="The suffix of the exported bake map",
        name="Suffix", default=""
    )
    enabled: BoolProperty(
        name="Export Enabled", default=True
    )
    reimport: BoolProperty(
        description="Reimport bake map texture into a Blender material",
        name="Re-import"
    )
    visibility: BoolProperty(
        description="Toggle UI visibility of this bake map", default=True
    )
    disable_filtering: BoolProperty(
        description="Override global filtering setting and set filter to .01px",
        name="Override Filtering", default=False, update=apply_render_settings
    )
    samples: IntProperty(name="EEVEE Samples", update=apply_render_settings,
                         default=32, min=1, soft_max=256)
    samples_cycles: IntProperty(name="Cycles Samples",
                                update=apply_render_settings,
                                default=16, min=1, soft_max=256)
    samples_workbench: EnumProperty(
        items=(('OFF',  "No Anti-Aliasing", ""),
               ('FXAA', "1 Sample",         ""),
               ('5',    "5 Samples",        ""),
               ('8',    "8 Samples",        ""),
               ('11',   "11 Samples",       ""),
               ('16',   "16 Samples",       ""),
               ('32',   "32 Samples",       "")),
        name="Workbench Samples", default="8", update=apply_render_settings
    )
    contrast: EnumProperty(
        items=(('None',                 "Default", ""),
               ('Very_High_Contrast',   "Very High",     ""),
               ('High_Contrast',        "High",          ""),
               ('Medium_High_Contrast', "Medium High",   ""),
               ('Medium_Low_Contrast',  "Medium Low",    ""),
               ('Low_Contrast',         "Low",           ""),
               ('Very_Low_Contrast',    "Very Low",      "")),
        name="Contrast", update=apply_render_settings
    )


class Normals(Baker):
    ID                  = 'normals'
    NAME                = ID.capitalize()
    VIEW_TRANSFORM      = "Raw"
    MARMOSET_COMPATIBLE = True
    REQUIRED_SOCKETS    = ()
    OPTIONAL_SOCKETS    = ('Alpha', 'Normal')
    SUPPORTED_ENGINES   = Baker.SUPPORTED_ENGINES[:-1]

    def node_setup(self):
        super().node_setup()
        self.node_tree.interface.new_socket(
            name='Normal', socket_type='NodeSocketVector'
        )
        self.node_input.location = (-1400, -225)

        geometry = self.node_tree.nodes.new('ShaderNodeNewGeometry')
        geometry.location = (-1400, 0)

        vec_mix = self.node_tree.nodes.new('ShaderNodeMix')
        vec_mix.data_type = 'VECTOR'
        vec_mix.location = (-1200, 0)

        vec_sep = self.node_tree.nodes.new('ShaderNodeSeparateXYZ')
        vec_sep.location = (-1200, -200)

        vec_ceil = self.node_tree.nodes.new('ShaderNodeVectorMath')
        vec_ceil.operation = 'CEIL'
        vec_ceil.location = (-1200, -325)

        bevel = self.node_tree.nodes.new('ShaderNodeBevel')
        bevel.samples = 16
        bevel.inputs[0].default_value = 0
        bevel.location = (-1000, 0)

        vec_transform = self.node_tree.nodes.new('ShaderNodeVectorTransform')
        vec_transform.vector_type = 'NORMAL'
        vec_transform.convert_to  = 'CAMERA'
        vec_transform.location    = (-800, 0)

        vec_mult = self.node_tree.nodes.new('ShaderNodeVectorMath')
        vec_mult.operation = 'MULTIPLY'
        vec_mult.inputs[1].default_value[0] = .5
        vec_mult.inputs[1].default_value[1] = -.5 if self.flip_y else .5
        vec_mult.inputs[1].default_value[2] = -.5
        vec_mult.location = (-600, 0)

        vec_add = self.node_tree.nodes.new('ShaderNodeVectorMath')
        vec_add.inputs[1].default_value[0] = \
        vec_add.inputs[1].default_value[1] = \
        vec_add.inputs[1].default_value[2] = 0.5
        vec_add.location = (-400, 0)

        invert = self.node_tree.nodes.new('ShaderNodeInvert')
        invert.location = (-600, -300)

        subtract = self.node_tree.nodes.new('ShaderNodeMixRGB')
        subtract.blend_type = 'SUBTRACT'
        subtract.inputs[0].default_value = 1
        subtract.inputs[1].default_value = (1, 1, 1, 1)
        subtract.location = (-400, -300)

        transp_shader = self.node_tree.nodes.new('ShaderNodeBsdfTransparent')
        transp_shader.location = (-200, -125)

        mix_shader = self.node_tree.nodes.new('ShaderNodeMixShader')
        mix_shader.location = (-200, 0)

        links = self.node_tree.links
        links.new(vec_mix.inputs['Factor'], vec_sep.outputs['Z'])
        links.new(vec_mix.inputs['A'],      geometry.outputs['Normal'])
        links.new(vec_mix.inputs['B'],      self.node_input.outputs['Normal'])
        links.new(vec_sep.inputs[0],        vec_ceil.outputs[0])
        links.new(vec_ceil.inputs[0],       self.node_input.outputs['Normal'])

        links.new(bevel.inputs['Normal'],  vec_mix.outputs['Result'])
        links.new(vec_transform.inputs[0], bevel.outputs[0])
        links.new(vec_mult.inputs[0],      vec_transform.outputs[0])
        links.new(vec_add.inputs[0],       vec_mult.outputs[0])

        links.new(invert.inputs[1],   self.node_input.outputs['Alpha'])
        links.new(subtract.inputs[2], invert.outputs[0])

        links.new(mix_shader.inputs[0], subtract.outputs[0])
        links.new(mix_shader.inputs[1], transp_shader.outputs[0])
        links.new(mix_shader.inputs[2], vec_add.outputs[0])
        links.new(self.node_output.inputs['Shader'],
                  mix_shader.outputs['Shader'])

    def reimport_setup(self, material, image):
        bsdf   = material.node_tree.nodes['Principled BSDF']
        normal = material.node_tree.nodes.get('Normal Map')
        if normal is None:
            normal = material.node_tree.nodes.new('ShaderNodeNormalMap')
        normal.hide = True
        normal.location = (image.location[0] + 100, image.location[1])
        image.location  = (image.location[0] - 200, image.location[1])
        links = material.node_tree.links
        links.new(normal.inputs["Color"], image.outputs["Color"])
        links.new(bsdf.inputs["Normal"],  normal.outputs["Normal"])

    def draw_properties(self, context: Context, layout: UILayout):
        col = layout.column()
        col.prop(self, 'flip_y')
        if context.scene.gd.engine == 'grabdoc':
            if self.engine == 'cycles':
                col.prop(self, 'bevel_weight')

    def update_flip_y(self, _context: Context):
        vec_multiply = self.node_tree.nodes['Vector Math']
        vec_multiply.inputs[1].default_value[1] = -.5 if self.flip_y else .5

    def update_bevel_weight(self, _context: Context):
        bevel = self.node_tree.nodes['Bevel']
        bevel.inputs[0].default_value = self.bevel_weight

    flip_y: BoolProperty(
        description="Flip the normal map Y direction (DirectX format)",
        name="Invert (-Y)", options={'SKIP_SAVE'}, update=update_flip_y
    )
    bevel_weight: FloatProperty(
        description="Bevel shader weight (May need to increase samples)",
        name="Bevel", options={'SKIP_SAVE'}, update=update_bevel_weight,
        default=0, step=1, min=0, max=10, soft_max=1
    )


class Curvature(Baker):
    ID                  = 'curvature'
    NAME                = ID.capitalize()
    VIEW_TRANSFORM      = "Standard"
    MARMOSET_COMPATIBLE = True
    REQUIRED_SOCKETS    = ()
    OPTIONAL_SOCKETS    = ()
    SUPPORTED_ENGINES   = (('blender_workbench',  "Workbench", ""),
                           ('cycles',             "Cycles",    ""))

    def setup(self) -> None:
        super().setup()
        scene = bpy.context.scene
        scene_shading = scene.display.shading
        scene_shading.light = 'FLAT'
        scene_shading.color_type = 'SINGLE'
        scene_shading.show_cavity = True
        scene_shading.cavity_type = 'BOTH'
        scene_shading.cavity_ridge_factor = \
        scene_shading.curvature_ridge_factor = self.ridge
        scene_shading.curvature_valley_factor = self.valley
        scene_shading.cavity_valley_factor = 0
        scene_shading.single_color = (.214041, .214041, .214041)
        scene.display.matcap_ssao_distance = .075
        self.update_range(bpy.context)

    def node_setup(self):
        super().node_setup()

        geometry = self.node_tree.nodes.new('ShaderNodeNewGeometry')
        geometry.location = (-800, 0)

        color_ramp = self.node_tree.nodes.new('ShaderNodeValToRGB')
        color_ramp.color_ramp.elements.new(.5)
        color_ramp.color_ramp.elements[0].position = 0.49
        color_ramp.color_ramp.elements[2].position = 0.51
        color_ramp.location = (-600, 0)

        emission = self.node_tree.nodes.new('ShaderNodeEmission')
        emission.location = (-200, 0)

        links = self.node_tree.links
        links.new(color_ramp.inputs["Fac"], geometry.outputs["Pointiness"])
        links.new(emission.inputs["Color"], color_ramp.outputs["Color"])
        links.new(self.node_output.inputs["Shader"],
                  emission.outputs["Emission"])

    def apply_render_settings(self, requires_preview: bool=True):
        super().apply_render_settings(requires_preview)
        scene = bpy.context.scene
        view_transform = self.VIEW_TRANSFORM
        if scene.render.engine != 'BLENDER_WORKBENCH':
            view_transform = "Raw"
        set_color_management(view_transform)

    def draw_properties(self, context: Context, layout: UILayout):
        if context.scene.gd.engine != 'grabdoc':
            return
        col = layout.column()
        if context.scene.render.engine == 'BLENDER_WORKBENCH':
            col.prop(self, 'ridge', text="Ridge")
            col.prop(self, 'valley', text="Valley")
        elif context.scene.render.engine == 'CYCLES':
            col.prop(self, 'range', text="Range")

    def cleanup(self) -> None:
        bpy.data.objects[Global.BG_PLANE_NAME].color[3] = 1

    def update_curvature(self, context: Context):
        if not context.scene.gd.preview_state:
            return
        scene_shading = context.scene.display.shading
        scene_shading.cavity_ridge_factor     = \
        scene_shading.curvature_ridge_factor  = self.ridge
        scene_shading.curvature_valley_factor = self.valley

    def update_range(self, _context: Context):
        color_ramp = self.node_tree.nodes['Color Ramp']
        color_ramp.color_ramp.elements[0].position = 0.49 - (self.range/2+.01)
        color_ramp.color_ramp.elements[2].position = 0.51 + (self.range/2-.01)

    ridge: FloatProperty(name="", update=update_curvature,
                         default=2, min=0, max=2, precision=3,
                         step=.1, subtype='FACTOR')
    valley: FloatProperty(name="", update=update_curvature,
                          default=1.5, min=0, max=2, precision=3,
                          step=.1, subtype='FACTOR')
    range: FloatProperty(name="", update=update_range,
                         default=.05, min=0, max=1, step=.1, subtype='FACTOR')


class Occlusion(Baker):
    ID                  = 'occlusion'
    NAME                = ID.capitalize()
    VIEW_TRANSFORM      = "Raw"
    MARMOSET_COMPATIBLE = True
    REQUIRED_SOCKETS    = ()
    OPTIONAL_SOCKETS    = ('Alpha', 'Normal')
    SUPPORTED_ENGINES   = Baker.SUPPORTED_ENGINES[:-1]

    def setup(self) -> None:
        super().setup()
        scene = bpy.context.scene
        eevee = scene.eevee
        if scene.render.engine == Global.EEVEE_ENGINE_NAME.upper():
            eevee.use_overscan  = True
            eevee.overscan_size = 25

    def node_setup(self):
        super().node_setup()
        self.node_tree.interface.new_socket(
            name='Normal', socket_type='NodeSocketVector'
        )
        self.node_input.location = (-1400, -225)

        geometry = self.node_tree.nodes.new('ShaderNodeNewGeometry')
        geometry.location = (-1400, 0)

        vec_mix = self.node_tree.nodes.new('ShaderNodeMix')
        vec_mix.data_type = 'VECTOR'
        vec_mix.location = (-1200, 0)

        vec_sep = self.node_tree.nodes.new('ShaderNodeSeparateXYZ')
        vec_sep.location = (-1200, -200)

        vec_ceil = self.node_tree.nodes.new('ShaderNodeVectorMath')
        vec_ceil.operation = 'CEIL'
        vec_ceil.location = (-1200, -325)

        ao = self.node_tree.nodes.new('ShaderNodeAmbientOcclusion')
        ao.samples  = 32
        ao.location = (-1000, 0)

        invert = self.node_tree.nodes.new('ShaderNodeInvert')
        invert.inputs[0].default_value = 0
        invert.location = (-800, 0)

        gamma = self.node_tree.nodes.new('ShaderNodeGamma')
        gamma.inputs[1].default_value = 1
        gamma.location = (-600, 0)

        emission = self.node_tree.nodes.new('ShaderNodeEmission')
        emission.location = (-400, 0)

        transp_invert = self.node_tree.nodes.new('ShaderNodeInvert')
        transp_invert.location = (-600, -300)

        subtract = self.node_tree.nodes.new('ShaderNodeMixRGB')
        subtract.blend_type = 'SUBTRACT'
        subtract.inputs[0].default_value = 1
        subtract.inputs[1].default_value = (1, 1, 1, 1)
        subtract.location = (-400, -300)

        transp_shader = self.node_tree.nodes.new('ShaderNodeBsdfTransparent')
        transp_shader.location = (-200, -125)

        mix_shader = self.node_tree.nodes.new('ShaderNodeMixShader')
        mix_shader.location = (-200, 0)

        links = self.node_tree.links
        links.new(vec_mix.inputs['Factor'], vec_sep.outputs['Z'])
        links.new(vec_mix.inputs['A'],      geometry.outputs['Normal'])
        links.new(vec_mix.inputs['B'],      self.node_input.outputs['Normal'])
        links.new(vec_sep.inputs[0],        vec_ceil.outputs[0])
        links.new(vec_ceil.inputs[0],       self.node_input.outputs['Normal'])

        links.new(ao.inputs["Normal"],      vec_mix.outputs['Result'])
        links.new(invert.inputs["Color"],   ao.outputs["Color"])
        links.new(gamma.inputs["Color"],    invert.outputs["Color"])
        links.new(emission.inputs["Color"], gamma.outputs["Color"])

        links.new(transp_invert.inputs[1], self.node_input.outputs['Alpha'])
        links.new(subtract.inputs[2],      transp_invert.outputs[0])

        links.new(mix_shader.inputs[0], subtract.outputs[0])
        links.new(mix_shader.inputs[1], transp_shader.outputs[0])
        links.new(mix_shader.inputs[2], emission.outputs["Emission"])
        links.new(self.node_output.inputs['Shader'],
                  mix_shader.outputs['Shader'])

    def draw_properties(self, context: Context, layout: UILayout):
        gd = context.scene.gd
        col = layout.column()
        if gd.engine == 'marmoset':
            col.prop(gd, "mt_occlusion_samples", text="Ray Count")
            return
        col.prop(self, 'invert')
        col.prop(self, 'gamma')
        col.prop(self, 'distance')

    def update_gamma(self, _context: Context):
        gamma = self.node_tree.nodes['Gamma']
        gamma.inputs[1].default_value = self.gamma

    def update_distance(self, _context: Context):
        ao = self.node_tree.nodes['Ambient Occlusion']
        ao.inputs[1].default_value = self.distance

    def update_invert(self, _context: Context):
        invert = self.node_tree.nodes['Invert Color']
        invert.inputs[0].default_value = 1 if self.invert else 0

    gamma: FloatProperty(
        description="Intensity of AO (calculated with gamma)",
        default=1, min=.001, soft_max=10, step=.17,
        name="Intensity", update=update_gamma
    )
    distance: FloatProperty(
        description="The distance AO rays travel",
        default=1, min=0, soft_max=100, step=.03, subtype='DISTANCE',
        name="Distance", update=update_distance
    )
    invert: BoolProperty(
        name="Invert", description="Invert the mask", update=update_invert
    )


class Height(Baker):
    ID                  = 'height'
    NAME                = ID.capitalize()
    VIEW_TRANSFORM      = "Raw"
    MARMOSET_COMPATIBLE = True
    REQUIRED_SOCKETS    = ()
    OPTIONAL_SOCKETS    = ()
    SUPPORTED_ENGINES   = Baker.SUPPORTED_ENGINES[:-1]

    def setup(self) -> None:
        super().setup()
        if self.method == 'AUTO':
            rendered_obs = get_rendered_objects()
            set_guide_height(rendered_obs)

    def node_setup(self):
        super().node_setup()

        camera = self.node_tree.nodes.new('ShaderNodeCameraData')
        camera.location = (-800, 0)

        # NOTE: Map Range updates handled on map preview
        map_range = self.node_tree.nodes.new('ShaderNodeMapRange')
        map_range.location = (-600, 0)

        ramp = self.node_tree.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
        ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
        ramp.location = (-400, 0)

        links = self.node_tree.links
        links.new(map_range.inputs["Value"], camera.outputs["View Z Depth"])
        links.new(ramp.inputs["Fac"], map_range.outputs["Result"])
        links.new(self.node_output.inputs["Shader"], ramp.outputs["Color"])

    def draw_properties(self, context: Context, layout: UILayout):
        col = layout.column()
        if context.scene.gd.engine == 'grabdoc':
            col.prop(self, 'invert', text="Invert")
        row = col.row()
        row.prop(self, 'method', text="Method", expand=True)
        if self.method == 'MANUAL':
            col.prop(self, 'distance', text="0-1 Range")

    def update_method(self, context: Context):
        scene_setup(self, context)
        if not context.scene.gd.preview_state:
            return
        if self.method == 'AUTO':
            rendered_obs = get_rendered_objects()
            set_guide_height(rendered_obs)

    def update_guide(self, context: Context):
        map_range = self.node_tree.nodes['Map Range']
        camera_object_z = Global.CAMERA_DISTANCE * bpy.context.scene.gd.scale
        map_range.inputs[1].default_value = camera_object_z - self.distance
        map_range.inputs[2].default_value = camera_object_z

        ramp = self.node_tree.nodes['Color Ramp']
        ramp.color_ramp.elements[0].color = \
            (0, 0, 0, 1) if self.invert else (1, 1, 1, 1)
        ramp.color_ramp.elements[1].color = \
            (1, 1, 1, 1) if self.invert else (0, 0, 0, 1)
        ramp.location = (-400, 0)

        if self.method == 'MANUAL':
            scene_setup(self, context)

    invert: BoolProperty(
        description="Invert height mask, useful for sculpting negatively",
        update=update_guide
    )
    distance: FloatProperty(
        name="", update=update_guide,
        default=1, min=.01, soft_max=100, step=.03, subtype='DISTANCE'
    )
    method: EnumProperty(
        description="Height method, use manual if auto produces range errors",
        name="Method", update=update_method,
        items=(('AUTO',   "Auto",   ""),
               ('MANUAL', "Manual", ""))
    )


class Id(Baker):
    ID                  = 'id'
    NAME                = "Material ID"
    VIEW_TRANSFORM      = "Standard"
    MARMOSET_COMPATIBLE = True
    REQUIRED_SOCKETS    = ()
    OPTIONAL_SOCKETS    = ()
    SUPPORTED_ENGINES   = (Baker.SUPPORTED_ENGINES[-1],)

    def initialize(self):
        super().initialize()
        self.disable_filtering = True

    def setup(self) -> None:
        super().setup()
        if bpy.context.scene.render.engine == 'BLENDER_WORKBENCH':
            self.update_method(bpy.context)

    def node_setup(self):
        pass

    def draw_properties(self, context: Context, layout: UILayout):
        gd = context.scene.gd
        row = layout.row()
        if gd.engine != 'marmoset':
            row.prop(self, 'method')
        if self.method != 'MATERIAL':
            return

        col = layout.column(align=True)
        col.separator(factor=.5)
        col.scale_y = 1.1
        col.operator("grabdoc.quick_id_setup")

        row = col.row(align=True)
        row.scale_y = .9
        row.label(text=" Remove:")
        row.operator(
            "grabdoc.remove_mats_by_name",
            text='All'
        ).name = Global.RANDOM_ID_PREFIX

        col = layout.column(align=True)
        col.separator(factor=.5)
        col.scale_y = 1.1
        col.operator("grabdoc.quick_id_selected")

        row = col.row(align=True)
        row.scale_y = .9
        row.label(text=" Remove:")
        row.operator("grabdoc.remove_mats_by_name",
                     text='All').name = Global.ID_PREFIX
        row.operator("grabdoc.quick_remove_selected_mats",
                     text='Selected')

    def update_method(self, context: Context):
        shading = context.scene.display.shading
        shading.show_cavity = False
        shading.light = 'FLAT'
        shading.color_type = self.method

    method: EnumProperty(
        items=(('MATERIAL', 'Material', ''),
               ('SINGLE',   'Single',   ''),
               ('OBJECT',   'Object',   ''),
               ('RANDOM',   'Random',   ''),
               ('VERTEX',   'Vertex',   ''),
               ('TEXTURE',  'Texture',  '')),
        name="Method", update=update_method, default='RANDOM'
    )

class Alpha(Baker):
    ID                  = 'alpha'
    NAME                = ID.capitalize()
    VIEW_TRANSFORM      = "Raw"
    MARMOSET_COMPATIBLE = True
    REQUIRED_SOCKETS    = ()
    OPTIONAL_SOCKETS    = Baker.OPTIONAL_SOCKETS
    SUPPORTED_ENGINES   = Baker.SUPPORTED_ENGINES[:-1]

    def node_setup(self):
        super().node_setup()

        camera = self.node_tree.nodes.new('ShaderNodeCameraData')
        camera.location = (-1000, 0)

        map_range = self.node_tree.nodes.new('ShaderNodeMapRange')
        map_range.location = (-800, 0)
        camera_object_z = Global.CAMERA_DISTANCE * bpy.context.scene.gd.scale
        map_range.inputs[1].default_value = camera_object_z - .00001
        map_range.inputs[2].default_value = camera_object_z

        invert_mask = self.node_tree.nodes.new('ShaderNodeInvert')
        invert_mask.name = "Invert Mask"
        invert_mask.location = (-600, 200)

        invert_depth = self.node_tree.nodes.new('ShaderNodeInvert')
        invert_depth.name = "Invert Depth"
        invert_depth.location = (-600, 0)

        mix = self.node_tree.nodes.new('ShaderNodeMix')
        mix.name = "Invert Mask"
        mix.data_type = "RGBA"
        mix.inputs["B"].default_value = (0, 0, 0, 1)
        mix.location = (-400, 0)

        emission = self.node_tree.nodes.new('ShaderNodeEmission')
        emission.location = (-200, 0)

        links = self.node_tree.links
        links.new(invert_mask.inputs["Color"], self.node_input.outputs["Alpha"])
        links.new(mix.inputs["Factor"], invert_mask.outputs["Color"])

        links.new(map_range.inputs["Value"], camera.outputs["View Z Depth"])
        links.new(invert_depth.inputs["Color"], map_range.outputs["Result"])
        links.new(mix.inputs["A"], invert_depth.outputs["Color"])

        links.new(emission.inputs["Color"], mix.outputs["Result"])
        links.new(self.node_output.inputs["Shader"],
                  emission.outputs["Emission"])

    def draw_properties(self, context: Context, layout: UILayout):
        if context.scene.gd.engine != 'grabdoc':
            return
        col = layout.column()
        col.prop(self, 'invert_depth', text="Invert Depth")
        col.prop(self, 'invert_mask', text="Invert Mask")

    def update_map_range(self, _context: Context):
        map_range = self.node_tree.nodes['Map Range']
        camera_object_z = Global.CAMERA_DISTANCE * bpy.context.scene.gd.scale
        map_range.inputs[1].default_value = camera_object_z - .00001
        map_range.inputs[2].default_value = camera_object_z
        invert_depth = self.node_tree.nodes['Invert Depth']
        invert_depth.inputs[0].default_value = 0 if self.invert_depth else 1
        invert_mask = self.node_tree.nodes['Invert Mask']
        invert_mask.inputs[0].default_value = 0 if self.invert_mask else 1

    invert_depth: BoolProperty(
        description="Invert the global depth mask", update=update_map_range
    )
    invert_mask: BoolProperty(
        description="Invert the alpha mask", update=update_map_range
    )


class Roughness(Baker):
    ID                  = 'roughness'
    NAME                = ID.capitalize()
    VIEW_TRANSFORM      = "Raw"
    MARMOSET_COMPATIBLE = False
    REQUIRED_SOCKETS    = (NAME,)
    OPTIONAL_SOCKETS    = ()
    SUPPORTED_ENGINES   = Baker.SUPPORTED_ENGINES[:-1]

    def node_setup(self):
        super().node_setup()
        self.node_tree.interface.new_socket(
            name=self.NAME, socket_type='NodeSocketFloat'
        )

        invert = self.node_tree.nodes.new('ShaderNodeInvert')
        invert.location = (-400, 0)
        invert.inputs[0].default_value = 0

        emission = self.node_tree.nodes.new('ShaderNodeEmission')
        emission.location = (-200, 0)

        links = self.node_tree.links
        links.new(invert.inputs["Color"], self.node_input.outputs["Roughness"])
        links.new(emission.inputs["Color"], invert.outputs["Color"])
        links.new(self.node_output.inputs["Shader"],
                  emission.outputs["Emission"])

    def draw_properties(self, _context: Context, layout: UILayout):
        col = layout.column()
        col.prop(self, 'invert', text="Invert")

    def update_invert(self, _context: Context):
        invert = self.node_tree.nodes['Invert Color']
        invert.inputs[0].default_value = 1 if self.invert else 0

    invert: BoolProperty(description="Invert the Roughness (AKA Glossiness)",
                         update=update_invert)


class Color(Baker):
    ID                  = 'color'
    NAME                = "Base Color"
    VIEW_TRANSFORM      = "Standard"
    MARMOSET_COMPATIBLE = False
    REQUIRED_SOCKETS    = (NAME,)
    OPTIONAL_SOCKETS    = ()
    SUPPORTED_ENGINES   = Baker.SUPPORTED_ENGINES[:-1]

    def node_setup(self):
        super().node_setup()
        self.node_tree.interface.new_socket(
            name=self.NAME, socket_type='NodeSocketColor'
        )

        emission = self.node_tree.nodes.new('ShaderNodeEmission')
        emission.location = (-200, 0)

        links = self.node_tree.links
        links.new(emission.inputs["Color"],
                  self.node_input.outputs["Base Color"])
        links.new(self.node_output.inputs["Shader"],
                  emission.outputs["Emission"])

    def reimport_setup(self, material, image):
        image.image.colorspace_settings.name = 'Non-Color'
        bsdf  = material.node_tree.nodes['Principled BSDF']
        links = material.node_tree.links
        links.new(bsdf.inputs["Base Color"], image.outputs["Color"])


class Emissive(Baker):
    ID                  = 'emissive'
    NAME                = ID.capitalize()
    VIEW_TRANSFORM      = "Standard"
    MARMOSET_COMPATIBLE = False
    REQUIRED_SOCKETS    = ("Emission Color", "Emission Strength")
    OPTIONAL_SOCKETS    = ()
    SUPPORTED_ENGINES   = Baker.SUPPORTED_ENGINES[:-1]

    def node_setup(self):
        super().node_setup()
        emit_color = self.node_tree.interface.new_socket(
            name="Emission Color", socket_type='NodeSocketColor'
        )
        emit_color.default_value = (0, 0, 0, 1)
        emit_strength = self.node_tree.interface.new_socket(
            name="Emission Strength", socket_type='NodeSocketFloat'
        )
        emit_strength.default_value = 1

        emission = self.node_tree.nodes.new('ShaderNodeEmission')
        emission.location = (-200, 0)

        links = self.node_tree.links
        links.new(emission.inputs["Color"],
                  self.node_input.outputs["Emission Color"])
        links.new(emission.inputs["Strength"],
                  self.node_input.outputs["Emission Strength"])
        links.new(self.node_output.inputs["Shader"],
                  emission.outputs["Emission"])

    def reimport_setup(self, material, image):
        image.image.colorspace_settings.name = 'Non-Color'
        bsdf  = material.node_tree.nodes['Principled BSDF']
        links = material.node_tree.links
        links.new(bsdf.inputs["Emission Color"], image.outputs["Color"])


class Metallic(Baker):
    ID                  = 'metallic'
    NAME                = ID.capitalize()
    VIEW_TRANSFORM      = "Raw"
    MARMOSET_COMPATIBLE = False
    REQUIRED_SOCKETS    = (NAME,)
    OPTIONAL_SOCKETS    = ()
    SUPPORTED_ENGINES   = Baker.SUPPORTED_ENGINES[:-1]

    def node_setup(self):
        super().node_setup()
        self.node_tree.interface.new_socket(
            name=self.NAME, socket_type='NodeSocketFloat'
        )

        invert = self.node_tree.nodes.new('ShaderNodeInvert')
        invert.location = (-400, 0)
        invert.inputs[0].default_value = 0

        emission = self.node_tree.nodes.new('ShaderNodeEmission')
        emission.location = (-200, 0)

        links = self.node_tree.links
        links.new(emission.inputs["Color"], self.node_input.outputs["Metallic"])
        links.new(self.node_output.inputs["Shader"],
                  emission.outputs["Emission"])

    def reimport_setup(self, material, image):
        bsdf  = material.node_tree.nodes['Principled BSDF']
        links = material.node_tree.links
        links.new(bsdf.inputs["Metallic"], image.outputs["Color"])

    def draw_properties(self, _context: Context, layout: UILayout):
        col = layout.column()
        col.prop(self, 'invert', text="Invert")

    def update_invert(self, _context: Context):
        invert = self.node_tree.nodes['Invert Color']
        invert.inputs[0].default_value = 1 if self.invert else 0

    invert: BoolProperty(description="Invert the mask", update=update_invert)


class Custom(Baker):
    ID                  = 'custom'
    NAME                = ID.capitalize()
    VIEW_TRANSFORM      = "Raw"
    MARMOSET_COMPATIBLE = False
    REQUIRED_SOCKETS    = ()
    OPTIONAL_SOCKETS    = ()
    SUPPORTED_ENGINES   = Baker.SUPPORTED_ENGINES[:-1]

    def update_view_transform(self, _context: Context):
        self.VIEW_TRANSFORM = self.view_transform.capitalize()
        self.apply_render_settings()

    def draw_properties(self, context: Context, layout: UILayout):
        col = layout.column()
        row = col.row()
        if context.scene.gd.preview_state:
            row.enabled = False
        if not isinstance(self.node_tree, NodeTree):
            row.alert = True
        row.prop(self, 'node_tree')
        col.prop(self, 'view_transform')

    def node_setup(self, _context: Context=bpy.context):
        if not isinstance(self.node_tree, NodeTree):
            self.node_name = ""
            return
        self.node_name = self.node_tree.name
        self.__class__.REQUIRED_SOCKETS = \
            tuple(socket.name for socket in get_group_inputs(self.node_tree))
        generate_shader_interface(self.node_tree, get_material_output_sockets())

    # NOTE: Subclassed property - implement as user-facing
    node_tree: PointerProperty(
        description="Your baking shader, MUST have shader output",
        name='Shader', type=NodeTree, update=node_setup
    )
    view_transform: EnumProperty(items=(('raw',      "Raw",      ""),
                                        ('standard', "Standard", "")),
                                 name="View", default=VIEW_TRANSFORM.lower(),
                                 update=update_view_transform)
