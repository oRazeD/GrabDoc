import bpy
from bpy.types import Object, NodeTree, NodeTreeInterfaceItem

from ..constants import Global


def node_cleanup(node_tree: NodeTree) -> None:
    """Remove node group and return original links if they exist"""
    inputs = get_material_output_sockets()
    for mat in bpy.data.materials:
        mat.use_nodes = True
        if mat.name == Global.GD_MATERIAL_NAME:
            bpy.data.materials.remove(mat)
            continue
        nodes = mat.node_tree.nodes
        if node_tree.name not in nodes:
            continue

        # Get node group in material
        gd_nodes = [node for node in nodes if node.gd_spawn is True]
        for gd_node in gd_nodes:
            if gd_node.type != 'FRAME':
                node = gd_node
                break
        output_node = None
        for output in node.outputs:
            for link in output.links:
                if link.to_node.type != 'OUTPUT_MATERIAL':
                    continue
                output_node = link.to_node
                break
        if output_node is None:
            for gd_node in gd_nodes:
                nodes.remove(gd_node)
            continue

        # Return original connections
        for node_input in node.inputs:
            for link in node_input.links:
                if node_input.name.split(' ')[-1] not in inputs:
                    continue
                original_node_connection = nodes.get(link.from_node.name)
                original_node_socket = link.from_socket.name
                for connection_name in inputs:
                    if node_input.name != connection_name:
                        continue
                    mat.node_tree.links.new(
                        output_node.inputs[connection_name],
                        original_node_connection.outputs[original_node_socket]
                    )

        warning_text = bpy.data.texts.get(Global.NODE_GROUP_WARN_NAME)
        if warning_text is not None:
            bpy.data.texts.remove(warning_text)
        for gd_node in gd_nodes:
            nodes.remove(gd_node)


def get_material_output_sockets() -> dict:
    """Create a dummy node group if none is supplied and
    capture the default material output sockets/`inputs`."""
    tree = bpy.data.node_groups.new('Material Output', 'ShaderNodeTree')
    output = tree.nodes.new('ShaderNodeOutputMaterial')
    material_output_sockets = {}
    for node_input in output.inputs:
        node_type = node_input.type.capitalize()
        if node_input.type == "VALUE":
            node_type = "Float"
        bpy_node_type = f'NodeSocket{node_type}'
        material_output_sockets[node_input.name] = bpy_node_type
    bpy.data.node_groups.remove(tree)
    return material_output_sockets


def get_group_inputs(
        node_tree: NodeTree, remove_cache: bool=True
    ) -> list[NodeTreeInterfaceItem]:
    """Get the interface inputs of a given `NodeTree`."""
    inputs = []
    for item in node_tree.interface.items_tree:
        if not hasattr(item, 'in_out') \
        or item.in_out != 'INPUT':
            continue
        inputs.append(item)
    if remove_cache:
        inputs = inputs[:-4]
    return inputs


def link_group_to_object(ob: Object, node_tree: NodeTree) -> list[str]:
    """Add given `NodeTree` to the objects' material slots.

    Handles cases with empty or no material slots.

    Returns list of socket names without links."""
    if not ob.material_slots or "" in ob.material_slots:
        if Global.GD_MATERIAL_NAME in bpy.data.materials:
            mat = bpy.data.materials[Global.GD_MATERIAL_NAME]
        else:
            mat = bpy.data.materials.new(name=Global.GD_MATERIAL_NAME)
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes['Principled BSDF']
            bsdf.inputs["Emission Color"].default_value = (0,0,0,1)

        # NOTE: Do not remove empty slots as they are used in geometry masking
        for slot in ob.material_slots:
            if slot.name == '':
                ob.material_slots[slot.name].material = mat
        if not ob.active_material or ob.active_material.name == '':
            ob.active_material = mat

    inputs                         = get_group_inputs(node_tree)
    input_names:         list[str] = [node_input.name for node_input in inputs]
    unlinked: dict[str, list[str]] = {}

    for slot in ob.material_slots:
        material = bpy.data.materials.get(slot.name)
        material.use_nodes = True
        nodes = material.node_tree.nodes
        if node_tree.name in nodes:
            continue
        if material.name.startswith(Global.FLAG_PREFIX):
            unlinked[material.name] = []
        else:
            unlinked[material.name] = input_names

        output = None
        output_nodes = [mat for mat in nodes if mat.type == 'OUTPUT_MATERIAL']
        for output_node in output_nodes:
            if output_node.is_active_output:
                output = output_node
                break
        if output is None:
            output = nodes.new('ShaderNodeOutputMaterial')

        node_group           = nodes.new('ShaderNodeGroup')
        node_group.hide      = True
        node_group.gd_spawn  = True
        node_group.node_tree = node_tree
        node_group.name      = node_tree.name
        node_group.location  = (output.location[0], output.location[1] - 160)

        warning_text = bpy.data.texts.get(Global.NODE_GROUP_WARN_NAME)
        if warning_text is None:
            warning_text = bpy.data.texts.new(Global.NODE_GROUP_WARN_NAME)
            warning_text.write(Global.NODE_GROUP_WARN)
        frame          = nodes.new('NodeFrame')
        frame.name     = node_tree.name
        frame.width    = 750
        frame.height   = 200
        frame.gd_spawn = True
        frame.location = (output.location[0], output.location[1] - 200)
        frame.text     = warning_text

        # Link identical outputs from BSDF to output node
        from_output_node = output.inputs[0].links[0].from_node
        for node_input in from_output_node.inputs:
            if node_input.name not in input_names or not node_input.links:
                continue
            link = node_input.links[0]
            material.node_tree.links.new(
                node_group.inputs[node_input.name],
                link.from_node.outputs[link.from_socket.name]
            )
            if node_input.name in unlinked[material.name]:
                unlinked[material.name].remove(node_input.name)

        # Link matching input names from BSDF to baker
        for node_input in output.inputs:
            for link in node_input.links:
                material.node_tree.links.new(
                    node_group.inputs[node_input.name],
                    link.from_node.outputs[link.from_socket.name]
                )
                material.node_tree.links.remove(link)
        material.node_tree.links.new(output.inputs["Surface"],
                                     node_group.outputs["Shader"])

    # NOTE: Collapse found unlinked sockets into flat list
    unlinked_names = set()
    for input_names in unlinked.values():
        for name in input_names:
            unlinked_names.add(name)
    return list(unlinked_names)


def generate_shader_interface(
    tree: NodeTree, inputs: dict[str, str],
    name: str = "Output Cache", hidden: bool=True
) -> None:
    """Add sockets to a new panel in a given `NodeTree`
    and expected input of sockets. Defaults to `Shader` output.

    Generally used alongside other automation
    for creating reusable node input schemes.

    Dict formatting example:
      {'Displacement': 'NodeSocketVector'} (Name: Type)"""
    if name in tree.interface.items_tree:
        return
    saved_links = tree.interface.new_panel(name, default_closed=hidden)
    for socket_name, socket_type in inputs.items():
        tree.interface.new_socket(name=socket_name, parent=saved_links,
                                  socket_type=socket_type)
    if "Shader" in tree.interface.items_tree:
        return
    tree.interface.new_socket(name="Shader", socket_type="NodeSocketShader",
                              in_out='OUTPUT')
