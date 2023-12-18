import bpy
from bpy.types import (
    Object,
    ShaderNodeGroup,
    NodeSocket,
    Context,
    Material
)

from ..constants import GlobalVariableConstants as Global
from ..constants import ErrorCodeConstants as Error


def ng_setup() -> None:
    """Initial setup of all node groups when setting up a file"""
    gd = bpy.context.scene.grabDoc

    # Create a dummy material output node to harvest potential inputs
    ng_dummy_output = bpy.data.node_groups.new(
        'Material Output',
        'ShaderNodeTree'
    )
    output = ng_dummy_output.nodes.new(
        'ShaderNodeOutputMaterial'
    )

    collected_inputs = {}
    for node_input in output.inputs:
        # NOTE: I have no idea why this secret input exists
        if node_input.name == 'Thickness':
            continue

        collected_inputs[node_input.name] = \
            f'NodeSocket{node_input.type.capitalize()}'

    # NORMALS
    if not Global.NG_NORMAL_NAME in bpy.data.node_groups:
        tree = bpy.data.node_groups.new(
            Global.NG_NORMAL_NAME, 'ShaderNodeTree'
        )
        tree.use_fake_user = True

        # Create group inputs/outputs
        tree.interface.new_socket(name="Input", in_out='INPUT')

        tree.interface.new_panel(name="My Panel")

        group_outputs = tree.nodes.new('NodeGroupOutput')
        group_outputs.name = "Group Output"
        group_inputs = tree.nodes.new('NodeGroupInput')
        group_inputs.name = "Group Input"
        group_inputs.location = (-1400,100)
        tree.interface.new_socket(
            name="Output", socket_type='NodeSocketShader', in_out='OUTPUT'
        )
        for key, value in collected_inputs.items():
            tree.interface.new_socket(name=f'Saved {key}', socket_type=value)
        alpha_input = tree.interface.new_socket(
            name='Alpha',
            socket_type='NodeSocketFloat'
        )
        alpha_input.default_value = 1
        tree.interface.new_socket(name='Normal', socket_type='NodeSocketVector')

        # Create group nodes
        bevel = tree.nodes.new('ShaderNodeBevel')
        bevel.name = "Bevel"
        bevel.inputs[0].default_value = 0
        bevel.location = (-1000,0)

        bevel_node_2 = tree.nodes.new('ShaderNodeBevel')
        bevel_node_2.name = "Bevel.001"
        bevel_node_2.location = (-1000,-200)
        bevel_node_2.inputs[0].default_value = 0

        vec_transform = tree.nodes.new('ShaderNodeVectorTransform')
        vec_transform.name = "Vector Transform"
        vec_transform.vector_type = 'NORMAL'
        vec_transform.convert_to = 'CAMERA'
        vec_transform.location = (-800,0)

        vec_mult = tree.nodes.new('ShaderNodeVectorMath')
        vec_mult.name = "Vector Math"
        vec_mult.operation = 'MULTIPLY'
        vec_mult.inputs[1].default_value[0] = .5
        vec_mult.inputs[1].default_value[1] = -.5 if gd.flipYNormals else .5
        vec_mult.inputs[1].default_value[2] = -.5
        vec_mult.location = (-600,0)

        vec_add = tree.nodes.new('ShaderNodeVectorMath')
        vec_add.name = "Vector Math.001"
        vec_add.inputs[1].default_value[0] = \
        vec_add.inputs[1].default_value[1] = \
        vec_add.inputs[1].default_value[2] = \
            0.5
        vec_add.location = (-400,0)

        invert = tree.nodes.new('ShaderNodeInvert')
        invert.name = "Invert"
        invert.location = (-1000,200)

        subtract = tree.nodes.new('ShaderNodeMixRGB')
        subtract.blend_type = 'SUBTRACT'
        subtract.name = "Subtract"
        subtract.inputs[0].default_value = 1
        subtract.inputs[1].default_value = (1, 1, 1, 1)
        subtract.location = (-800,300)

        transp_shader = tree.nodes.new('ShaderNodeBsdfTransparent')
        transp_shader.name = "Transparent BSDF"
        transp_shader.location = (-400,200)

        mix_shader = tree.nodes.new('ShaderNodeMixShader')
        mix_shader.name = "Mix Shader"
        mix_shader.location = (-200,300)

        # Link nodes
        link = tree.links

        # Path 1
        link.new(bevel.inputs["Normal"], group_inputs.outputs["Normal"])
        link.new(vec_transform.inputs["Vector"], bevel_node_2.outputs["Normal"])
        link.new(vec_mult.inputs["Vector"], vec_transform.outputs["Vector"])
        link.new(vec_add.inputs["Vector"], vec_mult.outputs["Vector"])
        link.new(group_outputs.inputs["Output"], vec_add.outputs["Vector"])

        # Path 2
        link.new(invert.inputs['Color'], group_inputs.outputs['Alpha'])
        link.new(subtract.inputs['Color2'], invert.outputs['Color'])
        link.new(mix_shader.inputs['Fac'], subtract.outputs['Color'])
        link.new(mix_shader.inputs[1], transp_shader.outputs['BSDF'])
        link.new(mix_shader.inputs[2], vec_add.outputs['Vector'])

    # AMBIENT OCCLUSION
    if not Global.NG_AO_NAME in bpy.data.node_groups:
        ng_ao = bpy.data.node_groups.new(Global.NG_AO_NAME, 'ShaderNodeTree')
        ng_ao.use_fake_user = True

        # Create group inputs/outputs
        group_outputs = ng_ao.nodes.new('NodeGroupOutput')
        group_outputs.name = "Group Output"
        ng_ao.outputs.new('NodeSocketShader','Output')
        for key, value in collected_inputs.items():
            ng_ao.inputs.new(value, f'Saved {key}')

        # Create group nodes
        ao = ng_ao.nodes.new('ShaderNodeAmbientOcclusion')
        ao.name = "Ambient Occlusion"
        ao.samples = 32
        ao.location = (-600,0)

        gamma = ng_ao.nodes.new('ShaderNodeGamma')
        gamma.name = "Gamma"
        gamma.inputs[1].default_value = gd.gammaOcclusion
        gamma.location = (-400,0)

        emission = ng_ao.nodes.new('ShaderNodeEmission')
        emission.name = "Emission"
        emission.location = (-200,0)

        # Link nodes
        link = ng_ao.links
        link.new(gamma.inputs["Color"], ao.outputs["Color"])
        link.new(emission.inputs["Color"], gamma.outputs["Color"])
        link.new(group_outputs.inputs["Output"], emission.outputs["Emission"])

    # HEIGHT
    if not Global.NG_HEIGHT_NAME in bpy.data.node_groups:
        ng_height = bpy.data.node_groups.new(
            Global.NG_HEIGHT_NAME,
            'ShaderNodeTree'
        )
        ng_height.use_fake_user = True

        # Create group inputs/outputs
        group_outputs = ng_height.nodes.new('NodeGroupOutput')
        group_outputs.name = "Group Output"
        ng_height.outputs.new('NodeSocketShader','Output')
        for key, value in collected_inputs.items():
            ng_height.inputs.new(value, f'Saved {key}')

        # Create group nodes
        camera = ng_height.nodes.new('ShaderNodeCameraData')
        camera.name = "Camera Data"
        camera.location = (-800,0)

        # NOTE: Map Range updates handled on map preview
        map_range = ng_height.nodes.new('ShaderNodeMapRange')
        map_range.name = "Map Range"
        map_range.location = (-600,0)

        ramp = ng_height.nodes.new('ShaderNodeValToRGB')
        ramp.name = "ColorRamp"
        ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
        ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
        ramp.location = (-400,0)

        # Link nodes
        link = ng_height.links
        link.new(map_range.inputs["Value"], camera.outputs["View Z Depth"])
        link.new(ramp.inputs["Fac"], map_range.outputs["Result"])
        link.new(group_outputs.inputs["Output"], ramp.outputs["Color"])

    # ALPHA
    if not Global.NG_ALPHA_NAME in bpy.data.node_groups:
        ng_alpha = bpy.data.node_groups.new(
            Global.NG_ALPHA_NAME,
            'ShaderNodeTree'
        )
        ng_alpha.use_fake_user = True

        # Create group input/outputs
        group_outputs = ng_alpha.nodes.new('NodeGroupOutput')
        group_outputs.name = "Group Output"
        ng_alpha.outputs.new('NodeSocketShader','Output')
        for key, value in collected_inputs.items():
            ng_alpha.inputs.new(value, f'Saved {key}')

        # Create group nodes
        camera = ng_alpha.nodes.new('ShaderNodeCameraData')
        camera.name = "Camera Data"
        camera.location = (-800,0)

        gd_camera_ob_z = \
            bpy.data.objects.get(Global.TRIM_CAMERA_NAME).location[2]

        map_range = ng_alpha.nodes.new('ShaderNodeMapRange')
        map_range.name = "Map Range"
        map_range.location = (-600,0)
        map_range.inputs[1].default_value = gd_camera_ob_z - .00001
        map_range.inputs[2].default_value = gd_camera_ob_z

        invert = ng_alpha.nodes.new('ShaderNodeInvert')
        invert.name = "Invert"
        invert.location = (-400,0)

        emission = ng_alpha.nodes.new('ShaderNodeEmission')
        emission.name = "Emission"
        emission.location = (-200,0)

        # Link nodes
        link = ng_alpha.links
        link.new(map_range.inputs["Value"], camera.outputs["View Z Depth"])
        link.new(invert.inputs["Color"], map_range.outputs["Result"])
        link.new(emission.inputs["Color"], invert.outputs["Color"])
        link.new(group_outputs.inputs["Output"], emission.outputs["Emission"])

    # ALBEDO
    if not Global.NG_ALBEDO_NAME in bpy.data.node_groups:
        ng_albedo = \
            bpy.data.node_groups.new(
                Global.NG_ALBEDO_NAME,
                'ShaderNodeTree'
            )
        ng_albedo.use_fake_user = True

        # Create group inputs/outputs
        group_outputs = ng_albedo.nodes.new('NodeGroupOutput')
        group_outputs.name = "Group Output"
        group_inputs = ng_albedo.nodes.new('NodeGroupInput')
        group_inputs.name = "Group Input"
        group_inputs.location = (-400,0)
        ng_albedo.outputs.new('NodeSocketShader','Output')
        ng_albedo.inputs.new('NodeSocketColor', 'Color Input')
        for key, value in collected_inputs.items():
            ng_albedo.inputs.new(value, f'Saved {key}')

        emission = ng_albedo.nodes.new('ShaderNodeEmission')
        emission.name = "Emission"
        emission.location = (-200,0)

        # Link nodes
        link = ng_albedo.links
        link.new(emission.inputs["Color"], group_inputs.outputs["Color Input"])
        link.new(group_outputs.inputs["Output"], emission.outputs["Emission"])

    # ROUGHNESS
    if not Global.NG_ROUGHNESS_NAME in bpy.data.node_groups:
        ng_roughness = bpy.data.node_groups.new(
                Global.NG_ROUGHNESS_NAME,
                'ShaderNodeTree'
            )
        ng_roughness.use_fake_user = True

        # Create group inputs/outputs
        group_outputs = ng_roughness.nodes.new('NodeGroupOutput')
        group_outputs.name = "Group Output"
        group_inputs = ng_roughness.nodes.new('NodeGroupInput')
        group_inputs.name = "Group Input"
        group_inputs.location = (-600,0)
        ng_roughness.outputs.new('NodeSocketShader','Output')
        ng_roughness.inputs.new('NodeSocketFloat', 'Roughness Input')
        for key, value in collected_inputs.items():
            ng_roughness.inputs.new(value, f'Saved {key}')

        invert = ng_roughness.nodes.new('ShaderNodeInvert')
        invert.location = (-400,0)
        invert.inputs[0].default_value = 0

        emission = ng_roughness.nodes.new('ShaderNodeEmission')
        emission.name = "Emission"
        emission.location = (-200,0)

        # Link nodes
        link = ng_roughness.links
        link.new(
            invert.inputs["Color"],
            group_inputs.outputs["Roughness Input"]
        )
        link.new(
            emission.inputs["Color"],
            invert.outputs["Color"]
        )
        link.new(
            group_outputs.inputs["Output"],
            emission.outputs["Emission"]
        )

    # METALNESS
    if not Global.NG_METALNESS_NAME in bpy.data.node_groups:
        ng_roughness = \
            bpy.data.node_groups.new(
                Global.NG_METALNESS_NAME,
                'ShaderNodeTree'
            )
        ng_roughness.use_fake_user = True

        # Create group inputs/outputs
        group_outputs = ng_roughness.nodes.new('NodeGroupOutput')
        group_outputs.name = "Group Output"
        group_inputs = ng_roughness.nodes.new('NodeGroupInput')
        group_inputs.name = "Group Input"
        group_inputs.location = (-400,0)
        ng_roughness.outputs.new('NodeSocketShader','Output')
        ng_roughness.inputs.new('NodeSocketFloat', 'Metalness Input')
        for key, value in collected_inputs.items():
            ng_roughness.inputs.new(value, f'Saved {key}')

        emission = ng_roughness.nodes.new('ShaderNodeEmission')
        emission.name = "Emission"
        emission.location = (-200,0)

        # Link nodes
        link = ng_roughness.links
        link.new(
            emission.inputs["Color"],
            group_inputs.outputs["Metalness Input"]
        )
        link.new(
            group_outputs.inputs["Output"],
            emission.outputs["Emission"]
        )


def create_apply_ng_mat(ob: Object) -> None:
    """Create & apply a material to objects without active materials"""
    mat_name = Global.GD_MATERIAL_NAME

    # Reuse GrabDoc created material if it already exists
    if mat_name in bpy.data.materials:
        mat = bpy.data.materials[mat_name]
    else:
        mat = bpy.data.materials.new(name = mat_name)
        mat.use_nodes = True

    # Apply the material to the appropriate slot
    #
    # Search through all material slots, if any
    # slots have no name that means they have no
    # material & therefore should have one added.
    # While this does run every time this is called
    # it should only really need to be used once per
    # in add-on use.
    #
    # We do not want to remove empty material slots
    # as they can be used for masking off materials.
    for slot in ob.material_slots:
        if slot.name == '':
            ob.material_slots[slot.name].material = mat
    if not ob.active_material or ob.active_material.name == '':
        ob.active_material = mat


def bsdf_link_factory(
        input_name: list,
        node_group: ShaderNodeGroup,
        original_input: NodeSocket,
        mat_slot: Material
    ) -> bool:
    """Add node group to all materials, save original
    links, and link the node group to material output"""
    node_found = False
    for link in original_input.links:
        node_found = True

        mat_slot.node_tree.links.new(
            node_group.inputs[input_name],
            link.from_node.outputs[link.from_socket.name]
        )
        break
    else:
        try:
            node_group.inputs[input_name].default_value = \
                original_input.default_value
        except TypeError:
            if isinstance(original_input.default_value, float):
                node_group.inputs[input_name].default_value = \
                    int(original_input.default_value)
            else:
                node_group.inputs[input_name].default_value = \
                    float(original_input.default_value)
    return node_found


def add_ng_to_mat(self, context: Context, setup_type: str) -> None:
    """Add corresponding node groups to all materials/objects"""
    for ob in context.view_layer.objects:
        if (
            ob.name not in self.rendered_obs \
            and ob.name == Global.ORIENT_GUIDE_NAME
        ):
            continue

        # If no material slots found or empty mat
        # slots found, assign a material to it
        if not ob.material_slots or '' in ob.material_slots:
            create_apply_ng_mat(ob)

        # Cycle through all material slots
        for slot in ob.material_slots:
            mat_slot = bpy.data.materials.get(slot.name)
            mat_slot.use_nodes = True

            nodes = mat_slot.node_tree.nodes
            if setup_type in nodes:
                continue

            # Get materials Output Material node(s)
            output_nodes = {
                mat for mat in nodes if mat.type == 'OUTPUT_MATERIAL'
            }
            if not output_nodes:
                output_nodes.append(
                    nodes.new('ShaderNodeOutputMaterial')
                )

            node_group = bpy.data.node_groups.get(setup_type)
            for output in output_nodes:
                # Add node group to material
                GD_node_group = nodes.new('ShaderNodeGroup')
                GD_node_group.node_tree = node_group
                GD_node_group.location = (
                    output.location[0],
                    output.location[1] - 160
                )
                GD_node_group.name = node_group.name
                GD_node_group.hide = True

                # Add note next to node group explaining basic functionality
                GD_text = bpy.data.texts.get('_grabdoc_ng_warning')
                if GD_text is None:
                    GD_text = bpy.data.texts.new(name='_grabdoc_ng_warning')

                GD_text.clear()
                GD_text.write(Global.NG_NODE_WARNING)

                GD_frame = nodes.new('NodeFrame')
                GD_frame.location = (
                    output.location[0],
                    output.location[1] - 195
                )
                GD_frame.name = node_group.name
                GD_frame.text = GD_text
                GD_frame.width = 1000
                GD_frame.height = 150

                # Handle node linking
                for node_input in output.inputs:
                    for link in node_input.links:
                        original = nodes.get(link.from_node.name)

                        # Link original connections to the Node Group
                        # TODO: can be more modular
                        connections_to_make = \
                            ('Surface', 'Volume', 'Displacement')
                        if node_input.name in connections_to_make:
                            for connection_name in connections_to_make:
                                if node_input.name != connection_name:
                                    continue
                                mat_slot.node_tree.links.new(
                                    GD_node_group.inputs[
                                        f"Saved {connection_name}"
                                    ],
                                    original.outputs[link.from_socket.name]
                                )

                        # Links for maps that feed information
                        # from the Principled BSDF
                        if setup_type not in (
                            Global.NG_ALBEDO_NAME,
                            Global.NG_ROUGHNESS_NAME,
                            Global.NG_METALNESS_NAME,
                            Global.NG_NORMAL_NAME
                        ) and original.type != 'BSDF_PRINCIPLED':
                            continue

                        node_found = False
                        for original_input in original.inputs:
                            if (
                                setup_type == Global.NG_ALBEDO_NAME \
                                and original_input.name == 'Base Color'
                            ):
                                node_found = bsdf_link_factory(
                                    input_name='Color Input',
                                    node_group=GD_node_group,
                                    original_input=original_input,
                                    mat_slot=mat_slot
                                )
                            elif (
                                setup_type == Global.NG_ROUGHNESS_NAME \
                                and original_input.name == 'Roughness'
                            ):
                                node_found = bsdf_link_factory(
                                    input_name='Roughness Input',
                                    node_group=GD_node_group,
                                    original_input=original_input,
                                    mat_slot=mat_slot
                                )
                            elif (
                                setup_type == Global.NG_METALNESS_NAME \
                                and original_input.name == 'Metallic'
                            ):
                                node_found = bsdf_link_factory(
                                    input_name='Metalness Input',
                                    node_group=GD_node_group,
                                    original_input=original_input,
                                    mat_slot=mat_slot
                                )
                            elif (
                                setup_type == Global.NG_NORMAL_NAME \
                                and original_input.name in ('Normal', 'Alpha')
                            ):
                                node_found = bsdf_link_factory(
                                    input_name=original_input.name,
                                    node_group=GD_node_group,
                                    original_input=original_input,
                                    mat_slot=mat_slot
                                )

                                # Does not work if Map Preview
                                # Mode is entered and *then*
                                # Texture Normals are enabled
                                if (
                                    original_input.name == 'Alpha' \
                                    and context.scene.grabDoc.useTextureNormals\
                                    and mat_slot.blend_method == 'OPAQUE' \
                                    and len(original_input.links)
                                ):
                                    mat_slot.blend_method = 'CLIP'
                            elif node_found:
                                break

                        if (
                            not node_found \
                            and setup_type != Global.NG_NORMAL_NAME \
                            and mat_slot.name != Global.GD_MATERIAL_NAME
                        ):
                            self.report(
                                {'WARNING'},
                                Error.MAT_SLOTS_WITHOUT_LINKS
                            )

                for link in output.inputs['Volume'].links:
                    mat_slot.node_tree.links.remove(link)
                for link in output.inputs['Displacement'].links:
                    mat_slot.node_tree.links.remove(link)

                # Link Node Group to the output
                mat_slot.node_tree.links.new(
                    output.inputs["Surface"],
                    GD_node_group.outputs["Output"]
                )


def cleanup_ng_from_mat(setup_type: str) -> None:
    """Remove node group & return original links if they exist"""
    for mat in bpy.data.materials:
        mat.use_nodes = True

        # If there is a GrabDoc created material, remove it
        if mat.name == Global.GD_MATERIAL_NAME:
            bpy.data.materials.remove(mat)
            continue
        elif setup_type not in mat.node_tree.nodes:
            continue

        # If a material has a GrabDoc created Node Group, remove it
        GD_node_groups = [
            mat for mat in mat.node_tree.nodes if mat.name.startswith(
                setup_type
            )
        ]
        for GD_node_group in GD_node_groups:
            output = None
            for output in GD_node_group.outputs:
                for link in output.links:
                    if link.to_node.type == 'OUTPUT_MATERIAL':
                        output = link.to_node
                        break
                if output is not None:
                    break

            if output is None:
                mat.node_tree.nodes.remove(GD_node_group)
                continue

            for node_input in GD_node_group.inputs:
                for link in node_input.links:
                    original_node_connection = \
                        mat.node_tree.nodes.get(link.from_node.name)
                    original_node_socket = link.from_socket.name

                    # TODO: can be more modular
                    connections_to_make = \
                        ('Surface', 'Volume', 'Displacement')
                    if node_input.name.split(' ')[-1] in connections_to_make:
                        for connection_name in connections_to_make:
                            if node_input.name == f'Saved {connection_name}':
                                mat.node_tree.links.new(
                                    output.inputs[connection_name],
                                    original_node_connection.outputs[
                                        original_node_socket
                                    ]
                                )

            mat.node_tree.nodes.remove(GD_node_group)


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
