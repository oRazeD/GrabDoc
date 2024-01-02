from typing import Iterable

import bpy
from bpy.types import (
    Object,
    ShaderNodeGroup,
    NodeSocket,
    NodeTree,
    Material
)

from ..constants import GlobalVariableConstants as Global
from ..constants import ErrorCodeConstants as Error


def generate_ng_interface(tree: NodeTree, inputs: dict) -> None:
    tree.interface.new_socket(
        name="Shader",
        socket_type="NodeSocketShader",
        in_out='OUTPUT'
    )
    saved_links = tree.interface.new_panel(
        name="Saved Links",
        description="Stored links to restore original socket links later",
        default_closed=True
    )
    for name, socket_type in inputs.items():
        tree.interface.new_socket(
            name=name,
            parent=saved_links,
            socket_type=socket_type,
            in_out='INPUT'
        )


def get_shader_outputs() -> dict:
    material_output_inputs = {}
    tree = bpy.data.node_groups.new(
        'Material Output',
        'ShaderNodeTree'
    )
    output = tree.nodes.new(
        'ShaderNodeOutputMaterial'
    )
    material_output_inputs = {}
    for node_input in output.inputs:
        # NOTE: No clue what this input is for
        if node_input.name == 'Thickness':
            continue

        material_output_inputs[node_input.name] = \
            f'NodeSocket{node_input.type.capitalize()}'
    return material_output_inputs


def ng_setup() -> None:
    """Initial setup of all node groups when setting up a file"""
    gd = bpy.context.scene.gd

    # Get material output inputs
    inputs = get_shader_outputs()

    # Normals
    if not Global.NORMAL_NG_NAME in bpy.data.node_groups:
        tree = bpy.data.node_groups.new(
            Global.NORMAL_NG_NAME, 'ShaderNodeTree'
        )
        tree.use_fake_user = True

        # Create interface
        generate_ng_interface(tree, inputs)
        alpha = tree.interface.new_socket(
            name='Alpha',
            socket_type='NodeSocketFloat'
        )
        alpha.default_value = 1
        tree.interface.new_socket(
            name='Normal',
            socket_type='NodeSocketVector',
            in_out='INPUT'
        )

        # Create nodes
        group_output = tree.nodes.new('NodeGroupOutput')
        group_output.name = "Group Output"
        group_input = tree.nodes.new('NodeGroupInput')
        group_input.name = "Group Input"
        group_input.location = (-1400,100)

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
        vec_mult.inputs[1].default_value[1] = \
            -.5 if gd.normals[0].flip_y else .5
        vec_mult.inputs[1].default_value[2] = -.5
        vec_mult.location = (-600,0)

        vec_add = tree.nodes.new('ShaderNodeVectorMath')
        vec_add.name = "Vector Math.001"
        vec_add.inputs[1].default_value[0] = \
        vec_add.inputs[1].default_value[1] = \
        vec_add.inputs[1].default_value[2] = 0.5
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
        links = tree.links
        # NOTE: Branch 1
        links.new(bevel.inputs["Normal"], group_input.outputs["Normal"])
        links.new(vec_transform.inputs["Vector"], bevel_node_2.outputs["Normal"])
        links.new(vec_mult.inputs["Vector"], vec_transform.outputs["Vector"])
        links.new(vec_add.inputs["Vector"], vec_mult.outputs["Vector"])
        links.new(group_output.inputs["Shader"], vec_add.outputs["Vector"])
        # NOTE: Branch 2
        links.new(invert.inputs['Color'], group_input.outputs['Alpha'])
        links.new(subtract.inputs['Color2'], invert.outputs['Color'])
        links.new(mix_shader.inputs['Fac'], subtract.outputs['Color'])
        links.new(mix_shader.inputs[1], transp_shader.outputs['BSDF'])
        links.new(mix_shader.inputs[2], vec_add.outputs['Vector'])

    # Ambient Occlusion
    if not Global.AO_NG_NAME in bpy.data.node_groups:
        tree = bpy.data.node_groups.new(Global.AO_NG_NAME, 'ShaderNodeTree')
        tree.use_fake_user = True

        # Create sockets
        generate_ng_interface(tree, inputs)

        # Create nodes
        group_output = tree.nodes.new('NodeGroupOutput')
        group_output.name = "Group Output"

        ao = tree.nodes.new('ShaderNodeAmbientOcclusion')
        ao.name = "Ambient Occlusion"
        ao.samples = 32
        ao.location = (-600,0)

        gamma = tree.nodes.new('ShaderNodeGamma')
        gamma.name = "Gamma"
        gamma.inputs[1].default_value = gd.occlusion[0].gamma
        gamma.location = (-400,0)

        emission = tree.nodes.new('ShaderNodeEmission')
        emission.name = "Emission"
        emission.location = (-200,0)

        # Link nodes
        links = tree.links
        links.new(gamma.inputs["Color"], ao.outputs["Color"])
        links.new(emission.inputs["Color"], gamma.outputs["Color"])
        links.new(group_output.inputs["Shader"], emission.outputs["Emission"])

    # Height
    if not Global.HEIGHT_NG_NAME in bpy.data.node_groups:
        tree = bpy.data.node_groups.new(
            Global.HEIGHT_NG_NAME,
            'ShaderNodeTree'
        )
        tree.use_fake_user = True

        # Create sockets
        generate_ng_interface(tree, inputs)

        # Create nodes
        group_output = tree.nodes.new('NodeGroupOutput')
        group_output.name = "Group Output"

        camera = tree.nodes.new('ShaderNodeCameraData')
        camera.name = "Camera Data"
        camera.location = (-800,0)

        # NOTE: Map Range updates handled on map preview
        map_range = tree.nodes.new('ShaderNodeMapRange')
        map_range.name = "Map Range"
        map_range.location = (-600,0)

        ramp = tree.nodes.new('ShaderNodeValToRGB')
        ramp.name = "ColorRamp"
        ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
        ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
        ramp.location = (-400,0)

        # Link nodes
        links = tree.links
        links.new(map_range.inputs["Value"], camera.outputs["View Z Depth"])
        links.new(ramp.inputs["Fac"], map_range.outputs["Result"])
        links.new(group_output.inputs["Shader"], ramp.outputs["Color"])

    # Alpha
    if not Global.ALPHA_NG_NAME in bpy.data.node_groups:
        tree = bpy.data.node_groups.new(
            Global.ALPHA_NG_NAME,
            'ShaderNodeTree'
        )
        tree.use_fake_user = True

        # Create sockets
        generate_ng_interface(tree, inputs)

        # Create nodes
        group_output = tree.nodes.new('NodeGroupOutput')
        group_output.name = "Group Output"

        camera = tree.nodes.new('ShaderNodeCameraData')
        camera.name = "Camera Data"
        camera.location = (-800,0)

        camera_object_z = \
            bpy.data.objects.get(Global.TRIM_CAMERA_NAME).location[2]

        map_range = tree.nodes.new('ShaderNodeMapRange')
        map_range.name = "Map Range"
        map_range.location = (-600,0)
        map_range.inputs[1].default_value = camera_object_z - .00001
        map_range.inputs[2].default_value = camera_object_z

        invert = tree.nodes.new('ShaderNodeInvert')
        invert.name = "Invert"
        invert.location = (-400,0)

        emission = tree.nodes.new('ShaderNodeEmission')
        emission.name = "Emission"
        emission.location = (-200,0)

        # Link nodes
        links = tree.links
        links.new(map_range.inputs["Value"], camera.outputs["View Z Depth"])
        links.new(invert.inputs["Color"], map_range.outputs["Result"])
        links.new(emission.inputs["Color"], invert.outputs["Color"])
        links.new(group_output.inputs["Shader"], emission.outputs["Emission"])

    # Base Color
    if not Global.COLOR_NG_NAME in bpy.data.node_groups:
        tree = \
            bpy.data.node_groups.new(
                Global.COLOR_NG_NAME,
                'ShaderNodeTree'
            )
        tree.use_fake_user = True

        # Create sockets
        generate_ng_interface(tree, inputs)
        tree.interface.new_socket(
            name=Global.COLOR_NAME,
            socket_type='NodeSocketColor'
        )

        # Create nodes
        group_output = tree.nodes.new('NodeGroupOutput')
        group_output.name = "Group Output"
        group_input = tree.nodes.new('NodeGroupInput')
        group_input.name = "Group Input"
        group_input.location = (-400,0)

        emission = tree.nodes.new('ShaderNodeEmission')
        emission.name = "Emission"
        emission.location = (-200,0)

        # Link nodes
        links = tree.links
        links.new(emission.inputs["Color"], group_input.outputs["Base Color"])
        links.new(group_output.inputs["Shader"], emission.outputs["Emission"])

    # Roughness
    if not Global.ROUGHNESS_NG_NAME in bpy.data.node_groups:
        tree = bpy.data.node_groups.new(
                Global.ROUGHNESS_NG_NAME,
                'ShaderNodeTree'
            )
        tree.use_fake_user = True

        # Create sockets
        generate_ng_interface(tree, inputs)
        tree.interface.new_socket(
            name='Roughness',
            socket_type='NodeSocketFloat',
            in_out='INPUT'
        )

        # Create nodes
        group_output = tree.nodes.new('NodeGroupOutput')
        group_output.name = "Group Output"
        group_input = tree.nodes.new('NodeGroupInput')
        group_input.name = "Group Input"
        group_input.location = (-600,0)

        invert = tree.nodes.new('ShaderNodeInvert')
        invert.location = (-400,0)
        invert.inputs[0].default_value = 0

        emission = tree.nodes.new('ShaderNodeEmission')
        emission.name = "Emission"
        emission.location = (-200,0)

        # Link nodes
        links = tree.links
        links.new(
            invert.inputs["Color"],
            group_input.outputs["Roughness"]
        )
        links.new(
            emission.inputs["Color"],
            invert.outputs["Color"]
        )
        links.new(
            group_output.inputs["Shader"],
            emission.outputs["Emission"]
        )

    # Metalness
    if not Global.METALNESS_NG_NAME in bpy.data.node_groups:
        tree = \
            bpy.data.node_groups.new(
                Global.METALNESS_NG_NAME,
                'ShaderNodeTree'
            )
        tree.use_fake_user = True

        # Create sockets
        generate_ng_interface(tree, inputs)
        tree.interface.new_socket(
            name='Metalness',
            socket_type='NodeSocketFloat',
            in_out='INPUT'
        )

        # Create nodes
        group_output = tree.nodes.new('NodeGroupOutput')
        group_output.name = "Group Output"
        group_input = tree.nodes.new('NodeGroupInput')
        group_input.name = "Group Input"
        group_input.location = (-400,0)

        emission = tree.nodes.new('ShaderNodeEmission')
        emission.name = "Emission"
        emission.location = (-200,0)

        # Link nodes
        links = tree.links
        links.new(
            emission.inputs["Color"],
            group_input.outputs["Metalness"]
        )
        links.new(
            group_output.inputs["Shader"],
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


def create_bsdf_link(
        input_name: str,
        node_group: ShaderNodeGroup,
        original_input: NodeSocket,
        material: Material
    ) -> bool:
    """Add node group to given material slots and save original links"""
    node_found = False
    for link in original_input.links:
        node_found = True
        material.node_tree.links.new(
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


def add_ng_to_mat(name: str, objects: Iterable[Object]) -> None:
    """Add node group to given object material slots"""
    for ob in objects:
        # If no material slots found or empty mat
        # slots found, assign a material to it
        if not ob.material_slots or '' in ob.material_slots:
            create_apply_ng_mat(ob)

        # Cycle through all material slots
        for slot in ob.material_slots:
            material = bpy.data.materials.get(slot.name)
            material.use_nodes = True

            nodes = material.node_tree.nodes
            if name in nodes:
                continue

            # Get output material node(s)
            output_nodes = {
                mat for mat in nodes if mat.type == 'OUTPUT_MATERIAL'
            }
            if not output_nodes:
                output_nodes.append(
                    nodes.new('ShaderNodeOutputMaterial')
                )

            node_group = bpy.data.node_groups.get(name)
            for output in output_nodes:
                # Add node group to material
                passthrough_ng = nodes.new('ShaderNodeGroup')
                passthrough_ng.node_tree = node_group
                passthrough_ng.location = (
                    output.location[0],
                    output.location[1] - 160
                )
                passthrough_ng.name = node_group.name
                passthrough_ng.hide = True

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

                # Link nodes
                for output_material_input in output.inputs:
                    for link in output_material_input.links:
                        source_node = nodes.get(link.from_node.name)

                        # TODO: can be more modular
                        #connections_to_make = \
                        #    ('Surface', 'Volume', 'Displacement')
                        #if node_input.name in connections_to_make:
                        #    for connection_name in connections_to_make:
                        #        if node_input.name != connection_name:
                        #            continue
                        #        mat_slot.node_tree.links.new(
                        #            passthrough_ng.inputs[connection_name],
                        #            source_node.outputs[link.from_socket.name]
                        #        )

                        # Store original output material connections
                        try:
                            material.node_tree.links.new(
                                passthrough_ng.inputs[
                                    output_material_input.name
                                ],
                                source_node.outputs[link.from_socket.name]
                            )
                        except KeyError:
                            pass

                        # Link dependencies from any BSDF node
                        if name not in Global.SHADER_MAP_NAMES \
                        or "BSDF" not in source_node.type:
                            continue
                        node_found = False
                        for original_input in source_node.inputs:
                            if original_input.name not in Global.ALL_MAP_NAMES:
                                continue
                            if (
                                name == Global.COLOR_NG_NAME \
                                and original_input.name == Global.COLOR_NAME
                            ):
                                node_found = create_bsdf_link(
                                    input_name=original_input.name,
                                    node_group=passthrough_ng,
                                    original_input=original_input,
                                    material=material
                                )
                            elif (
                                name == Global.ROUGHNESS_NG_NAME \
                                and original_input.name == Global.ROUGHNESS_NAME
                            ):
                                node_found = create_bsdf_link(
                                    input_name=original_input.name,
                                    node_group=passthrough_ng,
                                    original_input=original_input,
                                    material=material
                                )
                            elif (
                                name == Global.METALNESS_NG_NAME \
                                and original_input.name == Global.METALNESS_NAME
                            ):
                                node_found = create_bsdf_link(
                                    input_name=original_input.name,
                                    node_group=passthrough_ng,
                                    original_input=original_input,
                                    material=material
                                )
                            if (
                                name in (Global.ALPHA_NG_NAME,
                                         Global.NORMAL_NG_NAME) \
                                and original_input.name in (Global.ALPHA_NAME,
                                                            Global.NORMAL_NAME)
                            ):
                                node_found = create_bsdf_link(
                                    input_name=original_input.name,
                                    node_group=passthrough_ng,
                                    original_input=original_input,
                                    material=material
                                )

                                # TODO: Does not work if Map Preview
                                # Mode is entered and *then*
                                # Texture Normals are enabled
                                if (
                                    original_input.name == 'Alpha' \
                                    and bpy.context.scene.gd.normals[0].use_texture \
                                    and material.blend_method == 'OPAQUE' \
                                    and len(original_input.links)
                                ):
                                    material.blend_method = 'CLIP'
                            elif node_found:
                                break

                        if (
                            not node_found \
                            and name != Global.NORMAL_NG_NAME \
                            and material.name != Global.GD_MATERIAL_NAME
                        ):
                            # TODO: Report on this to user...
                            print(Error.MAT_SLOTS_WITHOUT_LINKS)

                for link in output.inputs['Volume'].links:
                    material.node_tree.links.remove(link)
                for link in output.inputs['Displacement'].links:
                    material.node_tree.links.remove(link)

                material.node_tree.links.new(
                    output.inputs["Surface"],
                    passthrough_ng.outputs["Shader"]
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
                            if node_input.name == connection_name:
                                mat.node_tree.links.new(
                                    output.inputs[connection_name],
                                    original_node_connection.outputs[
                                        original_node_socket
                                    ]
                                )

            mat.node_tree.nodes.remove(GD_node_group)



