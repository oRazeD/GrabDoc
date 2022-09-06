
import bpy
from bpy import types as type
from .gd_constants import *


def ng_setup() -> None:
    '''Initial setup of all node groups when setting up a file'''
    grabDoc = bpy.context.scene.grabDoc

    # NORMALS
    if not NG_NORMAL_NAME in bpy.data.node_groups:
        ng_normal = bpy.data.node_groups.new(NG_NORMAL_NAME, 'ShaderNodeTree')
        ng_normal.use_fake_user = True

        # Create group inputs/outputs
        group_outputs = ng_normal.nodes.new('NodeGroupOutput')
        group_inputs = ng_normal.nodes.new('NodeGroupInput')
        group_inputs.location = (-1400,100)
        ng_normal.outputs.new('NodeSocketShader','Output')
        ng_normal.inputs.new('NodeSocketShader','Saved Surface')
        ng_normal.inputs.new('NodeSocketShader','Saved Volume')
        ng_normal.inputs.new('NodeSocketShader','Saved Displacement')
        alpha_input = ng_normal.inputs.new('NodeSocketInt','Alpha')
        alpha_input.default_value = 1
        ng_normal.inputs.new('NodeSocketVector','Normal')

        # Create group nodes
        bevel_node = ng_normal.nodes.new('ShaderNodeBevel')
        bevel_node.inputs[0].default_value = 0
        bevel_node.location = (-1000,0)

        bevel_node_2 = ng_normal.nodes.new('ShaderNodeBevel')
        bevel_node_2.location = (-1000,-200)
        bevel_node_2.inputs[0].default_value = 0

        vec_transform_node = ng_normal.nodes.new('ShaderNodeVectorTransform')
        vec_transform_node.vector_type = 'NORMAL'
        vec_transform_node.convert_to = 'CAMERA'
        vec_transform_node.location = (-800,0)

        vec_multiply_node = ng_normal.nodes.new('ShaderNodeVectorMath')
        vec_multiply_node.operation = 'MULTIPLY'
        vec_multiply_node.inputs[1].default_value[0] = .5
        vec_multiply_node.inputs[1].default_value[1] = -.5 if grabDoc.flipYNormals else .5
        vec_multiply_node.inputs[1].default_value[2] = -.5
        vec_multiply_node.location = (-600,0)

        vec_add_node = ng_normal.nodes.new('ShaderNodeVectorMath')
        vec_add_node.inputs[1].default_value[0] = vec_add_node.inputs[1].default_value[1] = vec_add_node.inputs[1].default_value[2] = 0.5
        vec_add_node.location = (-400,0)

        invert_node = ng_normal.nodes.new('ShaderNodeInvert')
        invert_node.location = (-1000,200)

        subtract_node = ng_normal.nodes.new('ShaderNodeMixRGB')
        subtract_node.blend_type = 'SUBTRACT'
        subtract_node.inputs[0].default_value = 1
        subtract_node.inputs[1].default_value = (1, 1, 1, 1)
        subtract_node.location = (-800,300)

        transp_shader_node = ng_normal.nodes.new('ShaderNodeBsdfTransparent')
        transp_shader_node.location = (-400,200)

        mix_shader_node = ng_normal.nodes.new('ShaderNodeMixShader')
        mix_shader_node.location = (-200,300)

        # Link nodes
        link = ng_normal.links

        # Path 1
        link.new(bevel_node.inputs["Normal"], group_inputs.outputs["Normal"])
        link.new(vec_transform_node.inputs["Vector"], bevel_node_2.outputs["Normal"])
        link.new(vec_multiply_node.inputs["Vector"], vec_transform_node.outputs["Vector"])
        link.new(vec_add_node.inputs["Vector"], vec_multiply_node.outputs["Vector"])
        link.new(group_outputs.inputs["Output"], vec_add_node.outputs["Vector"])

        # Path 2
        link.new(invert_node.inputs['Color'], group_inputs.outputs['Alpha'])
        link.new(subtract_node.inputs['Color2'], invert_node.outputs['Color'])
        link.new(mix_shader_node.inputs['Fac'], subtract_node.outputs['Color'])
        link.new(mix_shader_node.inputs[1], transp_shader_node.outputs['BSDF'])
        link.new(mix_shader_node.inputs[2], vec_add_node.outputs['Vector'])

    # AMBIENT OCCLUSION
    if not NG_AO_NAME in bpy.data.node_groups:
        ng_ao = bpy.data.node_groups.new(NG_AO_NAME, 'ShaderNodeTree')
        ng_ao.use_fake_user = True

        # Create group inputs/outputs
        group_outputs = ng_ao.nodes.new('NodeGroupOutput')
        ng_ao.outputs.new('NodeSocketShader','Output')
        ng_ao.inputs.new('NodeSocketShader','Saved Surface')
        ng_ao.inputs.new('NodeSocketShader','Saved Volume')
        ng_ao.inputs.new('NodeSocketShader','Saved Displacement')

        # Create group nodes
        ao_node = ng_ao.nodes.new('ShaderNodeAmbientOcclusion')
        ao_node.samples = 32
        ao_node.location = (-600,0)

        gamma_node = ng_ao.nodes.new('ShaderNodeGamma')
        gamma_node.inputs[1].default_value = grabDoc.gammaOcclusion
        gamma_node.location = (-400,0)

        emission_node = ng_ao.nodes.new('ShaderNodeEmission')
        emission_node.location = (-200,0)

        # Link nodes
        link = ng_ao.links
        link.new(gamma_node.inputs["Color"], ao_node.outputs["Color"])
        link.new(emission_node.inputs["Color"], gamma_node.outputs["Color"])
        link.new(group_outputs.inputs["Output"], emission_node.outputs["Emission"])

    # HEIGHT
    if not NG_HEIGHT_NAME in bpy.data.node_groups:
        ng_height = bpy.data.node_groups.new(NG_HEIGHT_NAME, 'ShaderNodeTree')
        ng_height.use_fake_user = True
    
        # Create group inputs/outputs
        group_outputs = ng_height.nodes.new('NodeGroupOutput')
        ng_height.outputs.new('NodeSocketShader','Output')
        ng_height.inputs.new('NodeSocketShader','Saved Surface')
        ng_height.inputs.new('NodeSocketShader','Saved Volume')
        ng_height.inputs.new('NodeSocketShader','Saved Displacement')

        # Create group nodes
        camera_data_node = ng_height.nodes.new('ShaderNodeCameraData')
        camera_data_node.location = (-800,0)

        map_range_node = ng_height.nodes.new('ShaderNodeMapRange') # Map Range updates handled on map preview
        map_range_node.location = (-600,0)

        ramp_node = ng_height.nodes.new('ShaderNodeValToRGB')
        ramp_node.color_ramp.elements[0].color = (1, 1, 1, 1)
        ramp_node.color_ramp.elements[1].color = (0, 0, 0, 1)
        ramp_node.location = (-400,0)

        # Link nodes
        link = ng_height.links
        link.new(map_range_node.inputs["Value"], camera_data_node.outputs["View Z Depth"])
        link.new(ramp_node.inputs["Fac"], map_range_node.outputs["Result"])
        link.new(group_outputs.inputs["Output"], ramp_node.outputs["Color"])

    # ALPHA
    if not NG_ALPHA_NAME in bpy.data.node_groups:
        ng_alpha = bpy.data.node_groups.new(NG_ALPHA_NAME, 'ShaderNodeTree')
        ng_alpha.use_fake_user = True
    
        # Create group input/outputs
        group_outputs = ng_alpha.nodes.new('NodeGroupOutput')
        ng_alpha.outputs.new('NodeSocketShader','Output')
        ng_alpha.inputs.new('NodeSocketShader','Saved Surface')
        ng_alpha.inputs.new('NodeSocketShader','Saved Volume')
        ng_alpha.inputs.new('NodeSocketShader','Saved Displacement')

        # Create group nodes
        camera_data_node = ng_alpha.nodes.new('ShaderNodeCameraData')
        camera_data_node.location = (-800,0)

        gd_camera_ob_z = bpy.data.objects.get(TRIM_CAMERA_NAME).location[2]

        map_range_node = ng_alpha.nodes.new('ShaderNodeMapRange')
        map_range_node.location = (-600,0)
        map_range_node.inputs[1].default_value = gd_camera_ob_z - .00001
        map_range_node.inputs[2].default_value = gd_camera_ob_z

        invert_node = ng_alpha.nodes.new('ShaderNodeInvert')
        invert_node.location = (-400,0)
        
        emission_node = ng_alpha.nodes.new('ShaderNodeEmission')
        emission_node.location = (-200,0)

        # Link nodes
        link = ng_alpha.links
        link.new(map_range_node.inputs["Value"], camera_data_node.outputs["View Z Depth"])
        link.new(invert_node.inputs["Color"], map_range_node.outputs["Result"])
        link.new(emission_node.inputs["Color"], invert_node.outputs["Color"])
        link.new(group_outputs.inputs["Output"], emission_node.outputs["Emission"])

    # ALBEDO
    if not NG_ALBEDO_NAME in bpy.data.node_groups:
        ng_albedo = bpy.data.node_groups.new(NG_ALBEDO_NAME, 'ShaderNodeTree')
        ng_albedo.use_fake_user = True
    
        # Create group inputs/outputs
        group_outputs = ng_albedo.nodes.new('NodeGroupOutput')
        group_inputs = ng_albedo.nodes.new('NodeGroupInput')
        group_inputs.location = (-400,0)
        ng_albedo.outputs.new('NodeSocketShader','Output')
        ng_albedo.inputs.new('NodeSocketColor', 'Color Input')
        ng_albedo.inputs.new('NodeSocketShader','Saved Surface')
        ng_albedo.inputs.new('NodeSocketShader','Saved Volume')
        ng_albedo.inputs.new('NodeSocketShader','Saved Displacement')
        
        emission_node = ng_albedo.nodes.new('ShaderNodeEmission')
        emission_node.location = (-200,0)

        # Link nodes
        link = ng_albedo.links
        link.new(emission_node.inputs["Color"], group_inputs.outputs["Color Input"])
        link.new(group_outputs.inputs["Output"], emission_node.outputs["Emission"])

    # ROUGHNESS
    if not NG_ROUGHNESS_NAME in bpy.data.node_groups:
        ng_roughness = bpy.data.node_groups.new(NG_ROUGHNESS_NAME, 'ShaderNodeTree')
        ng_roughness.use_fake_user = True
    
        # Create group inputs/outputs
        group_outputs = ng_roughness.nodes.new('NodeGroupOutput')
        group_inputs = ng_roughness.nodes.new('NodeGroupInput')
        group_inputs.location = (-400,0)
        ng_roughness.outputs.new('NodeSocketShader','Output')
        ng_roughness.inputs.new('NodeSocketFloat', 'Roughness Input')
        ng_roughness.inputs.new('NodeSocketShader','Saved Surface')
        ng_roughness.inputs.new('NodeSocketShader','Saved Volume')
        ng_roughness.inputs.new('NodeSocketShader','Saved Displacement')
        
        emission_node = ng_roughness.nodes.new('ShaderNodeEmission')
        emission_node.location = (-200,0)

        # Link nodes
        link = ng_roughness.links
        link.new(emission_node.inputs["Color"], group_inputs.outputs["Roughness Input"])
        link.new(group_outputs.inputs["Output"], emission_node.outputs["Emission"])

    # METALNESS
    if not NG_METALNESS_NAME in bpy.data.node_groups:
        ng_roughness = bpy.data.node_groups.new(NG_METALNESS_NAME, 'ShaderNodeTree')
        ng_roughness.use_fake_user = True
    
        # Create group inputs/outputs
        group_outputs = ng_roughness.nodes.new('NodeGroupOutput')
        group_inputs = ng_roughness.nodes.new('NodeGroupInput')
        group_inputs.location = (-400,0)
        ng_roughness.outputs.new('NodeSocketShader','Output')
        ng_roughness.inputs.new('NodeSocketFloat', 'Metalness Input')
        ng_roughness.inputs.new('NodeSocketShader','Saved Surface')
        ng_roughness.inputs.new('NodeSocketShader','Saved Volume')
        ng_roughness.inputs.new('NodeSocketShader','Saved Displacement')
        
        emission_node = ng_roughness.nodes.new('ShaderNodeEmission')
        emission_node.location = (-200,0)

        # Link nodes
        link = ng_roughness.links
        link.new(emission_node.inputs["Color"], group_inputs.outputs["Metalness Input"])
        link.new(group_outputs.inputs["Output"], emission_node.outputs["Emission"])


def create_apply_ng_mat(ob: type.Object) -> None:
    '''Create & apply a material to objects without active materials'''
    mat_name = GD_MATERIAL_NAME

    # Reuse GrabDoc created material if it already exists
    if mat_name in bpy.data.materials:
        mat = bpy.data.materials[mat_name]
    else:
        mat = bpy.data.materials.new(name = mat_name)

        mat.use_nodes = True

    # Apply the material to the appropriate slot
    #
    # Search through all material slots, if any slots have no name that means they have no material
    # & therefore should have one added. While this does run every time this is called it should
    # only really need to be used once per in add-on use.
    # 
    # We do not want to remove empty material slots as they can be used for masking off materials.
    for slot in ob.material_slots:
        if slot.name == '':
            ob.material_slots[slot.name].material = mat
    else:
        if not ob.active_material or ob.active_material.name == '':
            ob.active_material = mat


def bsdf_link_factory(input_name: list, node_group: type.ShaderNodeGroup, original_node_input: type.NodeSocket, mat_slot: type.Material) -> bool:
    '''Add node group to all materials, save original links & link the node group to material output'''
    node_found = False

    for link in original_node_input.links:
        node_found = True

        mat_slot.node_tree.links.new(node_group.inputs[input_name], link.from_node.outputs[link.from_socket.name])
        break
    else:
        try:
            node_group.inputs[input_name].default_value = original_node_input.default_value
        except TypeError:
            if isinstance(original_node_input.default_value, float):
                node_group.inputs[input_name].default_value = int(original_node_input.default_value)
            else:
                node_group.inputs[input_name].default_value = float(original_node_input.default_value)

    return node_found


def add_ng_to_mat(self, context, setup_type: str) -> None:
    '''Add corresponding node groups to all materials/objects'''
    for ob in context.view_layer.objects:
        if ob.name in self.rendered_obs and ob.name != ORIENT_GUIDE_NAME:
            # If no material slots found or empty mat slots found, assign a material to it
            if not len(ob.material_slots) or '' in ob.material_slots:
                create_apply_ng_mat(ob)

            # Cycle through all material slots
            for slot in ob.material_slots:
                mat_slot = bpy.data.materials.get(slot.name)
                mat_slot.use_nodes = True

                if setup_type in mat_slot.node_tree.nodes:
                    continue

                # Get materials Output Material node(s)
                output_nodes = [mat_node for mat_node in mat_slot.node_tree.nodes if mat_node.type == 'OUTPUT_MATERIAL']
                if not len(output_nodes):
                    output_nodes.append(mat_slot.node_tree.nodes.new('ShaderNodeOutputMaterial'))

                for output_node in output_nodes:
                    # Add node group to material
                    GD_node_group = mat_slot.node_tree.nodes.new('ShaderNodeGroup')
                    GD_node_group.node_tree = bpy.data.node_groups[setup_type]
                    GD_node_group.location = (output_node.location[0], output_node.location[1] - 160)
                    GD_node_group.name = bpy.data.node_groups[setup_type].name
                    GD_node_group.hide = True

                    # Handle node linking
                    for node_input in output_node.inputs:
                        for link in node_input.links:
                            original_node = mat_slot.node_tree.nodes.get(link.from_node.name)

                            # Link original connections to the Node Group
                            if node_input.name == 'Surface':
                                mat_slot.node_tree.links.new(
                                    GD_node_group.inputs["Saved Surface"],
                                    original_node.outputs[link.from_socket.name]
                                )
                            elif node_input.name == 'Volume':
                                mat_slot.node_tree.links.new(
                                    GD_node_group.inputs["Saved Volume"],
                                    original_node.outputs[link.from_socket.name]
                                )
                            elif node_input.name == 'Displacement':
                                mat_slot.node_tree.links.new(
                                    GD_node_group.inputs["Saved Displacement"],
                                    original_node.outputs[link.from_socket.name]
                                )

                            # Links for maps that feed information from the Principled BSDF
                            if setup_type in {NG_ALBEDO_NAME, NG_ROUGHNESS_NAME, NG_METALNESS_NAME, NG_NORMAL_NAME} and original_node.type == 'BSDF_PRINCIPLED':
                                node_found = False

                                for original_node_input in original_node.inputs:
                                    if setup_type == NG_ALBEDO_NAME and original_node_input.name == 'Base Color':
                                        node_found = bsdf_link_factory(
                                            input_name='Color Input',
                                            node_group=GD_node_group,
                                            original_node_input=original_node_input,
                                            mat_slot=mat_slot
                                        )

                                    elif setup_type == NG_ROUGHNESS_NAME and original_node_input.name == 'Roughness':
                                        node_found = bsdf_link_factory(
                                            input_name='Roughness Input',
                                            node_group=GD_node_group,
                                            original_node_input=original_node_input,
                                            mat_slot=mat_slot
                                        )

                                    elif setup_type == NG_METALNESS_NAME and original_node_input.name == 'Metallic':
                                        node_found = bsdf_link_factory(
                                            input_name='Metalness Input',
                                            node_group=GD_node_group,
                                            original_node_input=original_node_input,
                                            mat_slot=mat_slot
                                        )

                                    elif setup_type == NG_NORMAL_NAME and original_node_input.name in {'Normal', 'Alpha'}:
                                        node_found = bsdf_link_factory(
                                            input_name=original_node_input.name,
                                            node_group=GD_node_group,
                                            original_node_input=original_node_input,
                                            mat_slot=mat_slot
                                        )

                                        if ( # Does not work if Map Preview Mode is entered and *then* Texture Normals are enabled
                                            original_node_input.name == 'Alpha'
                                            and context.scene.grabDoc.useTextureNormals
                                            and mat_slot.blend_method == 'OPAQUE'
                                            and len(original_node_input.links)
                                        ):
                                            mat_slot.blend_method = 'CLIP'

                                    elif node_found:
                                        break

                                if not node_found and setup_type != NG_NORMAL_NAME:
                                    self.report({'WARNING'}, "Material slots found without links & will be rendered using the sockets default value.")

                    # Remove existing links on the output node
                    if len(output_node.inputs['Volume'].links):
                        for link in output_node.inputs['Volume'].links:
                            mat_slot.node_tree.links.remove(link)

                    if len(output_node.inputs['Displacement'].links):
                        for link in output_node.inputs['Displacement'].links:
                            mat_slot.node_tree.links.remove(link)

                    # Link Node Group to the output
                    mat_slot.node_tree.links.new(output_node.inputs["Surface"], GD_node_group.outputs["Output"])


def cleanup_ng_from_mat(setup_type: str) -> None:
    '''Remove node group & return original links if they exist'''
    for mat in bpy.data.materials:
        mat.use_nodes = True
        
        # If there is a GrabDoc created material, remove it
        if mat.name == GD_MATERIAL_NAME:
            bpy.data.materials.remove(mat)
            continue
        elif setup_type not in mat.node_tree.nodes:
            continue
        
        # If a material has a GrabDoc created Node Group, remove it
        GD_node_groups = [mat_node for mat_node in mat.node_tree.nodes if mat_node.name.startswith(setup_type)]
        for GD_node_group in GD_node_groups:
            output_node = None
            for output in GD_node_group.outputs:
                for link in output.links:
                    if link.to_node.type == 'OUTPUT_MATERIAL':
                        output_node = link.to_node
                        break
                if output_node is not None:
                    break

            if output_node is None:
                mat.node_tree.nodes.remove(GD_node_group)
                continue

            for input in GD_node_group.inputs:
                for link in input.links:
                    original_node_connection = mat.node_tree.nodes.get(link.from_node.name)
                    original_node_socket = link.from_socket.name

                    if input.name == 'Saved Surface':
                        mat.node_tree.links.new(
                            output_node.inputs["Surface"],
                            original_node_connection.outputs[original_node_socket]
                        )
                    elif input.name == 'Saved Volume':
                        mat.node_tree.links.new(
                            output_node.inputs["Volume"],
                            original_node_connection.outputs[original_node_socket]
                        )
                    elif input.name == 'Saved Displacement':
                        mat.node_tree.links.new(
                            output_node.inputs["Displacement"],
                            original_node_connection.outputs[original_node_socket]
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
