
import bpy


def ng_setup(self, context):
    grabDoc = context.scene.grabDoc

    # NORMALS
    if not 'GD_Normal' in bpy.data.node_groups:
        # Create node group
        ng_normal = bpy.data.node_groups.new('GD_Normal', 'ShaderNodeTree')
        ng_normal.use_fake_user = True

        # Create group outputs
        group_outputs = ng_normal.nodes.new('NodeGroupOutput')
        ng_normal.outputs.new('NodeSocketShader','Output')
        ng_normal.inputs.new('NodeSocketShader','Saved Surface')
        ng_normal.inputs.new('NodeSocketShader','Saved Volume')
        ng_normal.inputs.new('NodeSocketShader','Saved Displacement')

        # Create group nodes
        geo_node = ng_normal.nodes.new('ShaderNodeNewGeometry')
        geo_node.location = (-800,0)

        vec_transform_node = ng_normal.nodes.new('ShaderNodeVectorTransform')
        vec_transform_node.vector_type = 'NORMAL'
        vec_transform_node.convert_to = 'CAMERA'
        vec_transform_node.location = (-600,0)

        vec_multiply_node = ng_normal.nodes.new('ShaderNodeVectorMath')
        vec_multiply_node.operation = 'MULTIPLY'
        vec_multiply_node.inputs[1].default_value[0] = .5
        vec_multiply_node.inputs[1].default_value[1] = -.5 if grabDoc.flipYNormals else .5
        vec_multiply_node.inputs[1].default_value[2] = -.5
        vec_multiply_node.location = (-400,0)

        vec_add_node = ng_normal.nodes.new('ShaderNodeVectorMath')
        vec_add_node.inputs[1].default_value[0] = vec_add_node.inputs[1].default_value[1] = vec_add_node.inputs[1].default_value[2] = 0.5
        vec_add_node.location = (-200,0)

        # Link nodes
        link = ng_normal.links

        link.new(vec_transform_node.inputs["Vector"], geo_node.outputs["Normal"])
        link.new(vec_multiply_node.inputs["Vector"], vec_transform_node.outputs["Vector"])
        link.new(vec_add_node.inputs["Vector"], vec_multiply_node.outputs["Vector"])
        link.new(group_outputs.inputs["Output"], vec_add_node.outputs["Vector"])

    # AMBIENT OCCLUSION
    if not 'GD_Ambient Occlusion' in bpy.data.node_groups:
        # Create node group
        ng_ao = bpy.data.node_groups.new('GD_Ambient Occlusion', 'ShaderNodeTree')
        ng_ao.use_fake_user = True

        # Create group outputs
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

        # Link materials
        link = ng_ao.links

        link.new(gamma_node.inputs["Color"], ao_node.outputs["Color"])
        link.new(emission_node.inputs["Color"], gamma_node.outputs["Color"])
        link.new(group_outputs.inputs["Output"], emission_node.outputs["Emission"])

    # HEIGHT
    if not 'GD_Height' in bpy.data.node_groups:
        # Create node group
        ng_height = bpy.data.node_groups.new('GD_Height', 'ShaderNodeTree')
        ng_height.use_fake_user = True
    
        # Create group outputs
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

        # Link materials
        link = ng_height.links

        link.new(map_range_node.inputs["Value"], camera_data_node.outputs["View Z Depth"])
        link.new(ramp_node.inputs["Fac"], map_range_node.outputs["Result"])
        link.new(group_outputs.inputs["Output"], ramp_node.outputs["Color"])

    # ALPHA
    if not 'GD_Alpha' in bpy.data.node_groups:
        # Create node group
        ng_alpha = bpy.data.node_groups.new('GD_Alpha', 'ShaderNodeTree')
        ng_alpha.use_fake_user = True
    
        # Create group outputs
        group_outputs = ng_alpha.nodes.new('NodeGroupOutput')
        ng_alpha.outputs.new('NodeSocketShader','Output')
        ng_alpha.inputs.new('NodeSocketShader','Saved Surface')
        ng_alpha.inputs.new('NodeSocketShader','Saved Volume')
        ng_alpha.inputs.new('NodeSocketShader','Saved Displacement')

        # Create group nodes
        camera_data_node = ng_alpha.nodes.new('ShaderNodeCameraData')
        camera_data_node.location = (-800,0)

        gd_camera_ob_z = bpy.data.objects.get('GD_Trim Camera').location[2]

        map_range_node = ng_alpha.nodes.new('ShaderNodeMapRange')
        map_range_node.location = (-600,0)

        map_range_node = bpy.data.node_groups["GD_Alpha"].nodes.get('Map Range')
        map_range_node.inputs[1].default_value = gd_camera_ob_z - .00001
        map_range_node.inputs[2].default_value = gd_camera_ob_z

        invert_node = ng_alpha.nodes.new('ShaderNodeInvert')
        invert_node.location = (-400,0)
        
        emission_node = ng_alpha.nodes.new('ShaderNodeEmission')
        emission_node.location = (-200,0)

        # Link materials
        link = ng_alpha.links

        link.new(map_range_node.inputs["Value"], camera_data_node.outputs["View Z Depth"])
        link.new(invert_node.inputs["Color"], map_range_node.outputs["Result"])
        link.new(emission_node.inputs["Color"], invert_node.outputs["Color"])
        link.new(group_outputs.inputs["Output"], emission_node.outputs["Emission"])


# CREATE & APPLY A MATERIAL TO OBJECTS WITHOUT ACTIVE MATERIALS
def create_apply_ng_mat(self, context):
    mat_name = 'GD_Material (do not touch contents)'

    # Reuse GrabDoc created material if it already exists
    if mat_name in bpy.data.materials:
        self.mat = bpy.data.materials[mat_name]
        mat = self.mat
    else:
        # Create a material
        self.mat = bpy.data.materials.new(name = mat_name)
        mat = self.mat

        mat.use_nodes = True
        
        # Remove unnecessary BSDF node
        mat.node_tree.nodes.remove(mat.node_tree.nodes.get('Principled BSDF'))

    # Apply the material to the appropriate slot
    #
    # Search through all material slots, if any slots have no name that means they have no material
    # & therefore should have one added. While this does need to run every time this is called it 
    # should only really need to be used once per in add-on use. We do not want to remove empty
    # material slots as they can be used for masking off materials.
    for slot in self.ob.material_slots:
        if slot.name == '':
            self.ob.material_slots[slot.name].material = mat
    else:
        if not self.ob.active_material or self.ob.active_material.name == '':
            self.ob.active_material = mat


# ADD NODE GROUP TO ALL MATERIALS, SAVE ORIGINAL LINKS & LINK NODE GROUP TO MATERIAL OUTPUT
def add_ng_to_mat(self, context, setup_type):
    for self.ob in context.view_layer.objects:
        if self.ob.name in self.render_list:
            ob = self.ob

            if ob.name != "GD_Orient Guide":
                # If no material slots found or empty mat slots found, assign a material to it
                if not len(ob.material_slots) or '' in ob.material_slots:
                    create_apply_ng_mat(self, context)

                # Cycle through all material slots
                for slot in ob.material_slots:
                    mat_slot = bpy.data.materials.get(slot.name)

                    output_node = None
                    original_node = None

                    if not mat_slot.use_nodes:
                        mat_slot.use_nodes = True

                    if not setup_type in mat_slot.node_tree.nodes:
                        # Get materials Output Material node
                        for mat_node in mat_slot.node_tree.nodes:
                            if mat_node.type == 'OUTPUT_MATERIAL' and mat_node.is_active_output:
                                output_node = mat_slot.node_tree.nodes.get(mat_node.name)
                                break

                        if not output_node:
                            output_node = mat_slot.node_tree.nodes.new('ShaderNodeOutputMaterial')

                        # Add node group to material
                        GD_node_group = mat_slot.node_tree.nodes.new('ShaderNodeGroup')
                        GD_node_group.node_tree = bpy.data.node_groups[setup_type]
                        GD_node_group.location = (output_node.location[0], output_node.location[1] - 140)
                        GD_node_group.name = bpy.data.node_groups[setup_type].name
                        GD_node_group.hide = True

                        # Get the original node link (if it exists)
                        for node_input in output_node.inputs:
                            for link in node_input.links:
                                original_node = mat_slot.node_tree.nodes.get(link.from_node.name)

                                # Link original connection to the Node Group
                                if node_input.name == 'Surface':
                                    mat_slot.node_tree.links.new(GD_node_group.inputs["Saved Surface"], original_node.outputs[link.from_socket.name])
                                elif node_input.name == 'Volume':
                                    mat_slot.node_tree.links.new(GD_node_group.inputs["Saved Volume"], original_node.outputs[link.from_socket.name])
                                elif node_input.name == 'Displacement':
                                    mat_slot.node_tree.links.new(GD_node_group.inputs["Saved Displacement"], original_node.outputs[link.from_socket.name])

                        # Remove existing links on the output node
                        if len(output_node.inputs['Volume'].links):
                            for link in output_node.inputs['Volume'].links:
                                mat_slot.node_tree.links.remove(link)

                        if len(output_node.inputs['Displacement'].links):
                            for link in output_node.inputs['Displacement'].links:
                                mat_slot.node_tree.links.remove(link)

                        # Link Node Group to the output
                        mat_slot.node_tree.links.new(output_node.inputs["Surface"], GD_node_group.outputs["Output"])


# REMOVE NODE GROUP & RETURN ORIGINAL LINKS IF THEY EXIST
def cleanup_ng_from_mat(self, context, setup_type):
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            mat.use_nodes = True
        
        # If there is a GrabDoc created material, remove it
        if mat.name == 'GD_Material (do not touch contents)':
            bpy.data.materials.remove(mat)

        # If a material has a GrabDoc created Node Group, remove it
        elif setup_type in mat.node_tree.nodes:
            for mat_node in mat.node_tree.nodes:
                if mat_node.type == 'OUTPUT_MATERIAL' and mat_node.is_active_output:
                    output_node = mat.node_tree.nodes.get(mat_node.name)
                    break

            GD_node_group = mat.node_tree.nodes.get(setup_type)

            for input in GD_node_group.inputs:
                for link in input.links:
                    original_node_connection = mat.node_tree.nodes.get(link.from_node.name)
                    original_node_socket = link.from_socket.name

                    if input.name == 'Saved Surface':
                        mat.node_tree.links.new(output_node.inputs["Surface"], original_node_connection.outputs[original_node_socket])
                    elif input.name == 'Saved Volume':
                        mat.node_tree.links.new(output_node.inputs["Volume"], original_node_connection.outputs[original_node_socket])
                    elif input.name == 'Saved Displacement':
                        mat.node_tree.links.new(output_node.inputs["Displacement"], original_node_connection.outputs[original_node_socket])
            
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
