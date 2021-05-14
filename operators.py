
import bpy
import time
import os
import bgl
import blf
from bpy.types import Operator
from bpy.props import EnumProperty, BoolProperty
import traceback
from random import random, randint
from mathutils import Vector, Color
import subprocess
import json
import bmesh


################################################################################################################
# GENERIC OPERATORS
################################################################################################################


class OpInfo:
    bl_options = {'REGISTER', 'UNDO'}


class GRABDOC_OT_load_ref(OpInfo, Operator):
    bl_idname = "grab_doc.load_ref"
    bl_label = "Load Reference"
    bl_description = "Loads a reference onto the background plane"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        # Load a new image into the main database
        bpy.data.images.load(self.filepath, check_existing=True)

        context.scene.grabDoc.refSelection = bpy.data.images[os.path.basename(os.path.normpath(self.filepath))]
        return{'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class GRABDOC_OT_open_folder(OpInfo, Operator):
    bl_idname = "grab_doc.open_folder"
    bl_label = "Open Folder"
    bl_description = "Opens up the File Explorer with the designated folder location"

    def execute(self, context):
        try:
            bpy.ops.wm.path_open(filepath = context.scene.grabDoc.exportPath)
        except RuntimeError:
            self.report({'ERROR'}, "No valid file path set")
        return{'FINISHED'}


class GRABDOC_OT_view_cam(OpInfo, Operator):
    bl_idname = "grab_doc.view_cam"
    bl_label = "View Trim Camera"
    bl_description = "View the scenes Trim Camera"

    from_modal: BoolProperty(default = False, options={'HIDDEN'})

    def execute(self, context):
        context.scene.camera = bpy.data.objects["GD_Trim Camera"]
        
        try:
            if self.from_modal:
                if [area.spaces.active.region_3d.view_perspective for area in context.screen.areas if area.type == 'VIEW_3D'] == ['CAMERA']:
                    bpy.ops.view3d.view_camera()
            else:
                bpy.ops.view3d.view_camera()
        except:
            traceback.print_exc()
            self.report({'ERROR'}, "Exit camera failed, please contact the developer with the error code listed in the console. ethan.simon.3d@gmail.com")

        self.from_modal = False
        return{'FINISHED'}


################################################################################################################
# SCENE SETUP
################################################################################################################


class GRABDOC_OT_setup_scene(Operator):
    bl_idname = "grab_doc.setup_scene"
    bl_label = "Setup / Refresh Scene"
    bl_description = "Setup/Refresh your current scene. Useful if you messed up something within the GrabDoc collections that you don't know how to perfectly revert" 
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene_refresh(self, context)
        return{'FINISHED'}


class GRABDOC_OT_remove_setup(Operator):
    bl_idname = "grab_doc.remove_setup"
    bl_label = "Remove Setup"
    bl_description = "Completely removes every element of GrabDoc from the scene, not including images reimported after bakes" 
    bl_options = {'REGISTER'}

    def execute(self, context):
        # Remove Node Groups
        if 'GD_Normals' in bpy.data.node_groups:
            bpy.data.node_groups.remove(bpy.data.node_groups["GD_Normals"])

        if 'GD_Height' in bpy.data.node_groups:
            bpy.data.node_groups.remove(bpy.data.node_groups["GD_Height"])

        if 'GD_Ambient Occlusion' in bpy.data.node_groups:
            bpy.data.node_groups.remove(bpy.data.node_groups["GD_Ambient Occlusion"])

        # Remove collections
        if "GrabDoc (do not touch contents)" in bpy.data.collections:
            bpy.data.collections.remove(bpy.data.collections["GrabDoc (do not touch contents)"])

        if "GrabDoc Objects (put objects here)" in bpy.data.collections:
            objectsColl = "GrabDoc Objects (put objects here)"

            if "GrabDoc Objects (put objects here)" in bpy.data.collections:
                for ob in bpy.data.collections[objectsColl].all_objects:
                    # Move object to the master collection
                    context.scene.collection.objects.link(ob)
                    # Remove the objects from the grabdoc collection
                    bpy.data.collections[objectsColl].objects.unlink(ob)

            bpy.data.collections.remove(bpy.data.collections[objectsColl])
        
        # Remove image ref
        if "GD_Reference" in bpy.data.materials:
            bpy.data.materials.remove(bpy.data.materials["GD_Reference"])

        # Remove bg plane
        if "GD_Background Plane" in bpy.data.objects:
            bpy.data.meshes.remove(bpy.data.objects["GD_Background Plane"].data)

        # Remove camera
        if "GD_Trim Camera" in bpy.data.cameras:
            bpy.data.cameras.remove(bpy.data.cameras["GD_Trim Camera"])

        # Remove height guide
        if "GD_Height Guide" in bpy.data.objects:
            bpy.data.meshes.remove(bpy.data.objects["GD_Height Guide"].data)

        # Remove orient guide
        if "GD_Orient Guide" in bpy.data.objects:
            bpy.data.meshes.remove(bpy.data.objects["GD_Orient Guide"].data)
        return{'FINISHED'}


def scene_refresh(self, context):
    # PRELIMINARY

    grabDoc = context.scene.grabDoc

    savedActiveColl = context.view_layer.active_layer_collection
    selectedCallback = context.view_layer.objects.selected.keys()

    if context.active_object:
        if context.object.type in {'MESH', 'CURVE', 'FONT', 'SURFACE', 'META', 'LATTICE', 'ARMATURE', 'CAMERA'}:
            activeCallback = context.active_object.name

            modeCallback = context.object.mode
            
            bpy.ops.object.mode_set(mode = 'OBJECT')
    else:
        activeCallback = None

    # Deselect all objects
    for ob in context.selected_objects:
        ob.select_set(False)

    # Set - Scene resolution (Trying to avoid destructively changing values, but this is one that needs to be changed)
    context.scene.render.resolution_x = grabDoc.exportResX
    context.scene.render.resolution_y = grabDoc.exportResY
    
    # NODE GROUPS

    ng_setup(self, context)

    # COLLECTIONS

    # Do some checks to see if the user wants to only render out the objects in a specific collection (for perf reasons)
    objectsColl = "GrabDoc Objects (put objects here)"

    if context.scene.grabDoc.onlyRenderColl:
        if not objectsColl in bpy.data.collections:
            bpy.data.collections.new(name = objectsColl)
            context.scene.collection.children.link(bpy.data.collections[objectsColl])
            context.view_layer.active_layer_collection = context.view_layer.layer_collection.children[-1]
    else:
        if objectsColl in bpy.data.collections:
            for ob in bpy.data.collections[objectsColl].all_objects:
                # Move object to the master collection
                context.scene.collection.objects.link(ob)
                # Remove the objects from the grabdoc collection
                bpy.data.collections[objectsColl].objects.unlink(ob)

            # Delete the collection
            bpy.data.collections.remove(bpy.data.collections[objectsColl])

    # Create main GrabDoc collection
    if "GrabDoc (do not touch contents)" in bpy.data.collections:
        bpy.data.collections.remove(bpy.data.collections["GrabDoc (do not touch contents)"])

    grabDocColl = bpy.data.collections.new(name = "GrabDoc (do not touch contents)")
    context.scene.collection.children.link(grabDocColl)
    context.view_layer.active_layer_collection = context.view_layer.layer_collection.children[-1]

    # Make the GrabDoc collection the active one
    context.view_layer.active_layer_collection = context.view_layer.layer_collection.children[grabDocColl.name]

    # BG PLANE

    # Remove pre existing BG Plane & all related data blocks 
    if "GD_Background Plane" in bpy.data.objects:
        # Grab the existing plane_ob & mesh
        plane_ob_old = bpy.data.objects["GD_Background Plane"]

        # Save original location & rotation
        plane_ob_old_loc = plane_ob_old.location
        plane_ob_old_rot = plane_ob_old.rotation_euler

        # Save plane_ob material
        saved_mat = plane_ob_old.active_material
    
        bpy.data.meshes.remove(plane_ob_old.data)
    else:
        plane_ob_old_loc = plane_ob_old_rot = (0, 0, 0)
    
    bpy.ops.mesh.primitive_plane_add(size=grabDoc.scalingSet, enter_editmode=False, calc_uvs=True, align='WORLD', location=(plane_ob_old_loc), rotation=(plane_ob_old_rot))

    # Rename newly made BG Plane & set a reference to it
    context.object.name = context.object.data.name = "GD_Background Plane"
    plane_ob = bpy.data.objects["GD_Background Plane"]

    # Prepare proper plane scaling & create the new plane object
    if grabDoc.exportResX != grabDoc.exportResY:
        if grabDoc.exportResX > grabDoc.exportResY:
            div_factor = grabDoc.exportResX / grabDoc.exportResY

            plane_ob.scale[1] /= div_factor
        else:
            div_factor = grabDoc.exportResY / grabDoc.exportResX

            plane_ob.scale[0] /= div_factor

        bpy.ops.object.transform_apply(location=False, rotation=False)
    
    plane_ob.select_set(False)
        
    # Lock the BG Plane's scaling
    plane_ob.lock_scale[0] = plane_ob.lock_scale[1] = plane_ob.lock_scale[2] = True

    # Add reference to the plane if one exists
    if grabDoc.refSelection and not grabDoc.modalState:
        for mat in bpy.data.materials:
            if mat.name == "GD_Reference":
                mat.node_tree.nodes.get('Image Texture').image = grabDoc.refSelection
                break
        else:
            # Create a new material & turn on node use
            mat = bpy.data.materials.new("GD_Reference")
            mat.use_nodes = True

            # Get / load nodes
            output_node = mat.node_tree.nodes.get('Material Output')
            output_node.location = (0,0)

            mat.node_tree.nodes.remove(mat.node_tree.nodes.get('Principled BSDF'))

            image_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
            image_node.image = grabDoc.refSelection
            image_node.location = (-300,0)

            # Link materials
            links = mat.node_tree.links

            links.new(output_node.inputs["Surface"], image_node.outputs["Color"])
            
        plane_ob.active_material = bpy.data.materials["GD_Reference"]

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    space.shading.color_type = 'TEXTURE'
    else:
        # Refresh original material
        if 'saved_mat' in locals():
            plane_ob.active_material = saved_mat

        for mat in bpy.data.materials:
            if mat.name == "GD_Reference":
                bpy.data.materials.remove(mat)
                break

    plane_ob.show_wire = True

    if grabDoc.gridSubdivisions and grabDoc.useGrid:
        # Create & load new bmesh
        bm = bmesh.new()
        bm.from_mesh(plane_ob.data)

        # Subdivide
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=grabDoc.gridSubdivisions, use_grid_fill=True)

        # Write back to the mesh
        bm.to_mesh(plane_ob.data)

    # CAMERA

    # If actively viewing a camera, set a variable to remind the script later on
    if [area.spaces.active.region_3d.view_perspective for area in context.screen.areas if area.type == 'VIEW_3D'] == ['CAMERA']:
        repositionCam = True
        bpy.ops.view3d.view_camera()

    # Remove pre existing camera & related data blocks
    if "GD_Trim Camera" in bpy.data.cameras:
        bpy.data.cameras.remove(bpy.data.cameras["GD_Trim Camera"])

    # Add Trim Camera & change settings
    trim_cam = bpy.data.cameras.new("GD_Trim Camera")
    trim_cam_ob = bpy.data.objects.new("GD_Trim Camera", trim_cam)

    trim_cam_ob.location = (0, 0, 10 * grabDoc.scalingSet)
    trim_cam_ob.data.type = 'ORTHO'
    trim_cam_ob.data.display_size = .01
    trim_cam_ob.data.passepartout_alpha = 1
    trim_cam_ob.hide_viewport = trim_cam_ob.hide_select = True
    trim_cam_ob.parent = plane_ob

    grabDocColl.objects.link(trim_cam_ob)
        
    # Change the camera scaling based on user preference
    trim_cam_ob.data.ortho_scale = grabDoc.scalingSet

    if 'repositionCam' in locals():
        bpy.ops.view3d.view_camera() # Needed to do twice or else Blender decides where the users personal camera is located when they exit

    # HEIGHT GUIDE

    # Remove pre existing Height Guide & all related data blocks 
    if "GD_Height Guide" in bpy.data.objects:
        bpy.data.meshes.remove(bpy.data.objects["GD_Height Guide"].data)
    
    # Create object & link new object to the active collection
    if grabDoc.exportHeight and grabDoc.rangeTypeHeight == 'MANUAL':
        pc_height_guide = manual_height_guide_pc("GD_Height Guide")
        context.collection.objects.link(pc_height_guide)

        # Parent the height guide to the BG Plane
        pc_height_guide.parent = plane_ob
        pc_height_guide.hide_select = True

    # ORIENT GUIDE

    # Remove pre existing orient guide & all related data blocks
    if "GD_Orient Guide" in bpy.data.objects:
        bpy.data.meshes.remove(bpy.data.objects["GD_Orient Guide"].data)

    plane_y = plane_ob.dimensions.y / 2

    pc_orient = uv_orient_pc("GD_Orient Guide", [(-.3, plane_y + .1, 0), (.3, plane_y + .1, 0), (0, plane_y + .35, 0)])
    context.collection.objects.link(pc_orient)

    # Parent the height guide to the BG Plane
    pc_orient.parent = plane_ob
    pc_orient.hide_select = True

    # CLEANUP

    # Select original object(s)
    for o in selectedCallback:
        ob = context.scene.objects.get(o)
        ob.select_set(True)

    # Select original active collection, active object & the context mode
    if 'savedActiveColl' in locals():
        context.view_layer.active_layer_collection = savedActiveColl

    context.view_layer.objects.active = bpy.data.objects[activeCallback] if activeCallback else None

    if 'modeCallback' in locals() and activeCallback:
        bpy.ops.object.mode_set(mode = modeCallback)

    # Hide collections & make unselectable if requested (runs after everything else)
    grabDocColl.hide_select = not grabDoc.collSelectable
    grabDocColl.hide_viewport = not grabDoc.collVisible


def manual_height_guide_pc(ob_name, edges = [(0,4), (1,5), (2,6), (3,7), (4,5), (5,6), (6,7), (7,4)], faces = []):
    grabDoc = bpy.context.scene.grabDoc

    # Make a tuple for the planes vertex positions
    cameraVectorsList = bpy.data.objects["GD_Trim Camera"].data.view_frame(scene = bpy.context.scene)

    def change_stem_z(tuple):
        newVectorTuple = (tuple[0], tuple[1], grabDoc.guideHeight)
        return newVectorTuple

    stemsVectorsList = tuple([change_stem_z(vec) for vec in cameraVectorsList])

    def change_ring_z(tuple):
        newVectorTuple = (tuple[0], tuple[1], tuple[2] + 1)
        return newVectorTuple

    ringVectorsList = tuple([change_ring_z(vec) for vec in cameraVectorsList])

    # Combine both tuples
    ringVectorsList += stemsVectorsList

    # Create new mesh & object data blocks
    meNew = bpy.data.meshes.new(ob_name)
    obNew = bpy.data.objects.new(ob_name, meNew)

    # Make a mesh from a list of vertices / edges / faces
    meNew.from_pydata(ringVectorsList, edges, faces)

    # Display name & update the mesh
    meNew.update()
    return obNew


def uv_orient_pc(ob_name, vertices, edges = [(0,2), (0,1), (1,2)], faces = []):
    # Create new mesh & object data blocks
    meNew = bpy.data.meshes.new(ob_name)
    obNew = bpy.data.objects.new(ob_name, meNew)

    # Make a mesh from a list of vertices / edges / faces
    meNew.from_pydata(vertices, edges, faces)

    # Display name & update the mesh
    meNew.update()
    return obNew


def ng_setup(self, context):
    grabDoc = context.scene.grabDoc

    # NORMALS

    if not 'GD_Normals' in bpy.data.node_groups:
        # Create node group
        ng_normal = bpy.data.node_groups.new('GD_Normals', 'ShaderNodeTree')
        ng_normal.use_fake_user = True

        # Create group outputs
        group_outputs = ng_normal.nodes.new('NodeGroupOutput')
        ng_normal.outputs.new('NodeSocketShader','Output')
        ng_normal.inputs.new('NodeSocketShader','Saved Input')

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
        ng_ao.inputs.new('NodeSocketShader','Saved Input')

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
        ng_height.inputs.new('NodeSocketShader','Saved Input')

        # Create group nodes
        camera_data_node = ng_height.nodes.new('ShaderNodeCameraData')
        camera_data_node.location = (-800,0)

        map_range_node = ng_height.nodes.new('ShaderNodeMapRange')
        map_range_node.inputs[1].default_value = -grabDoc.guideHeight + 5
        map_range_node.inputs[2].default_value = 5
        map_range_node.location = (-600,0)

        invert_node = ng_height.nodes.new('ShaderNodeInvert')
        invert_node.location = (-400,0)
        
        emission_node = ng_height.nodes.new('ShaderNodeEmission')
        emission_node.location = (-200,0)

        # Link materials
        link = ng_height.links

        link.new(map_range_node.inputs["Value"], camera_data_node.outputs["View Z Depth"])
        link.new(invert_node.inputs["Color"], map_range_node.outputs["Result"])
        link.new(emission_node.inputs["Color"], invert_node.outputs["Color"])
        link.new(group_outputs.inputs["Output"], emission_node.outputs["Emission"])


################################################################################################################
# BAKER SETUP
################################################################################################################


def get_rendered_objects(self, context):
    self.render_list = ['GD_Background Plane']

    if context.scene.grabDoc.onlyRenderColl:  
        for coll in bpy.data.collections:
            if coll.name == "GrabDoc Objects (put objects here)" or coll.name == "GrabDoc (do not touch contents)":
                for ob in coll.all_objects:
                    if not ob.hide_render and ob.type == 'MESH' and len(ob.data.polygons) and not ob.name.startswith('GD_'):
                        self.render_list.append(ob.name)
    else:
        for ob in context.view_layer.objects:
            if not ob.hide_render and ob.type == 'MESH' and len(ob.data.polygons) and not ob.name.startswith('GD_'):
                local_bbox_center = .125 * sum((Vector(b) for b in ob.bound_box), Vector())
                global_bbox_center = ob.matrix_world @ local_bbox_center

                if(is_in_bounding_vectors(global_bbox_center)):
                    self.render_list.append(ob.name)


def find_tallest_object(self, context):
    tallest_vert = 0

    for ob in context.view_layer.objects:
        if ob.name in self.render_list:
            if not ob.name.startswith('GD_'):
                # Get global coordinates of vertices
                global_vert_coords = [ob.matrix_world @ v.co for v in ob.data.vertices]

                # Find the highest Z value amongst the object's verts
                max_z_co = max([co.z for co in global_vert_coords])
                
                if max_z_co > tallest_vert:
                    tallest_vert = max_z_co

    if tallest_vert:
        context.scene.grabDoc.guideHeight = tallest_vert


def is_in_bounding_vectors(vec_check):
    planeName = bpy.data.objects["GD_Background Plane"]

    vec1 = Vector((planeName.dimensions.x * -1.25 + planeName.location[0], planeName.dimensions.y * -1.25 + planeName.location[1], -100))
    vec2 = Vector((planeName.dimensions.x * 1.25 + planeName.location[0], planeName.dimensions.y * 1.25 + planeName.location[1], 100))

    for i in range(0, 3):
        if (vec_check[i] < vec1[i] and vec_check[i] < vec2[i] or vec_check[i] > vec1[i] and vec_check[i] > vec2[i]):
            return False
    return True


def proper_scene_setup(is_setup=False):
    if "GrabDoc (do not touch contents)" in bpy.data.collections:
        if "GD_Background Plane" in bpy.data.objects:
            if "GD_Trim Camera" in bpy.data.objects:
                is_setup = True
    return is_setup


def bad_setup_check(self, context, active_export, report_value=False, report_string=""):
    grabDoc = context.scene.grabDoc

    # Run this before other error checks as the following error checker contains dependencies
    get_rendered_objects(self, context)

    # Look for Trim Camera (only thing required to render)
    if not "GD_Trim Camera" in context.view_layer.objects and not report_value:
        report_value = True
        report_string = "Trim Camera not found, refresh the scene to set everything up properly."

    # Check for no objects in manual collection
    if grabDoc.onlyRenderColl and not report_value:
        if not len(bpy.data.collections["GrabDoc Objects (put objects here)"].objects):
            report_value = True
            report_string = "You have 'Pick Baked Objects via Collection' turned on, but no objects are inside the collection."
        
    # Check for rendered objects that contain the Displace modifier
    if grabDoc.exportHeight and not report_value:
        for ob in context.view_layer.objects:
            if ob.name in self.render_list and grabDoc.exportHeight and grabDoc.rangeTypeHeight == 'AUTO':
                for mod in ob.modifiers:
                    if mod.type == "DISPLACE":
                        report_value = True
                        report_string = "When using Displace modifiers & baking Height you must use the 'Manual' 0-1 Range option.\n\n 'Auto' 0-1 Range cannot account for modifier geometry, this goes for all modifiers but is only required for displacement."
                        
    if active_export:
        # Check for export path
        if not os.path.exists(grabDoc.exportPath) and not report_value:
            report_value = True
            report_string = "There is no export path set"

        # Check if all bake maps are disabled
        if not grabDoc.uiVisibilityNormals or not grabDoc.exportNormals:
            if not grabDoc.uiVisibilityCurvature or not grabDoc.exportCurvature:
                if not grabDoc.uiVisibilityOcclusion or not grabDoc.exportOcclusion:
                    if not grabDoc.uiVisibilityHeight or not grabDoc.exportHeight:
                        if not grabDoc.uiVisibilityMatID or not grabDoc.exportMatID:
                            report_value = True
                            report_string = "No bake maps are turned on."

    return (report_value, report_string)


def export_bg_plane(self, context):
    # Save original selection
    savedSelection = context.selected_objects

    # Deselect all objects
    bpy.ops.object.select_all(action='DESELECT')

    # Select bg plane, export and deselect bg plane
    bpy.data.objects["GD_Background Plane"].select_set(True)
    bpy.ops.export_scene.fbx(filepath=f'{context.scene.grabDoc.exportPath}{context.scene.grabDoc.exportName}.fbx', use_selection=True)
    bpy.data.objects["GD_Background Plane"].select_set(False)

    # Refresh original selection
    for ob in savedSelection:
        ob.select_set(True)


def export_and_preview_setup(self, context):
    grabDoc = context.scene.grabDoc
    render = context.scene.render

    # TO DO - Preserve use_local_camera & original camera

    # Set - Active Camera
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                space.use_local_camera = False
                break

    context.scene.camera = bpy.data.objects["GD_Trim Camera"]

        ## VIEW LAYER PROPERTIES ##

    # Save & Set - View layer
    self.savedViewLayerUse = context.view_layer.use
    self.savedUseSingleLayer = render.use_single_layer

    context.view_layer.use = True
    render.use_single_layer = True

        ## RENDER PROPERTIES ##

    eevee = context.scene.eevee

    # Save - Render Engine (Set per bake map)
    self.savedRenderer = render.engine

    # Save - Sampling (Set per bake map)
    self.savedWorkbenchSampling = context.scene.display.render_aa
    self.savedEeveeSampling = eevee.taa_render_samples

    # Save & Set - Bloom
    self.savedUseBloom = eevee.use_bloom

    eevee.use_bloom = False

    # Save & Set - Ambient Occlusion
    self.savedUseAO = eevee.use_gtao
    self.savedAODistance = eevee.gtao_distance # Set per bake map
    self.savedAOQuality = eevee.gtao_quality

    eevee.use_gtao = False # Disable unless needed

    context.scene.use_nodes = False # Disable scene nodes unless needed (Prevents black render...?)

    # Save & Set - Color Management
    view_settings = context.scene.view_settings

    self.savedDisplayDevice = context.scene.display_settings.display_device
    self.savedViewTransform = view_settings.view_transform
    self.savedContrastType = view_settings.look
    self.savedExposure = view_settings.exposure
    self.savedGamma = view_settings.gamma 

    view_settings.view_transform = 'Standard'
    view_settings.look = 'None'
    view_settings.exposure = 0
    view_settings.gamma = 1

    # Save & Set - Performance 
    if bpy.app.version >= (2, 83, 0):
        self.savedHQNormals = render.use_high_quality_normals
        render.use_high_quality_normals = True

        ## OUTPUT PROPERTIES ##

    image_settings = render.image_settings

    # Save & Set - Dimensions
    self.savedResX = render.resolution_x
    self.savedResY = render.resolution_y

    render.resolution_x = grabDoc.exportResX
    render.resolution_y = grabDoc.exportResY
    render.resolution_percentage = 100 # Don't bother saving

    # Save & Set - Output
    self.savedColorMode = image_settings.color_mode
    self.savedFileFormat = image_settings.file_format

    image_settings.file_format = grabDoc.imageType

    if grabDoc.imageType == 'PNG':
        self.savedCompression = image_settings.compression
        image_settings.compression = grabDoc.imageComp

    if grabDoc.imageType == 'TIFF':
        self.savedCompression = image_settings.tiff_codec
        image_settings.tiff_codec = grabDoc.imageCompTIFF

    if grabDoc.imageType != 'TARGA':
        self.savedColorDepth = image_settings.color_depth
        image_settings.color_depth = grabDoc.colorDepth

    # Save & Set - Post Processing
    self.savedUseSequencer = render.use_sequencer
    self.savedUseCompositer = render.use_compositing
    self.savedDitherIntensity = render.dither_intensity

    render.use_sequencer = False
    render.use_compositing = False
    render.dither_intensity = 0

        ## VIEWPORT SHADING ##

    scene_shading = bpy.data.scenes[str(context.scene.name)].display.shading

    # Save & Set
    self.savedLight = scene_shading.light
    self.savedColorType = scene_shading.color_type
    self.savedBackface = scene_shading.show_backface_culling
    self.savedXray = scene_shading.show_xray
    self.savedShadows = scene_shading.show_shadows
    self.savedCavity = scene_shading.show_cavity
    self.savedDOF = scene_shading.use_dof
    self.savedOutline = scene_shading.show_object_outline
    self.savedShowSpec = scene_shading.show_specular_highlight

    scene_shading.show_backface_culling = False
    scene_shading.show_xray = False
    scene_shading.show_shadows = False
    scene_shading.show_cavity = False
    scene_shading.use_dof = False
    scene_shading.show_object_outline = False
    scene_shading.show_specular_highlight = False

        ## PLANE REFERENCE ##

    if grabDoc.refSelection:
        self.savedRefSelection = grabDoc.refSelection.name
    else:
        self.savedRefSelection = None
    
        ## OBJECT VISIBILITY ##

    bg_plane = bpy.data.objects["GD_Background Plane"]
   
    bg_plane.hide_viewport = False
    bg_plane.hide_set(False)
    bg_plane.hide_render = False

    self.ob_hidden_render_list = []
    self.ob_hidden_vp_list = []
    
    # Save & Set - Non-rendered objects visibility (self.render_list defined in bad_setup_check)
    for ob in context.view_layer.objects:
        if ob.type == 'MESH':
            if not ob.name in self.render_list:
                # Hide in render
                if not ob.hide_render:
                    self.ob_hidden_render_list.append(ob.name)
                ob.hide_render = True

                # Hide in viewport
                if not ob.hide_viewport:
                    self.ob_hidden_vp_list.append(ob.name)
                ob.hide_viewport = True


def export_refresh(self, context):
    grabDoc = context.scene.grabDoc
    render = context.scene.render

        ## VIEW LAYER PROPERTIES ##

    # Refresh - View layer
    context.view_layer.use = self.savedViewLayerUse
    context.scene.render.use_single_layer = self.savedUseSingleLayer

        ## RENDER PROPERTIES ##

    # Refresh - Render Engine
    render.engine = self.savedRenderer

    # Refresh - Sampling
    context.scene.display.render_aa = self.savedWorkbenchSampling
    context.scene.eevee.taa_render_samples = self.savedEeveeSampling

    # Refresh - Bloom
    context.scene.eevee.use_bloom = self.savedUseBloom

    # Refresh - Color Management
    view_settings = context.scene.view_settings

    view_settings.look = self.savedContrastType
    context.scene.display_settings.display_device = self.savedDisplayDevice
    view_settings.view_transform = self.savedViewTransform
    view_settings.exposure = self.savedExposure
    view_settings.gamma = self.savedGamma

    # Refresh - Performance
    if bpy.app.version >= (2, 83, 0):
        render.use_high_quality_normals = self.savedHQNormals

        ## OUTPUT PROPERTIES ##

    # Refresh - Output
    render.image_settings.color_mode = self.savedColorMode
    render.image_settings.file_format = self.savedFileFormat

    if grabDoc.imageType == 'TIFF':
        render.image_settings.tiff_codec = self.savedCompression
    if grabDoc.imageType == 'PNG':
        render.image_settings.compression = self.savedCompression

    if grabDoc.imageType != 'TARGA':
        render.image_settings.color_depth = self.savedColorDepth

    # Refresh - Post Processing
    render.use_sequencer = self.savedUseSequencer
    render.use_compositing = self.savedUseCompositer

    render.dither_intensity = self.savedDitherIntensity

    # Refresh - Dimensions
    render.resolution_x = self.savedResX
    render.resolution_y = self.savedResY

        ## VIEWPORT SHADING ##

    scene_shading = bpy.data.scenes[str(context.scene.name)].display.shading

    # Refresh
    scene_shading.show_cavity = self.savedCavity
    scene_shading.color_type = self.savedColorType
    scene_shading.show_backface_culling = self.savedBackface
    scene_shading.show_xray = self.savedXray
    scene_shading.show_shadows = self.savedShadows
    scene_shading.use_dof = self.savedDOF
    scene_shading.show_object_outline = self.savedOutline
    scene_shading.show_specular_highlight = self.savedShowSpec
    scene_shading.light = self.savedLight

        ## PLANE REFERENCE ##

    if self.savedRefSelection:
        grabDoc.refSelection = bpy.data.images[self.savedRefSelection]

        ## OBJECT VISIBILITY ##

    # Refresh - Non-rendered objects visibility
    for ob in context.view_layer.objects:
        # Unhide in render
        if ob.name in self.ob_hidden_render_list:
            ob.hide_render = False
        
        # Unhide in viewport
        if ob.name in self.ob_hidden_vp_list:
            ob.hide_viewport = False


################################################################################################################
# ID SETUP & CLEANUP
################################################################################################################


class GRABDOC_OT_quick_id_setup(Operator):
    bl_idname = "grab_doc.quick_id_setup"
    bl_label = "Auto ID Full Scene"
    bl_description = "Quickly sets up materials on all objects within the cameras view spectrum"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.active_object:
            bpy.ops.object.mode_set(mode='OBJECT')

        for mat in bpy.data.materials:
            if mat.name.startswith("GD_RANDOM"):
                bpy.data.materials.remove(mat)

        get_rendered_objects(self, context)

        for ob in context.view_layer.objects:
            add_mat = True
            if ob.name in self.render_list and not ob.name.startswith('GD_'):
                for slot in ob.material_slots:
                    if slot.name.startswith('GD_ID'):
                        add_mat = False
                        break

                if add_mat:
                    mat = bpy.data.materials.new(f"GD_RANDOM_ID.{randint(0, 100000000)}")
                    mat.use_nodes = True

                    # Set - viewport color
                    mat.diffuse_color = random(), random(), random(), 1

                    bsdf_node = mat.node_tree.nodes.get('Principled BSDF')
                    bsdf_node.inputs[0].default_value = mat.diffuse_color
                        
                    ob.active_material_index = 0
                    ob.active_material = mat

        for mat in bpy.data.materials:
            if mat.name.startswith('GD_ID') or mat.name.startswith('GD_RANDOM'):
                if not mat.users:
                    bpy.data.materials.remove(mat)
        return{'FINISHED'}


class GRABDOC_OT_quick_id_selected(Operator):
    bl_idname = "grab_doc.quick_id_selected"
    bl_label = "Add ID to Selected"
    bl_description = "Adds a new single material with a random color to the selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects

    def execute(self, context):
        if context.active_object:
            bpy.ops.object.mode_set(mode='OBJECT')

        mat = bpy.data.materials.new(f"GD_ID.{randint(0, 100000000)}")
        mat.diffuse_color = random(), random(), random(), 1
        mat.use_nodes = True

        bsdf_node = mat.node_tree.nodes.get('Principled BSDF')
        bsdf_node.inputs[0].default_value = mat.diffuse_color

        for ob in context.selected_objects:
            if ob.type == 'MESH':                       
                ob.active_material_index = 0
                ob.active_material = mat

        for mat in bpy.data.materials:
            if mat.name.startswith('GD_ID') or mat.name.startswith('GD_RANDOM'):
                if not mat.users:
                    bpy.data.materials.remove(mat)
        return{'FINISHED'}


class GRABDOC_OT_quick_remove_random_mats(Operator):
    bl_idname = "grab_doc.quick_remove_random_mats"
    bl_label = "All"
    bl_description = "Removes all GrabDoc Mat ID materials from all related objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.active_object:
            bpy.ops.object.mode_set(mode = 'OBJECT')

        for mat in bpy.data.materials:
            if mat.name.startswith("GD_RANDOM"):
                bpy.data.materials.remove(mat)
        return{'FINISHED'}


class GRABDOC_OT_quick_remove_manual_mats(Operator):
    bl_idname = "grab_doc.quick_remove_manual_mats"
    bl_label = "All"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.active_object:
            bpy.ops.object.mode_set(mode = 'OBJECT')

        for mat in bpy.data.materials:
            if mat.name.startswith("GD_ID"):
                bpy.data.materials.remove(mat)
        return{'FINISHED'}


class GRABDOC_OT_quick_remove_selected_mats(Operator):
    bl_idname = "grab_doc.quick_remove_selected_mats"
    bl_label = "Selected"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects

    def execute(self, context):
        if context.active_object:
            bpy.ops.object.mode_set(mode='OBJECT')

        get_rendered_objects(self, context)

        for ob in context.selected_objects:
            if ob.type == 'MESH':
                for slot in ob.material_slots:
                    if slot.name.startswith('GD_ID'):
                        bpy.data.materials.remove(bpy.data.materials[slot.name])
                        break
        return{'FINISHED'}


################################################################################################################
# MATERIAL SETUP & CLEANUP
################################################################################################################


## REMOVE NODE GROUP & RETURN ORIGINAL LINKS IF THEY EXIST ##
def cleanup_ng_from_mat(self, context):
    if self.setup_type != 'None':
        for mat in bpy.data.materials:
            if not mat.use_nodes:
                mat.use_nodes = True
            
            # If there is a GrabDoc created material, remove it
            if mat.name == 'GD_Material (do not touch contents)':
                bpy.data.materials.remove(mat)

            # If a material has a GrabDoc created Node Group, remove it
            elif self.setup_type in mat.node_tree.nodes:
                for mat_node in mat.node_tree.nodes:
                    if mat_node.type == 'OUTPUT_MATERIAL' and mat_node.is_active_output:
                        output_node = mat.node_tree.nodes.get(mat_node.name)
                        break

                GD_node_group = mat.node_tree.nodes.get(self.setup_type)

                for input in GD_node_group.inputs:
                    for link in input.links:
                        original_node_connection = mat.node_tree.nodes.get(link.from_node.name)
                        original_node_socket = link.from_socket.name
                        
                mat.node_tree.links.new(output_node.inputs["Surface"], original_node_connection.outputs[original_node_socket])
                
                mat.node_tree.nodes.remove(GD_node_group)


## CREATE & APPLY A MATERIAL TO OBJECTS WITHOUT ACTIVE MATERIALS ##
def create_apply_ng_mat(self, context):
    # Reuse GrabDoc created material if it already exists
    if 'GD_Material (do not touch contents)' in bpy.data.materials:
        self.mat = bpy.data.materials["GD_Material (do not touch contents)"]
        mat = self.mat
    else:
        # Create a material
        self.mat = bpy.data.materials.new(name = "GD_Material (do not touch contents)")
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


def add_ng_to_mat(self, context):
    if self.setup_type != 'None':
        ## ADD NODE GROUP TO ALL MATERIALS, SAVE ORIGINAL LINKS & LINK NODE GROUP TO MATERIAL OUTPUT ##
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
                        original_node_connection = None

                        if not mat_slot.use_nodes:
                            mat_slot.use_nodes = True

                        if not self.setup_type in mat_slot.node_tree.nodes:
                            # Get materials Output Material node
                            for mat_node in mat_slot.node_tree.nodes:
                                if mat_node.type == 'OUTPUT_MATERIAL' and mat_node.is_active_output:
                                    output_node = mat_slot.node_tree.nodes.get(mat_node.name)
                                    break

                            if not output_node:
                                output_node = mat_slot.node_tree.nodes.new('ShaderNodeOutputMaterial')

                            # Add node group to material
                            GD_node_group = mat_slot.node_tree.nodes.new('ShaderNodeGroup')
                            GD_node_group.node_tree = bpy.data.node_groups[self.setup_type]
                            GD_node_group.location = (output_node.location[0], output_node.location[1] - 140)
                            GD_node_group.name = bpy.data.node_groups[self.setup_type].name
                            GD_node_group.hide = True

                            original_node_found = False

                            # Get the original node link (if it exists)
                            for node_input in output_node.inputs:
                                for link in node_input.links:
                                    original_node_connection = mat_slot.node_tree.nodes.get(link.from_node.name)

                                    # Link original connection to the Node Group
                                    mat_slot.node_tree.links.new(GD_node_group.inputs["Saved Input"], original_node_connection.outputs[link.from_socket.name])

                                    original_node_found = True

                                if original_node_found:
                                    break

                            # Link Node Group to the output
                            mat_slot.node_tree.links.new(output_node.inputs["Surface"], GD_node_group.outputs["Output"])


## NORMALS ##


def normals_setup(self, context):
    grabDoc = context.scene.grabDoc
    render = context.scene.render

    render.engine = 'BLENDER_EEVEE'
    context.scene.eevee.taa_render_samples = grabDoc.samplesNormals
    render.image_settings.color_mode = 'RGBA'
    context.scene.display_settings.display_device = 'None'

    self.setup_type = 'GD_Normals'
    add_ng_to_mat(self, context)

def normals_export(self, context):
    if self.offlineRenderType == "normals":
        offline_render(self, context)
    else:
        grabdoc_export(self, context, exportSuffix="_normals")

        # Reimport the Normal map as a material (if the option is turned on)
        if context.scene.grabDoc.reimportAsMatNormals:
            normals_reimport_as_mat(self, context)

def normals_reimport_as_mat(self, context):
    grabDoc = context.scene.grabDoc

    # Remove pre-existing material
    for mat in bpy.data.materials:
        if mat.name == f'{grabDoc.exportName}_normals':
            bpy.data.materials.remove(mat)
            break

    # Remove original image
    for image in bpy.data.images:
        if image.name == f'{grabDoc.exportName}_normals':
            bpy.data.images.remove(image)
            break

    # Create material
    mat = bpy.data.materials.new(name=f'{grabDoc.exportName}_normals')
    mat.use_nodes = True

    output_node = mat.node_tree.nodes["Material Output"]
    output_node.location = (0,0)

    bsdf_node = mat.node_tree.nodes["Principled BSDF"]
    bsdf_node.inputs[5].default_value = 0
    bsdf_node.location = (-300,0)

    normal_map_node = mat.node_tree.nodes.new('ShaderNodeNormalMap')
    normal_map_node.location = (-500,0)

    if grabDoc.imageType == 'TIFF':
        file_extension = '.tif'
    elif grabDoc.imageType == 'TARGA':
        file_extension = '.tga'
    else:
        file_extension = '.png'

    image_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    image_node.image = bpy.data.images.load(f'{grabDoc.exportPath}{grabDoc.exportName}_normals{file_extension}')
    image_node.image.colorspace_settings.name = 'Linear'
    image_node.location = (-800,0)

    # Rename the newly imported image
    bpy.data.images[f'{grabDoc.exportName}_normals{file_extension}'].name = f'{grabDoc.exportName}_normals'

    # Make links
    link = mat.node_tree.links

    link.new(normal_map_node.inputs['Color'], image_node.outputs['Color'])
    link.new(bsdf_node.inputs['Normal'], normal_map_node.outputs['Normal'])


## CURVATURE ##


def curvature_setup(self, context):
    scene = context.scene
    grabDoc = scene.grabDoc
    scene_shading = bpy.data.scenes[str(scene.name)].display.shading
    
    # Set - Render engine settings
    scene.view_settings.look = grabDoc.contrastCurvature.replace('_', ' ')

    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.render_aa = grabDoc.samplesCurvature
    scene_shading.light = 'FLAT'
    scene_shading.color_type =  'SINGLE'
    scene.display_settings.display_device = 'sRGB'

    scene.render.image_settings.color_mode = 'BW'

    # Save & Set - Cavity
    self.savedCavityType = scene_shading.cavity_type
    self.savedCavityRidgeFactor = scene_shading.cavity_ridge_factor
    self.savedCurveRidgeFactor = scene_shading.curvature_ridge_factor
    self.savedCavityValleyFactor = scene_shading.cavity_valley_factor
    self.savedCurveValleyFactor = scene_shading.curvature_valley_factor
    self.savedRidgeDistance = scene.display.matcap_ssao_distance

    self.savedSingleList = [] # List for single_color because saving the variable on its own isn't enough (for some reason)

    for i in scene_shading.single_color:
        self.savedSingleList.append(i)
    
    scene_shading.show_cavity = True
    scene_shading.cavity_type = 'BOTH'
    scene_shading.cavity_ridge_factor = scene_shading.curvature_ridge_factor = grabDoc.ridgeCurvature
    scene_shading.curvature_valley_factor = grabDoc.valleyCurvature
    scene_shading.cavity_valley_factor = 0
    scene_shading.single_color = (0.214041, 0.214041, 0.214041)

    scene.display.matcap_ssao_distance = 0.075

    self.setup_type = 'None'
    
def curvature_export(self, context):
    if self.offlineRenderType == "curvature":
        offline_render(self, context)
    else:
        grabdoc_export(self, context, exportSuffix="_curvature")

def curvature_refresh(self, context):
    scene_shading = bpy.data.scenes[str(context.scene.name)].display.shading

    scene_shading.cavity_ridge_factor = self.savedCavityRidgeFactor
    scene_shading.curvature_ridge_factor = self.savedCurveRidgeFactor
    scene_shading.cavity_valley_factor = self.savedCavityValleyFactor
    scene_shading.curvature_valley_factor = self.savedCurveValleyFactor
    scene_shading.single_color =  self.savedSingleList
    scene_shading.cavity_type = self.savedCavityType
    scene_shading.show_cavity = self.savedCavity

    context.scene.display.matcap_ssao_distance = self.savedRidgeDistance
    
    bpy.data.objects["GD_Background Plane"].color[3] = 1


## AMBIENT OCCLUSION ##


def occlusion_setup(self, context):
    grabDoc = context.scene.grabDoc
    render = context.scene.render
    eevee = context.scene.eevee
    
    render.engine = 'BLENDER_EEVEE'
    eevee.taa_render_samples = grabDoc.samplesOcclusion
    render.image_settings.color_mode = 'BW'
    context.scene.display_settings.display_device = 'None'

    # Save & Set - Overscan (Can help with screenspace effects)
    self.savedUseOverscan = eevee.use_overscan
    self.savedOverscanSize = eevee.overscan_size

    eevee.use_overscan = True
    eevee.overscan_size = 10

    # Set - Ambient Occlusion
    eevee.use_gtao = True
    eevee.gtao_distance = grabDoc.distanceOcclusion
    eevee.gtao_quality = .5

    context.scene.view_settings.look = grabDoc.contrastOcclusion.replace('_', ' ')

    self.setup_type = 'GD_Ambient Occlusion'
    add_ng_to_mat(self, context)

def occlusion_export(self, context):
    if self.offlineRenderType == "occlusion":
        offline_render(self, context)
    else:
        grabdoc_export(self, context, exportSuffix="_ao")

        # Reimport the Normal map as a material if requested
        if context.scene.grabDoc.reimportAsMatOcclusion:
            occlusion_reimport_as_mat(self, context)

def occlusion_refresh(self, context):
    eevee = context.scene.eevee

    eevee.use_overscan = self.savedUseOverscan
    eevee.overscan_size = self.savedOverscanSize

    eevee.use_gtao = self.savedUseAO
    eevee.gtao_distance = self.savedAODistance
    eevee.gtao_quality = self.savedAOQuality

def occlusion_reimport_as_mat(self, context):
    grabDoc = context.scene.grabDoc

    # Remove pre-existing material
    for mat in bpy.data.materials:
        if mat.name == f'{grabDoc.exportName}_AO':
            bpy.data.materials.remove(mat)
            break

    # Remove original image
    for image in bpy.data.images:
        if image.name == f'{grabDoc.exportName}_AO':
            bpy.data.images.remove(image)
            break

    # Create material
    mat = bpy.data.materials.new(name=f'{grabDoc.exportName}_AO')
    mat.use_nodes = True

    output_node = mat.node_tree.nodes["Material Output"]
    output_node.location = (0,0)

    mat.node_tree.nodes.remove(mat.node_tree.nodes.get('Principled BSDF'))

    if grabDoc.imageType == 'TIFF':
        file_extension = '.tif'
    elif grabDoc.imageType == 'TARGA':
        file_extension = '.tga'
    else:
        file_extension = '.png'

    image_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    image_node.image = bpy.data.images.load(f'{grabDoc.exportPath}{grabDoc.exportName}_AO{file_extension}')
    image_node.location = (-300,0)

    # Rename the newly imported image
    bpy.data.images[f'{grabDoc.exportName}_AO{file_extension}'].name = f'{grabDoc.exportName}_AO'

    # Make links
    link = mat.node_tree.links

    link.new(output_node.inputs['Surface'], image_node.outputs['Color'])


## HEIGHT ##


def height_setup(self, context):
    grabDoc = context.scene.grabDoc
    render = context.scene.render

    render.engine = 'BLENDER_EEVEE'
    context.scene.eevee.taa_render_samples = grabDoc.samplesHeight
    render.image_settings.color_mode = 'BW'
    context.scene.display_settings.display_device = 'None'

    self.setup_type = 'GD_Height'
    add_ng_to_mat(self, context)

    if grabDoc.rangeTypeHeight == 'AUTO':
        find_tallest_object(self, context)

def height_export(self, context):
    if self.offlineRenderType == "height":
        offline_render(self, context)
    else:
        grabdoc_export(self, context, exportSuffix="_height")
        

## MATERIAL ID ##


def id_setup(self, context):
    render = context.scene.render
    scene_shading = bpy.data.scenes[str(context.scene.name)].display.shading

    render.engine = 'BLENDER_WORKBENCH'
    context.scene.display.render_aa = context.scene.grabDoc.samplesMatID
    scene_shading.light = 'FLAT'
    render.image_settings.color_mode = 'RGBA'
    context.scene.display_settings.display_device = 'sRGB'

    # Choose the method of ID creation based on user preference
    scene_shading.color_type = context.scene.grabDoc.methodMatID

    self.setup_type = 'None'

def id_export(self, context):
    if self.offlineRenderType == "ID":
        offline_render(self, context)
    else:
        grabdoc_export(self, context, exportSuffix="_matID")


################################################################################################################
# BAKER
################################################################################################################


def grabdoc_export(self, context, exportSuffix):
    grabDoc = context.scene.grabDoc
    render = context.scene.render
    
    # Save - file output path
    savedPath = render.filepath

    # Set - Output path to add-on path + add-on name + the type of map exported (file extensions handled automatically)
    render.filepath = grabDoc.exportPath + grabDoc.exportName + exportSuffix

    context.scene.camera = bpy.data.objects["GD_Trim Camera"]

    bpy.ops.render.render(write_still = True)

    # Refresh - file output path
    render.filepath = savedPath


def offline_render(self, context):
    render = context.scene.render

    # Get add-on paths
    addon_path = os.path.dirname(__file__)
    temp_folder_path = os.path.join(addon_path, "Temp")

    # Create the directory 
    if not os.path.exists(temp_folder_path):
        os.mkdir(temp_folder_path)

    image_name = 'GD_Render Result'

    # Save & Set - file output path
    savedPath = render.filepath

    render.filepath = f'{temp_folder_path}\\{image_name}'

    # Delete original image
    if image_name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[image_name])

    # Render
    bpy.ops.render.render(write_still = True)

    # Load in the newly rendered image
    new_image = bpy.data.images.load(f'{temp_folder_path}\\{image_name}.png')
    new_image.name = image_name

    # Refresh - file output path
    render.filepath = savedPath

    # Call user prefs window
    bpy.ops.screen.userpref_show("INVOKE_DEFAULT")

    # Change area & image type
    area = context.window_manager.windows[-1].screen.areas[0]
    area.type = "IMAGE_EDITOR"
    area.spaces.active.image = bpy.data.images[image_name]


class GRABDOC_OT_export_maps(OpInfo, Operator):
    bl_idname = "grab_doc.export_maps"
    bl_label = ""
    bl_description = " "
    bl_options={'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return(not context.scene.grabDoc.modalState)

    offlineRenderType: EnumProperty(items=(('online', "Online", ""),
                                           ('normals', "Normals", ""),
                                           ('curvature', "Curvature", ""),
                                           ('occlusion', "Ambient Occlusion", ""),
                                           ('height', "Height", ""),
                                           ('ID', "Material ID", "")),
                                           options={'HIDDEN'})

    def execute(self, context):
        # Declare propertygroup as var
        grabDoc = context.scene.grabDoc

        report_value, report_string = bad_setup_check(self, context, active_export=True if self.offlineRenderType == 'online' else False)

        if report_value:
            self.report({'ERROR'}, report_string)
            return{'CANCELLED'}
        
        # Start execution timer
        if self.offlineRenderType == "online":
            start = time.time()

        # Live UI timer (updated manually as progress is made)
        context.window_manager.progress_begin(0, 9999)
        
        export_and_preview_setup(self, context)

        if context.active_object:
            if context.object.type in {'MESH', 'CURVE', 'FONT', 'SURFACE', 'META', 'LATTICE', 'ARMATURE', 'CAMERA'}:
                activeCallback = context.active_object.name
                modeCallback = context.object.mode

                bpy.ops.object.mode_set(mode = 'OBJECT')
                activeSelected = True

        # Scale up BG Plane (helps overscan & border pixels)
        plane_ob = bpy.data.objects["GD_Background Plane"]
        plane_ob.scale[0] = plane_ob.scale[1] = 3

        context.window_manager.progress_update(14)

        if grabDoc.uiVisibilityNormals and grabDoc.exportNormals and self.offlineRenderType == 'online' or self.offlineRenderType == "normals":
            normals_setup(self, context)
            normals_export(self, context)
            cleanup_ng_from_mat(self, context)

        context.window_manager.progress_update(28)

        if grabDoc.uiVisibilityCurvature and grabDoc.exportCurvature and self.offlineRenderType == 'online' or self.offlineRenderType == "curvature":
            curvature_setup(self, context)
            curvature_export(self, context)
            curvature_refresh(self, context)

        context.window_manager.progress_update(42)

        if grabDoc.uiVisibilityOcclusion and grabDoc.exportOcclusion and self.offlineRenderType == 'online' or self.offlineRenderType == "occlusion":
            occlusion_setup(self, context)
            occlusion_export(self, context)
            cleanup_ng_from_mat(self, context)
            occlusion_refresh(self, context)

        context.window_manager.progress_update(56)

        if grabDoc.uiVisibilityHeight and grabDoc.exportHeight and self.offlineRenderType == 'online' or self.offlineRenderType == "height":
            height_setup(self, context)
            height_export(self, context)
            cleanup_ng_from_mat(self, context)

        context.window_manager.progress_update(70)

        if grabDoc.uiVisibilityMatID and grabDoc.exportMatID and self.offlineRenderType == 'online' or self.offlineRenderType == "ID":
            id_setup(self, context)
            id_export(self, context)

        context.window_manager.progress_update(84)

        # Scale down BG Plane (helps overscan & border pixels)
        plane_ob = bpy.data.objects["GD_Background Plane"]
        plane_ob.scale[0] = plane_ob.scale[1] = 1

        # Refresh all original settings
        export_refresh(self, context)

        if grabDoc.exportPlane:
            export_bg_plane(self, context)

        # Call for Original Context Mode (Use bpy.ops so that Blenders viewport refreshes)
        if 'activeSelected' in locals():
            context.view_layer.objects.active = bpy.data.objects[activeCallback]
            bpy.ops.object.mode_set(mode = modeCallback)

        context.window_manager.progress_update(98)

        if self.offlineRenderType == "online":
            if grabDoc.openFolderOnExport:
                bpy.ops.wm.path_open(filepath = grabDoc.exportPath)

            # End the timer
            end = time.time()
            timeSpent = end - start

            self.report({'INFO'}, f"Export completed! (execution time: {str((round(timeSpent, 2)))}s)")
        else:
            self.report({'INFO'}, "Offline render completed!")
            
            # Reset so default can be the realtime renderer
            self.offlineRenderType = "online"

        context.window_manager.progress_end()
        return{'FINISHED'}


class GRABDOC_OT_send_to_marmo(OpInfo, Operator):
    bl_idname = "grab_doc.bake_marmoset"
    bl_label = "Open / Refresh in Marmoset"
    bl_description = "Export your models, open & bake (if turned on) in Marmoset Toolbag utilizing the settings set within the 'View / Edit Maps' tab"
    
    send_type: EnumProperty(items=(('open',"Open",""),
                                   ('refresh', "Refresh", "")),
                                   options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return(os.path.exists(context.scene.grabDoc.marmoExportPath))

    def execute(self, context):
        grabDoc = context.scene.grabDoc

        report_value, report_string = bad_setup_check(self, context, active_export=True)

        if report_value:
            self.report({'ERROR'}, report_string)
            return{'CANCELLED'}

        if grabDoc.imageType != "PNG":
            self.report({'ERROR'}, "Non PNG formats are currently not supported for external baking in Marmoset")
            return{'FINISHED'}

        # Add-on root path 
        addon_path = os.path.dirname(__file__)
        
        # Temporary model path 
        temps_path = os.path.join(addon_path, "Temp")

        # Create the directory 
        if not os.path.exists(temps_path):
            os.mkdir(temps_path)

        selectedCallback = context.view_layer.objects.selected.keys()

        if context.active_object:
            bpy.ops.object.mode_set(mode = 'OBJECT')

        if grabDoc.exportHeight:
            if grabDoc.rangeTypeHeight == 'AUTO':
                find_tallest_object(self, context)

        for ob in context.view_layer.objects:
            ob.select_set(False)
            if ob.name in self.render_list:
                if ob.visible_get():
                    ob.select_set(True)
                    if ob.name.startswith('GD_'):
                        obCopy = ob.copy()
                        context.collection.objects.link(obCopy)
                        obCopy.name = "GrabDoc_high GD_Background Plane"

                        ob.name = f"GrabDoc_low {ob.name}"
                    else:
                        ob.name = f"GrabDoc_high {ob.name}"

        # Reselect BG Plane high poly
        bpy.data.objects['GrabDoc_high GD_Background Plane'].select_set(True)

        for mat in bpy.data.materials:
            if mat.name == "GD_Reference":
                bpy.data.materials.remove(mat)

        # Export models
        bpy.ops.export_scene.fbx(filepath=f"{temps_path}\\grabdoc_temp_model.fbx",
                                 use_selection=True,
                                 path_mode='ABSOLUTE')

        if "GrabDoc_high GD_Background Plane" in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects["GrabDoc_high GD_Background Plane"])

        for ob in context.selected_objects:
            if ob.name == "GrabDoc_low GD_Background Plane":
                ob.name = ob.name[12:]
            else:
                ob.name = ob.name[13:]
            ob.select_set(False)

        for o in selectedCallback:
            if ob.visible_get():
                ob = context.scene.objects.get(o)
                ob.select_set(True)

        # Create a dictionary of variables to transfer into Marmoset
        marmo_vars = {'file_path': f'{grabDoc.exportPath}{grabDoc.exportName}.{grabDoc.imageType.lower()}',
                      'file_path_no_ext': grabDoc.exportPath,
                      'marmo_sky_path': f'{os.path.dirname(grabDoc.marmoExportPath)}\\data\\sky\\Evening Clouds.tbsky',

                      'resolution_x': grabDoc.exportResX,
                      'resolution_y': grabDoc.exportResY,
                      'bits_per_channel': int(grabDoc.colorDepth),
                      'samples': int(grabDoc.marmoSamples),

                      'auto_bake': grabDoc.marmoAutoBake,
                      'close_after_bake': grabDoc.marmoClosePostBake,
                      'open_folder': grabDoc.openFolderOnExport,

                      'export_normals': grabDoc.exportNormals & grabDoc.uiVisibilityNormals,
                      'flipy_normals': grabDoc.flipYNormals,

                      'export_curvature': grabDoc.exportCurvature & grabDoc.uiVisibilityCurvature,

                      'export_occlusion': grabDoc.exportOcclusion & grabDoc.uiVisibilityOcclusion,
                      'ray_count_occlusion': grabDoc.marmoAORayCount,

                      'export_height': grabDoc.exportHeight & grabDoc.uiVisibilityHeight,
                      'flat_height': grabDoc.flatMaskHeight,
                      'cage_height': grabDoc.guideHeight * 100 * 2,

                      'export_matid': grabDoc.exportMatID & grabDoc.uiVisibilityMatID}

        # Flip the slashes of the first Dict value (It's gross but I don't know how to do it any other way without an error in Marmoset)
        for key, value in marmo_vars.items():
            marmo_vars[key] = value.replace("\\", "/")
            break
        
        # Serializing
        marmo_json = json.dumps(marmo_vars, indent = 4)

        # Writing
        with open(temps_path + "\\" + "marmo_vars.json", "w") as outfile:
            outfile.write(marmo_json)
        
        path_ext_only = os.path.basename(os.path.normpath(grabDoc.marmoExportPath)).encode()

        if grabDoc.exportPlane:
            export_bg_plane(self, context)

        if self.send_type == 'refresh':
            subproc = subprocess.check_output('tasklist', shell=True)
            if not path_ext_only in subproc:
                subprocess.Popen([grabDoc.marmoExportPath, os.path.join(addon_path, "grabdoc_marmo.py")])

                self.report({'INFO'}, "Export completed! Opening Marmoset Toolbag...")
            else:
                if grabDoc.marmoAutoBake:
                    self.report({'INFO'}, "Models re-exported! Check Marmoset Toolbag.")
                else:
                    self.report({'INFO'}, "Models re-exported! Check Marmoset Toolbag. (Rebake required)")
        else:
            subprocess.Popen([grabDoc.marmoExportPath, os.path.join(addon_path, "grabdoc_marmo.py")])

            self.report({'INFO'}, "Export completed! Opening Marmoset Toolbag...")
        return{'FINISHED'}


################################################################################################################
# MAP PREVIEWER
################################################################################################################


def draw_callback_px(self, context):
    font_id = 0

    blf.position(font_id, 15, 140, 0)
    blf.size(font_id, 26, 72)
    blf.draw(font_id, f"{self.preview_type.capitalize()} Preview | 'ESC' to leave")

    blf.position(font_id, 15, 90, 0)
    blf.size(font_id, 21, 72)
    blf.draw(font_id, "You are currently in Map Preview mode!")


class GRABDOC_OT_leave_map_preview(Operator):
    bl_idname = "grab_doc.leave_modal"
    bl_label = "Leave Map Preview"
    bl_description = "Leave the current Map Preview"
    bl_options = {'INTERNAL', 'REGISTER'}

    def execute(self, context):
        context.scene.grabDoc.modalState = False
        return{'FINISHED'}


class GRABDOC_OT_map_preview_warning(OpInfo, Operator):
    """Preview the selected material"""
    bl_idname = "grab_doc.preview_warning"
    bl_label = "    MATERIAL PREVIEW WARNING"
    bl_options = {'INTERNAL'}

    preview_type: EnumProperty(items=(('normals', "", ""),
                                      ('curvature', "", ""),
                                      ('occlusion', "", ""),
                                      ('height', "", ""),
                                      ('ID', "", "")),
                                      options={'HIDDEN'})

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width = 550)

    def draw(self, context):
        layout = self.layout
        
        col = layout.column()
        col.separator()

        col.label(text = "Live Material Preview is a feature that allows you to view what your bake maps will look like")
        col.label(text = "in real-time. Consider this warning: This feature is strictly meant for viewing your materials &")
        col.label(text = "not for editing while inside a preview. Once finished previewing, please exit to avoid instability.")
        col.label(text = "")
        col.label(text = "Pressing 'OK' will dismiss this warning permanently for this project file.")

    def execute(self, context):
        context.scene.grabDoc.firstBakePreview = False

        bpy.ops.grab_doc.preview_map(preview_type = self.preview_type)
        return{'FINISHED'}


class GRABDOC_OT_map_preview(OpInfo, Operator):
    """Preview the selected material"""
    bl_idname = "grab_doc.preview_map"
    bl_label = ""
    bl_options = {'INTERNAL'}

    preview_type: EnumProperty(items=(('normals', "", ""),
                                      ('curvature', "", ""),
                                      ('occlusion', "", ""),
                                      ('height', "", ""),
                                      ('ID', "", "")),
                                      options={'HIDDEN'})

    def modal(self, context, event):
        grabDoc = context.scene.grabDoc
        view_settings = context.scene.view_settings
        scene_shading = bpy.data.scenes[str(context.scene.name)].display.shading
        eevee = context.scene.eevee

        # Idea for UI blocking
        #if event.type == 'LEFTMOUSE':
        #    return {'INTERFACE'}

        context.scene.camera = bpy.data.objects["GD_Trim Camera"]

        # Set - Exporter settings
        image_settings = context.scene.render.image_settings

        image_settings.file_format = grabDoc.imageType

        if grabDoc.imageType == 'TIFF':
            image_settings.tiff_codec = grabDoc.imageCompTIFF
        if grabDoc.imageType == 'PNG':
            image_settings.compression = grabDoc.imageComp

        if grabDoc.imageType != 'TARGA':
            image_settings.color_depth = grabDoc.colorDepth

        if self.preview_type == "normals":
            context.scene.eevee.taa_render_samples = grabDoc.samplesNormals
    
        elif self.preview_type == "curvature":
            context.scene.display.render_aa = grabDoc.samplesCurvature
            view_settings.look = grabDoc.contrastCurvature.replace('_', ' ')

            bpy.data.objects["GD_Background Plane"].color[3] = .9999

            # Refresh specific settings
            if self.done:
                curvature_refresh(self, context)

        elif self.preview_type == "occlusion":
            eevee.taa_render_samples = grabDoc.samplesOcclusion
            eevee.gtao_distance = grabDoc.distanceOcclusion
            view_settings.look = grabDoc.contrastOcclusion.replace('_', ' ')

            # Refresh specific settings
            if self.done:
                occlusion_refresh(self, context)

        elif self.preview_type == "height":
            eevee.taa_render_samples = grabDoc.samplesHeight

        elif self.preview_type == "ID":
            context.scene.display.render_aa = grabDoc.samplesMatID

            # Choose the method of ID creation based on user preference
            scene_shading.color_type = grabDoc.methodMatID

        is_setup = proper_scene_setup()

        # Exiting    
        if self.done:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')

            cleanup_ng_from_mat(self, context)
            export_refresh(self, context)

            # Refresh - Current workspace shading type
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        space.shading.type = self.saved_render_view
                        break
            
            # Refresh - Original workspace shading type
            for screen in bpy.data.workspaces[self.savedOriginalWorkspace].screens:
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        for space in area.spaces:
                            space.shading.type = self.saved_render_view
                            break

            grabDoc.bakerType = self.savedBakerType

            # Check for auto exit camera option (Keep this at the end of the stack to avoid pop in)
            if grabDoc.autoExitCamera or not is_setup:
                bpy.ops.grab_doc.view_cam(from_modal=True)
            return {'CANCELLED'}

        # Exit checking
        if not grabDoc.modalState or event.type in {'ESC'} or not is_setup:
            bpy.ops.grab_doc.leave_modal()
            self.done = True
            return {'PASS_THROUGH'}
        return {'PASS_THROUGH'}

    def execute(self, context):
        grabDoc = context.scene.grabDoc

        report_value, report_string = bad_setup_check(self, context, active_export = False)

        if report_value:
            self.report({'ERROR'}, report_string)
            return{'CANCELLED'}

        self.done = False
        grabDoc.modalState = True

        if context.active_object:
            bpy.ops.object.mode_set(mode = 'OBJECT')

        export_and_preview_setup(self, context)
        
        if [area.spaces.active.region_3d.view_perspective for area in context.screen.areas if area.type == 'VIEW_3D'] != ['CAMERA']:
            bpy.ops.view3d.view_camera()

        # Save & Set - Shading type
        self.savedOriginalWorkspace = context.workspace.name

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    self.saved_render_view = space.shading.type
                    space.shading.type = 'RENDERED'
                    break

        # Save & Set - UI Baker Type
        self.savedBakerType = grabDoc.bakerType
        grabDoc.bakerType = 'Blender'

        # Set - Preview type
        grabDoc.modalPreviewType = self.preview_type

        if self.preview_type == 'normals':
            normals_setup(self, context)
        elif self.preview_type == 'curvature':
            curvature_setup(self, context)
        elif self.preview_type == 'occlusion':
            occlusion_setup(self, context)
        elif self.preview_type == 'height':
            height_setup(self, context)
        else: # ID
            id_setup(self, context)

        # Draw text handler
        args = (self, context)
        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')

        # Modal handler
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class GRABDOC_OT_export_current_preview(OpInfo, Operator):
    """Export the currently previewed material"""
    bl_idname = "grab_doc.export_preview"
    bl_label = "Export Previewed Map"

    @classmethod
    def poll(cls, context):
        return(context.scene.grabDoc.modalState)

    def execute(self, context):
        grabDoc = context.scene.grabDoc

        report_value, report_string = bad_setup_check(self, context, active_export = True)

        if report_value:
            self.report({'ERROR'}, report_string)
            return{'CANCELLED'}

        # Start counting execution time
        start = time.time()

        # Save - file output path
        render = context.scene.render
        savedPath = render.filepath

        # Set - Output path to add-on path + add-on name + the type of map exported (file extensions get handled automatically)
        render.filepath = grabDoc.exportPath + grabDoc.exportName + f"_{grabDoc.modalPreviewType}"

        bpy.ops.render.render(write_still = True)

        # Refresh - file output path
        render.filepath = savedPath

        # Reimport the Normal map as a material if requested
        if grabDoc.modalPreviewType == 'normals' and grabDoc.reimportAsMatNormals:
            normals_reimport_as_mat(self, context)

        # Reimport the Occlusion map as a material if requested
        elif grabDoc.modalPreviewType == 'occlusion' and grabDoc.reimportAsMatOcclusion:
            occlusion_reimport_as_mat(self, context)

        if grabDoc.exportPlane:
            export_bg_plane(self, context)
        
        # Open export path location if requested
        if grabDoc.openFolderOnExport:
            bpy.ops.wm.path_open(filepath = grabDoc.exportPath)

        # End the timer
        end = time.time()
        timeSpent = end - start

        self.report({'INFO'}, f"Export completed! (execution time: {str((round(timeSpent, 2)))}s)")
        return{'FINISHED'}


################################################################################################################
# REGISTRATION
################################################################################################################


classes = (GRABDOC_OT_open_folder,
           GRABDOC_OT_load_ref,
           GRABDOC_OT_view_cam,
           GRABDOC_OT_setup_scene,
           GRABDOC_OT_remove_setup,
           GRABDOC_OT_quick_id_setup,
           GRABDOC_OT_quick_id_selected,
           GRABDOC_OT_quick_remove_random_mats,
           GRABDOC_OT_quick_remove_manual_mats,
           GRABDOC_OT_quick_remove_selected_mats,
           GRABDOC_OT_export_maps,
           GRABDOC_OT_map_preview_warning,
           GRABDOC_OT_map_preview,
           GRABDOC_OT_leave_map_preview,
           GRABDOC_OT_export_current_preview,
           GRABDOC_OT_send_to_marmo)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

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