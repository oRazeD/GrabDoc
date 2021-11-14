
import bpy, time, os, blf, bmesh
from bpy.types import Operator
from bpy.props import EnumProperty
from .generic_utils import OpInfo, proper_scene_setup, bad_setup_check, export_bg_plane
from .node_group_utils import ng_setup, cleanup_ng_from_mat, add_ng_to_mat
from .render_setup_utils import find_tallest_object


################################################################################################################
# SCENE SETUP
################################################################################################################


def scene_setup_and_refresh(self, context):
    grabDoc = context.scene.grabDoc
    view_layer = context.view_layer

    # PRELIMINARY

    savedActiveColl = view_layer.active_layer_collection
    selectedCallback = view_layer.objects.selected.keys()

    if context.active_object:
        if context.object.type in ('MESH', 'CURVE', 'FONT', 'SURFACE', 'META', 'LATTICE', 'ARMATURE', 'CAMERA'):
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

    # COLLECTIONS

    # Do some checks to see if the user wants to only render out the objects in a specific collection
    objectsColl = "GrabDoc Objects (put objects here)"
    if grabDoc.onlyRenderColl:
        if not objectsColl in bpy.data.collections:
            bpy.data.collections.new(name = objectsColl)
            context.scene.collection.children.link(bpy.data.collections[objectsColl])
            view_layer.active_layer_collection = view_layer.layer_collection.children[-1]
    else:
        if objectsColl in bpy.data.collections:
            for ob in bpy.data.collections[objectsColl].all_objects:
                # Move object to the master collection
                context.scene.collection.objects.link(ob)
                
                # Remove the objects from the grabdoc collection
                ob.users_collection[0].objects.unlink(ob)

            # Delete the collection
            bpy.data.collections.remove(bpy.data.collections[objectsColl])

    # Remove objects accidentally placed by the user in the GD collection into the master collection
    gdColl = "GrabDoc (do not touch contents)"
    if gdColl in bpy.data.collections:
        for ob in bpy.data.collections[gdColl].all_objects:
            if ob.name not in ('GD_Background Plane', 'GD_Orient Guide', 'GD_Trim Camera'):
                # Move object to the master collection
                context.scene.collection.objects.link(ob)

                # Remove the objects from the grabdoc collection
                ob.users_collection[0].objects.unlink(ob)

    # Create main GrabDoc collection
    if gdColl in bpy.data.collections:
        bpy.data.collections.remove(bpy.data.collections[gdColl])

    grabDocColl = bpy.data.collections.new(name = gdColl)
    context.scene.collection.children.link(grabDocColl)
    view_layer.active_layer_collection = view_layer.layer_collection.children[-1]

    # Make the GrabDoc collection the active one
    view_layer.active_layer_collection = view_layer.layer_collection.children[grabDocColl.name]

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

    trim_cam_ob.location = (0, 0, 15 * grabDoc.scalingSet)
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
        pc_height_guide = manual_height_guide_point_cloud("GD_Height Guide")
        context.collection.objects.link(pc_height_guide)

        # Parent the height guide to the BG Plane
        pc_height_guide.parent = plane_ob
        pc_height_guide.hide_select = True

    # ORIENT GUIDE

    # Remove pre existing orient guide & all related data blocks
    if "GD_Orient Guide" in bpy.data.objects:
        bpy.data.meshes.remove(bpy.data.objects["GD_Orient Guide"].data)

    plane_y = plane_ob.dimensions.y / 2

    pc_orient = uv_orient_point_cloud("GD_Orient Guide", [(-.3, plane_y + .1, 0), (.3, plane_y + .1, 0), (0, plane_y + .35, 0)])
    context.collection.objects.link(pc_orient)

    # Parent the height guide to the BG Plane
    pc_orient.parent = plane_ob
    pc_orient.hide_select = True
    
    # NODE GROUPS

    ng_setup(self, context)

    # CLEANUP

    # Select original object(s)
    for o in selectedCallback:
        ob = context.scene.objects.get(o)
        ob.select_set(True)

    # Select original active collection, active object & the context mode
    if 'savedActiveColl' in locals():
        view_layer.active_layer_collection = savedActiveColl

    view_layer.objects.active = bpy.data.objects[activeCallback] if activeCallback else None

    if 'modeCallback' in locals() and activeCallback:
        bpy.ops.object.mode_set(mode = modeCallback)

    # Hide collections & make unselectable if requested (runs after everything else)
    grabDocColl.hide_select = not grabDoc.collSelectable
    grabDocColl.hide_viewport = not grabDoc.collVisible
    grabDocColl.hide_render = not grabDoc.collRendered


def manual_height_guide_point_cloud(ob_name, edges = [(0,4), (1,5), (2,6), (3,7), (4,5), (5,6), (6,7), (7,4)], faces = []):
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


def uv_orient_point_cloud(ob_name, vertices, edges = [(0,2), (0,1), (1,2)], faces = []):
    # Create new mesh & object data blocks
    meNew = bpy.data.meshes.new(ob_name)
    obNew = bpy.data.objects.new(ob_name, meNew)

    # Make a mesh from a list of vertices / edges / faces
    meNew.from_pydata(vertices, edges, faces)

    # Display name & update the mesh
    meNew.update()
    return obNew


################################################################################################################
# BAKER SETUP & CLEANUP
################################################################################################################


def export_and_preview_setup(self, context):
    grabDoc = context.scene.grabDoc
    render = context.scene.render

    # TODO Preserve use_local_camera & original camera

    # Set - Active Camera
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                space.use_local_camera = False
                break

    context.scene.camera = bpy.data.objects.get("GD_Trim Camera")

        ## VIEW LAYER PROPERTIES ##

    # Save & Set - View layer
    self.savedViewLayerUse = context.view_layer.use
    self.savedUseSingleLayer = render.use_single_layer

    context.view_layer.use = True
    render.use_single_layer = True

        ## WORLD PROPERTIES ##

    context.scene.world.use_nodes = False

        ## RENDER PROPERTIES ##

    eevee = context.scene.eevee

    # Save - Render Engine (Set per bake map)
    self.savedRenderer = render.engine

    # Save - Sampling (Set per bake map)
    self.savedWorkbenchSampling = context.scene.display.render_aa
    self.savedWorkbenchVPSampling = context.scene.display.viewport_aa
    self.savedEeveeRenderSampling = eevee.taa_render_samples
    self.savedEeveeSampling = eevee.taa_samples

    # Save & Set - Bloom
    self.savedUseBloom = eevee.use_bloom

    eevee.use_bloom = False

    # Save & Set - Ambient Occlusion
    self.savedUseAO = eevee.use_gtao
    self.savedAODistance = eevee.gtao_distance
    self.savedAOQuality = eevee.gtao_quality

    eevee.use_gtao = False # Disable unless needed for AO bakes
    eevee.gtao_distance = .2
    eevee.gtao_quality = .5

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

    # Set - Dimensions (Don't bother saving these)
    render.resolution_x = grabDoc.exportResX
    render.resolution_y = grabDoc.exportResY
    render.resolution_percentage = 100

    # Save & Set - Output
    self.savedColorMode = image_settings.color_mode
    self.savedFileFormat = image_settings.file_format

    image_settings.file_format = grabDoc.imageType

    if grabDoc.imageType == 'OPEN_EXR':
        image_settings.color_depth = grabDoc.colorDepthEXR
    elif grabDoc.imageType != 'TARGA':
        image_settings.color_depth = grabDoc.colorDepthPNG

    if grabDoc.imageType == "PNG":
        image_settings.compression = grabDoc.imageCompPNG
    
    self.savedColorDepth = image_settings.color_depth

    # Save & Set - Post Processing
    self.savedUseSequencer = render.use_sequencer
    self.savedUseCompositer = render.use_compositing
    self.savedDitherIntensity = render.dither_intensity
    self.savedUseCompositingNodes = context.scene.use_nodes

    render.use_sequencer = render.use_compositing = context.scene.use_nodes = False
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

    scene_shading.show_backface_culling = scene_shading.show_xray = scene_shading.show_shadows = False
    scene_shading.show_cavity = scene_shading.use_dof = scene_shading.show_object_outline = False
    scene_shading.show_specular_highlight = False

        ## PLANE REFERENCE ##

    self.savedRefSelection = grabDoc.refSelection.name if grabDoc.refSelection else None
    
        ## OBJECT VISIBILITY ##

    bg_plane = bpy.data.objects.get("GD_Background Plane")
   
    bg_plane.hide_viewport = not grabDoc.collVisible
    bg_plane.hide_render = not grabDoc.collRendered
    bg_plane.hide_set(False)

    self.ob_hidden_render_list = []
    self.ob_hidden_vp_list = []
    
    # Save & Set - Non-rendered objects visibility (self.render_list defined in bad_setup_check)
    for ob in context.view_layer.objects:
        if ob.type in ('MESH', 'CURVE') and not ob.name in self.render_list:
            if not ob.hide_render:
                self.ob_hidden_render_list.append(ob.name)
            ob.hide_render = True

            if not ob.hide_viewport:
                self.ob_hidden_vp_list.append(ob.name)
            ob.hide_viewport = True


def export_refresh(self, context):
    scene = context.scene
    grabDoc = scene.grabDoc
    render = scene.render

        ## VIEW LAYER PROPERTIES ##

    # Refresh - View layer
    context.view_layer.use = self.savedViewLayerUse
    scene.render.use_single_layer = self.savedUseSingleLayer

        ## WORLD PROPERTIES ##

    context.scene.world.use_nodes = True

        ## RENDER PROPERTIES ##

    # Refresh - Render Engine
    render.engine = self.savedRenderer

    # Refresh - Sampling
    scene.display.render_aa = self.savedWorkbenchSampling
    scene.display.viewport_aa = self.savedWorkbenchVPSampling
    scene.eevee.taa_render_samples = self.savedEeveeRenderSampling
    scene.eevee.taa_samples = self.savedEeveeSampling

    # Refresh - Bloom
    scene.eevee.use_bloom = self.savedUseBloom

    # Refresh - Color Management
    view_settings = scene.view_settings

    view_settings.look = self.savedContrastType
    scene.display_settings.display_device = self.savedDisplayDevice
    view_settings.view_transform = self.savedViewTransform
    view_settings.exposure = self.savedExposure
    view_settings.gamma = self.savedGamma

    # Refresh - Performance
    if bpy.app.version >= (2, 83, 0):
        render.use_high_quality_normals = self.savedHQNormals

        ## OUTPUT PROPERTIES ##

    # Refresh - Output
    render.image_settings.color_depth = self.savedColorDepth
    render.image_settings.color_mode = self.savedColorMode
    render.image_settings.file_format = self.savedFileFormat

    # Refresh - Post Processing
    render.use_sequencer = self.savedUseSequencer
    render.use_compositing = self.savedUseCompositer
    scene.use_nodes = self.savedUseCompositingNodes

    render.dither_intensity = self.savedDitherIntensity

        ## VIEWPORT SHADING ##

    scene_shading = bpy.data.scenes[str(scene.name)].display.shading

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


class GRABDOC_OT_setup_scene(OpInfo, Operator):
    """Setup / Refresh your current scene. Useful if you messed up something within the GrabDoc collections that you don't know how to properly revert"""
    bl_idname = "grab_doc.setup_scene"
    bl_label = "Setup / Refresh GrabDoc Scene"

    def execute(self, context):
        scene_setup_and_refresh(self, context)
        return{'FINISHED'}


class GRABDOC_OT_remove_setup(OpInfo, Operator):
    """Completely removes every element of GrabDoc from the scene, not including images reimported after bakes"""
    bl_idname = "grab_doc.remove_setup"
    bl_label = "Remove Setup"

    def execute(self, context):
        # Remove GD Node Groups
        for group in bpy.data.node_groups:
            if group.name in ('GD_Normal', 'GD_Height', 'GD_Ambient Occlusion', 'GD_Alpha'):
                bpy.data.node_groups.remove(group)

        objectsColl = "GrabDoc Objects (put objects here)"
        if objectsColl in bpy.data.collections:
            for ob in bpy.data.collections[objectsColl].all_objects:
                # Move object to the master collection
                context.scene.collection.objects.link(ob)

                # Remove the objects from the grabdoc collection
                ob.users_collection[0].objects.unlink(ob)

            bpy.data.collections.remove(bpy.data.collections[objectsColl])

        # Remove objects accidentally placed by the user in the GD collection into the master collection
        gdColl = "GrabDoc (do not touch contents)"
        if gdColl in bpy.data.collections:
            for ob in bpy.data.collections[gdColl].all_objects:
                if ob.name not in ('GD_Background Plane', 'GD_Orient Guide', 'GD_Trim Camera'):
                    # Move object to the master collection
                    context.scene.collection.objects.link(ob)

                    # Remove the objects from the grabdoc collection
                    ob.users_collection[0].objects.unlink(ob)

            bpy.data.collections.remove(bpy.data.collections["GrabDoc (do not touch contents)"])

        # Remove all GD objects, references & cameras
        if "GD_Reference" in bpy.data.materials:
            bpy.data.materials.remove(bpy.data.materials["GD_Reference"])

        for ob in bpy.data.objects:
            if ob.name in ("GD_Height Guide", "GD_Orient Guide", "GD_Background Plane"):
                bpy.data.meshes.remove(bpy.data.meshes[ob.name])

            elif ob.name == "GD_Trim Camera":
                bpy.data.cameras.remove(bpy.data.cameras[ob.name])
        return{'FINISHED'}


################################################################################################################
# INDIVIDUAL MATERIAL SETUP & CLEANUP
################################################################################################################


# NORMALS
def normals_setup(self, context):
    scene = context.scene
    render = scene.render

    render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = scene.eevee.taa_samples = scene.grabDoc.samplesNormals
    render.image_settings.color_mode = 'RGBA'
    scene.display_settings.display_device = 'None'

    add_ng_to_mat(self, context, setup_type='GD_Normal')


def normals_reimport_as_mat(self, context):
    grabDoc = context.scene.grabDoc

    mat_name = f'{grabDoc.exportName}_normal'

    # Remove pre-existing material
    for mat in bpy.data.materials:
        if mat.name == mat_name:
            bpy.data.materials.remove(mat)
            break

    # Remove original image
    for image in bpy.data.images:
        if image.name == mat_name:
            bpy.data.images.remove(image)
            break

    # Create material
    mat = bpy.data.materials.new(name=mat_name)
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
    else: # PNG
        file_extension = '.png'

    image_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    image_node.image = bpy.data.images.load(f'{bpy.path.abspath(grabDoc.exportPath)}{mat_name}{file_extension}')
    image_node.image.colorspace_settings.name = 'Linear'
    image_node.location = (-800,0)

    # Rename the newly imported image
    bpy.data.images[f'{mat_name}{file_extension}'].name = mat_name

    # Make links
    link = mat.node_tree.links

    link.new(normal_map_node.inputs['Color'], image_node.outputs['Color'])
    link.new(bsdf_node.inputs['Normal'], normal_map_node.outputs['Normal'])


# CURVATURE
def curvature_setup(self, context):
    scene = context.scene
    grabDoc = scene.grabDoc
    scene_shading = bpy.data.scenes[str(scene.name)].display.shading
    
    # Set - Render engine settings
    scene.view_settings.look = grabDoc.contrastCurvature.replace('_', ' ')

    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.render_aa = scene.display.viewport_aa = grabDoc.samplesCurvature
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

    self.savedSingleList = [] # List for single_color because saving the variable on its own isn't enough for whatever reason

    for i in scene_shading.single_color:
        self.savedSingleList.append(i)
    
    scene_shading.show_cavity = True
    scene_shading.cavity_type = 'BOTH'
    scene_shading.cavity_ridge_factor = scene_shading.curvature_ridge_factor = grabDoc.ridgeCurvature
    scene_shading.curvature_valley_factor = grabDoc.valleyCurvature
    scene_shading.cavity_valley_factor = 0
    scene_shading.single_color = (.214041, .214041, .214041)

    scene.display.matcap_ssao_distance = .075


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


# AMBIENT OCCLUSION
def occlusion_setup(self, context):
    scene = context.scene
    grabDoc = scene.grabDoc
    eevee = scene.eevee
    
    scene.render.engine = 'BLENDER_EEVEE'
    eevee.taa_render_samples = eevee.taa_samples = grabDoc.samplesOcclusion
    scene.render.image_settings.color_mode = 'BW'
    scene.display_settings.display_device = 'None'

    # Save & Set - Overscan (Can help with screenspace effects)
    self.savedUseOverscan = eevee.use_overscan
    self.savedOverscanSize = eevee.overscan_size

    eevee.use_overscan = True
    eevee.overscan_size = 10

    # Set - Ambient Occlusion
    eevee.use_gtao = True

    scene.view_settings.look = grabDoc.contrastOcclusion.replace('_', ' ')

    add_ng_to_mat(self, context, setup_type='GD_Ambient Occlusion')


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
    image_node.image = bpy.data.images.load(f'{bpy.path.abspath(grabDoc.exportPath)}{grabDoc.exportName}_AO{file_extension}')
    image_node.location = (-300,0)

    # Rename the newly imported image
    bpy.data.images[f'{grabDoc.exportName}_AO{file_extension}'].name = f'{grabDoc.exportName}_AO'

    # Make links
    link = mat.node_tree.links

    link.new(output_node.inputs['Surface'], image_node.outputs['Color'])


# HEIGHT
def height_setup(self, context):
    scene = context.scene
    grabDoc = scene.grabDoc

    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = scene.eevee.taa_samples = grabDoc.samplesHeight
    scene.render.image_settings.color_mode = 'BW'
    scene.display_settings.display_device = 'None'

    scene.view_settings.look = grabDoc.contrastHeight.replace('_', ' ')

    add_ng_to_mat(self, context, setup_type='GD_Height')

    if grabDoc.rangeTypeHeight == 'AUTO':
        find_tallest_object(self, context)


# MATERIAL ID
def id_setup(self, context):
    scene = context.scene
    grabDoc = scene.grabDoc
    render = scene.render
    scene_shading = bpy.data.scenes[str(scene.name)].display.shading

    render.engine = 'BLENDER_WORKBENCH'
    scene.display.render_aa = scene.display.viewport_aa = grabDoc.samplesMatID
    scene_shading.light = 'FLAT'
    render.image_settings.color_mode = 'RGBA'
    scene.display_settings.display_device = 'sRGB'

    # Choose the method of ID creation based on user preference
    scene_shading.color_type = grabDoc.methodMatID


# ALPHA
def alpha_setup(self, context):
    scene = context.scene
    render = scene.render

    render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = scene.eevee.taa_samples = scene.grabDoc.samplesAlpha
    render.image_settings.color_mode = 'BW'
    scene.display_settings.display_device = 'None'

    add_ng_to_mat(self, context, setup_type='GD_Alpha')


# ALBEDO
def albedo_setup(self, context):
    scene = context.scene
    render = scene.render

    render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = scene.eevee.taa_samples = scene.grabDoc.samplesAlbedo
    render.image_settings.color_mode = 'RGBA'
    scene.display_settings.display_device = 'sRGB'

    add_ng_to_mat(self, context, setup_type='GD_Albedo')


# ROUGHNESS
def roughness_setup(self, context):
    scene = context.scene
    render = scene.render

    render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = scene.eevee.taa_samples = scene.grabDoc.samplesRoughness
    render.image_settings.color_mode = 'RGBA'
    scene.display_settings.display_device = 'sRGB'

    add_ng_to_mat(self, context, setup_type='GD_Roughness')


# METALNESS
def metalness_setup(self, context):
    scene = context.scene
    render = scene.render

    render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = scene.eevee.taa_samples = scene.grabDoc.samplesMetalness
    render.image_settings.color_mode = 'RGBA'
    scene.display_settings.display_device = 'sRGB'

    add_ng_to_mat(self, context, setup_type='GD_Metalness')


################################################################################################################
# MAP EXPORTER
################################################################################################################


def grabdoc_export(self, context, export_suffix):
    grabDoc = context.scene.grabDoc
    render = context.scene.render
    
    # Save - file output path
    savedPath = render.filepath

    # Set - Output path to add-on path + add-on name + the type of map exported (file extensions handled automatically)
    render.filepath = bpy.path.abspath(grabDoc.exportPath) + grabDoc.exportName + '_' + export_suffix

    context.scene.camera = bpy.data.objects["GD_Trim Camera"]

    bpy.ops.render.render(write_still = True)

    # Refresh - file output path
    render.filepath = savedPath


class GRABDOC_OT_export_maps(OpInfo, Operator):
    """Export all enabled bake maps"""
    bl_idname = "grab_doc.export_maps"
    bl_label = "Export Maps"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return not context.scene.grabDoc.modalState

    def execute(self, context):
        grabDoc = context.scene.grabDoc

        report_value, report_string = bad_setup_check(self, context, active_export=True)

        self.render_type = 'export'

        if report_value:
            self.report({'ERROR'}, report_string)
            return{'CANCELLED'}

        # Start execution timer
        start = time.time()

        # Live UI timer (updated manually as progress is made)
        context.window_manager.progress_begin(0, 9999)

        # System for dynamically deciding the progress percentage
        operation_counter = 3

        if grabDoc.uiVisibilityNormals and grabDoc.exportNormals:
            operation_counter += 1
        if grabDoc.uiVisibilityCurvature and grabDoc.exportCurvature:
            operation_counter += 1
        if grabDoc.uiVisibilityOcclusion and grabDoc.exportOcclusion:
            operation_counter += 1
        if grabDoc.uiVisibilityHeight and grabDoc.exportHeight:
            operation_counter += 1
        if grabDoc.uiVisibilityAlpha and grabDoc.exportAlpha:
            operation_counter += 1
        if grabDoc.uiVisibilityMatID and grabDoc.exportMatID:
            operation_counter += 1
        if grabDoc.uiVisibilityAlbedo and grabDoc.exportAlbedo:
            operation_counter += 1
        if grabDoc.uiVisibilityRoughness and grabDoc.exportRoughness:
            operation_counter += 1
        if grabDoc.uiVisibilityMetalness and grabDoc.exportMetalness:
            operation_counter += 1

        percentage_division = 100 / operation_counter
        percent_till_completed = 0

        export_and_preview_setup(self, context)

        if context.active_object and context.object.type in ('MESH', 'CURVE', 'FONT', 'SURFACE', 'META', 'LATTICE', 'ARMATURE', 'CAMERA'):
            activeCallback = context.active_object.name
            modeCallback = context.object.mode

            bpy.ops.object.mode_set(mode = 'OBJECT')
            activeSelected = True

        # Scale up BG Plane (helps overscan & border pixels)
        plane_ob = bpy.data.objects["GD_Background Plane"]
        plane_ob.scale[0] = plane_ob.scale[1] = 3

        percent_till_completed += percentage_division
        context.window_manager.progress_update(percent_till_completed)

        if grabDoc.uiVisibilityNormals and grabDoc.exportNormals:
            normals_setup(self, context)
            grabdoc_export(self, context, export_suffix=grabDoc.suffixNormals)

            # Reimport the Normal map as a material (if the option is turned on)
            if context.scene.grabDoc.reimportAsMatNormals:
                normals_reimport_as_mat(self, context)

            cleanup_ng_from_mat(self, context, setup_type='GD_Normal')

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if grabDoc.uiVisibilityCurvature and grabDoc.exportCurvature:
            curvature_setup(self, context)
            grabdoc_export(self, context, export_suffix=grabDoc.suffixCurvature)
            curvature_refresh(self, context)

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if grabDoc.uiVisibilityOcclusion and grabDoc.exportOcclusion:
            occlusion_setup(self, context)
            grabdoc_export(self, context, export_suffix=grabDoc.suffixOcclusion)

            # Reimport the Normal map as a material if requested
            if context.scene.grabDoc.reimportAsMatOcclusion:
                occlusion_reimport_as_mat(self, context)

            cleanup_ng_from_mat(self, context, setup_type='GD_Ambient Occlusion')
            occlusion_refresh(self, context)

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if grabDoc.uiVisibilityHeight and grabDoc.exportHeight:
            height_setup(self, context)
            grabdoc_export(self, context, export_suffix=grabDoc.suffixHeight)
            cleanup_ng_from_mat(self, context, setup_type='GD_Height')

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if grabDoc.uiVisibilityAlpha and grabDoc.exportAlpha:
            alpha_setup(self, context)
            grabdoc_export(self, context, export_suffix=grabDoc.suffixAlpha)
            cleanup_ng_from_mat(self, context, setup_type='GD_Alpha')

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if grabDoc.uiVisibilityMatID and grabDoc.exportMatID:
            id_setup(self, context)
            grabdoc_export(self, context, export_suffix=grabDoc.suffixID)

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if grabDoc.uiVisibilityAlbedo and grabDoc.exportAlbedo:
            albedo_setup(self, context)
            grabdoc_export(self, context, export_suffix=grabDoc.suffixAlbedo)
            cleanup_ng_from_mat(self, context, setup_type='GD_Albedo')

        if grabDoc.uiVisibilityRoughness and grabDoc.exportRoughness:
            roughness_setup(self, context)
            grabdoc_export(self, context, export_suffix=grabDoc.suffixRoughness)
            cleanup_ng_from_mat(self, context, setup_type='GD_Roughness')

        if grabDoc.uiVisibilityMetalness and grabDoc.exportMetalness:
            metalness_setup(self, context)
            grabdoc_export(self, context, export_suffix=grabDoc.suffixMetalness)
            cleanup_ng_from_mat(self, context, setup_type='GD_Metalness')

        percent_till_completed += percentage_division
        context.window_manager.progress_update(percent_till_completed)

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

        percent_till_completed += percentage_division
        context.window_manager.progress_update(percent_till_completed)

        if grabDoc.openFolderOnExport:
            bpy.ops.wm.path_open(filepath = bpy.path.abspath(grabDoc.exportPath))

        # End the timer
        end = time.time()
        timeSpent = end - start

        self.report({'INFO'}, f"Export completed! (execution time: {str((round(timeSpent, 2)))}s)")

        context.window_manager.progress_end()
        return{'FINISHED'}


################################################################################################################
# OFFLINE RENDERER
################################################################################################################


class GRABDOC_OT_offline_render(OpInfo, Operator):
    """Renders the selected material and previews it inside Blender"""
    bl_idname = "grab_doc.offline_render"
    bl_label = ""
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return not context.scene.grabDoc.modalState

    render_type: EnumProperty(
        items=(
            ('normals', "Normals", ""),
            ('curvature', "Curvature", ""),
            ('occlusion', "Ambient Occlusion", ""),
            ('height', "Height", ""),
            ('ID', "Material ID", ""),
            ('alpha', "Alpha", ""),
            ('albedo', "Albedo", ""),
            ('roughness', "Roughness", ""),
            ('metalness', "Metalness", "")
        ),
        options={'HIDDEN'}
    )
    
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

        # Load in the newly rendered image TODO might not work with non png formats?
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

    def execute(self, context):
        report_value, report_string = bad_setup_check(self, context, active_export=False)

        if report_value:
            self.report({'ERROR'}, report_string)
            return{'CANCELLED'}
        
        export_and_preview_setup(self, context)

        if context.active_object and context.object.type in ('MESH', 'CURVE', 'FONT', 'SURFACE', 'META', 'LATTICE', 'ARMATURE', 'CAMERA'):
            activeCallback = context.active_object.name
            modeCallback = context.object.mode

            bpy.ops.object.mode_set(mode = 'OBJECT')
            activeSelected = True

        # Scale up BG Plane (helps overscan & border pixels)
        plane_ob = bpy.data.objects["GD_Background Plane"]
        plane_ob.scale[0] = plane_ob.scale[1] = 3

        if self.render_type == "normals":
            normals_setup(self, context)
            self.offline_render(context)
            cleanup_ng_from_mat(self, context, setup_type='GD_Normal')

        elif self.render_type == "curvature":
            curvature_setup(self, context)
            self.offline_render(context)
            curvature_refresh(self, context)

        elif self.render_type == "occlusion":
            occlusion_setup(self, context)
            self.offline_render(context)
            cleanup_ng_from_mat(self, context, setup_type='GD_Ambient Occlusion')
            occlusion_refresh(self, context)

        elif self.render_type == "height":
            height_setup(self, context)
            self.offline_render(context)
            cleanup_ng_from_mat(self, context, setup_type='GD_Height')

        elif self.render_type == "ID":
            id_setup(self, context)
            self.offline_render(context)

        elif self.render_type == "alpha":
            alpha_setup(self, context)
            self.offline_render(context)
            cleanup_ng_from_mat(self, context, setup_type='GD_Alpha')

        elif self.render_type == "albedo":
            alpha_setup(self, context)
            self.offline_render(context)
            cleanup_ng_from_mat(self, context, setup_type='GD_Albedo')

        elif self.render_type == "roughness":
            roughness_setup(self, context)
            self.offline_render(context)
            cleanup_ng_from_mat(self, context, setup_type='GD_Roughness')

        elif self.render_type == "metalness":
            metalness_setup(self, context)
            self.offline_render(context)
            cleanup_ng_from_mat(self, context, setup_type='GD_Metalness')

        # Scale down BG Plane (helps overscan & border pixels)
        plane_ob = bpy.data.objects["GD_Background Plane"]
        plane_ob.scale[0] = plane_ob.scale[1] = 1

        # Refresh all original settings
        export_refresh(self, context)

        # Call for Original Context Mode (Use bpy.ops so that Blenders viewport refreshes)
        if 'activeSelected' in locals():
            context.view_layer.objects.active = bpy.data.objects[activeCallback]
            bpy.ops.object.mode_set(mode = modeCallback)

        self.report({'INFO'}, "Offline render completed!")
        return{'FINISHED'}


################################################################################################################
# MAP PREVIEWER
################################################################################################################


def draw_callback_px(self, context):
    font_id = 0

    # Special clause for Material ID preview
    render_text = self.preview_type.capitalize() if self.preview_type != 'ID' else "Material ID"

    blf.position(font_id, 15, 140, 0)
    blf.size(font_id, 26, 72)
    blf.color(font_id, 1, 1, 1, 1)
    blf.draw(font_id, f"{render_text} Preview  ｜  [ESC] to exit")

    blf.position(font_id, 15, 80, 0)
    blf.size(font_id, 28, 72)
    blf.color(font_id, 1, 1, 0, 1)
    blf.draw(font_id, "You are in Map Preview mode!")


class GRABDOC_OT_leave_map_preview(Operator):
    """Leave the current Map Preview"""
    bl_idname = "grab_doc.leave_modal"
    bl_label = "Leave Map Preview"
    bl_options = {'INTERNAL', 'REGISTER'}

    def execute(self, context):
        context.scene.grabDoc.modalState = False
        return{'FINISHED'}


class GRABDOC_OT_map_preview_warning(OpInfo, Operator):
    """Preview the selected material"""
    bl_idname = "grab_doc.preview_warning"
    bl_label = "    MATERIAL PREVIEW WARNING"
    bl_options = {'INTERNAL'}

    preview_type: EnumProperty(
        items=(
            ('normals', "", ""),
            ('curvature', "", ""),
            ('occlusion', "", ""),
            ('height', "", ""),
            ('ID', "", ""),
            ('alpha', "", ""),
            ('albedo', "", ""),
            ('roughness', "", ""),
            ('metalness', "", "")
        ),
        options={'HIDDEN'}
    )

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

    preview_type: EnumProperty(
        items=(
            ('normals', "", ""),
            ('curvature', "", ""),
            ('occlusion', "", ""),
            ('height', "", ""),
            ('ID', "", ""),
            ('alpha', "", ""),
            ('albedo', "", ""),
            ('roughness', "", ""),
            ('metalness', "", "")
        ),
        options={'HIDDEN'}
    )

    def modal(self, context, event):
        scene = context.scene
        grabDoc = scene.grabDoc
        view_settings = scene.view_settings
        scene_shading = bpy.data.scenes[str(scene.name)].display.shading
        eevee = scene.eevee

        scene.camera = bpy.data.objects["GD_Trim Camera"]

        # Set - Exporter settings
        image_settings = scene.render.image_settings

        image_settings.file_format = grabDoc.imageType

        if grabDoc.imageType == 'OPEN_EXR':
            image_settings.color_depth = grabDoc.colorDepthEXR

        elif grabDoc.imageType != 'TARGA':
            image_settings.color_depth = grabDoc.colorDepthPNG

        if self.preview_type == "normals":
            eevee.taa_render_samples = eevee.taa_samples = grabDoc.samplesNormals
    
        elif self.preview_type == "curvature":
            scene.display.render_aa = scene.display.viewport_aa = grabDoc.samplesCurvature
            view_settings.look = grabDoc.contrastCurvature.replace('_', ' ')

            bpy.data.objects["GD_Background Plane"].color[3] = .9999

            # Refresh specific settings
            if self.done:
                curvature_refresh(self, context)

        elif self.preview_type == "occlusion":
            eevee.taa_render_samples = eevee.taa_samples = grabDoc.samplesOcclusion

            view_settings.look = grabDoc.contrastOcclusion.replace('_', ' ')

            ao_node = bpy.data.node_groups["GD_Ambient Occlusion"].nodes.get('Ambient Occlusion')
            ao_node.inputs[1].default_value = grabDoc.distanceOcclusion

            # Refresh specific settings
            if self.done:
                occlusion_refresh(self, context)

        elif self.preview_type == "height":
            eevee.taa_render_samples = eevee.taa_samples = grabDoc.samplesHeight

            view_settings.look = grabDoc.contrastHeight.replace('_', ' ')

        elif self.preview_type == "ID":
            scene.display.render_aa = scene.display.viewport_aa = grabDoc.samplesMatID

            # Choose the method of ID creation based on user preference
            scene_shading.color_type = grabDoc.methodMatID

        elif self.preview_type == "alpha":
            eevee.taa_render_samples = eevee.taa_samples = grabDoc.samplesAlpha

        elif self.preview_type == "albedo":
            eevee.taa_render_samples = eevee.taa_samples = grabDoc.samplesAlbedo

        elif self.preview_type == "roughness":
            eevee.taa_render_samples = eevee.taa_samples = grabDoc.samplesRoughness

        elif self.preview_type == "metalness":
            eevee.taa_render_samples = eevee.taa_samples = grabDoc.samplesMetalness

        # TODO update the node group input values for Mixed Normal

        # Exiting    
        if self.done:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')

            if self.preview_type == "normals":
                cleanup_ng_from_mat(self, context, setup_type='GD_Normal')
            elif self.preview_type == "occlusion":
                cleanup_ng_from_mat(self, context, setup_type='GD_Ambient Occlusion')
            elif self.preview_type == "height":
                cleanup_ng_from_mat(self, context, setup_type='GD_Height')
            elif self.preview_type == "alpha":
                cleanup_ng_from_mat(self, context, setup_type='GD_Alpha')
            elif self.preview_type == "albedo":
                cleanup_ng_from_mat(self, context, setup_type='GD_Albedo')
            elif self.preview_type == "roughness":
                cleanup_ng_from_mat(self, context, setup_type='GD_Roughness')
            elif self.preview_type == "metalness":
                cleanup_ng_from_mat(self, context, setup_type='GD_Metalness')

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
            if grabDoc.autoExitCamera or not proper_scene_setup(context):
                bpy.ops.grab_doc.view_cam(from_modal=True)
            return {'CANCELLED'}

        # Exit checking
        if not grabDoc.modalState or event.type in {'ESC'} or not proper_scene_setup(context):
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
        elif self.preview_type == 'alpha':
            alpha_setup(self, context)
        elif self.preview_type == 'albedo':
            albedo_setup(self, context)
        elif self.preview_type == 'roughness':
            roughness_setup(self, context)
        elif self.preview_type == 'metalness':
            metalness_setup(self, context)
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
        return context.scene.grabDoc.modalState

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
        render.filepath = bpy.path.abspath(grabDoc.exportPath) + grabDoc.exportName + f"_{grabDoc.modalPreviewType}"

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
            bpy.ops.wm.path_open(filepath = bpy.path.abspath(grabDoc.exportPath))

        # End the timer
        end = time.time()
        timeSpent = end - start

        self.report({'INFO'}, f"Export completed! (execution time: {str((round(timeSpent, 2)))}s)")
        return{'FINISHED'}


################################################################################################################
# REGISTRATION
################################################################################################################


classes = (
    GRABDOC_OT_setup_scene,
    GRABDOC_OT_remove_setup,
    GRABDOC_OT_offline_render,
    GRABDOC_OT_export_maps,
    GRABDOC_OT_map_preview_warning,
    GRABDOC_OT_map_preview,
    GRABDOC_OT_leave_map_preview,
    GRABDOC_OT_export_current_preview
)


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
