import time
import bpy
import os
import bgl
import blf
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty
import traceback
from random import random, randint
from mathutils import Vector, Color
import subprocess
import json


############################################################
# OPERATORS
############################################################


class OpInfo:
    bl_options = {'REGISTER'}


class GRABDOC_OT_open_folder(OpInfo, Operator):
    bl_idname = "grab_doc.open_folder"
    bl_label = "Open Folder"
    bl_description = "Opens up the File Explorer with the designated folder location"

    def execute(self, context):
        if not os.path.exists(context.scene.grab_doc_filepath):
            self.report({'ERROR'}, "There is no file path set")
            return{'FINISHED'}
        else:
            bpy.ops.wm.path_open(filepath = context.scene.grab_doc_filepath)
        return{'FINISHED'}


class GRABDOC_OT_view_cam(OpInfo, Operator):
    bl_idname = "grab_doc.view_cam"
    bl_label = "View Trim Camera"
    bl_description = "View the scenes Trim Camera"

    def execute(self, context):
        try:
            # Set active camera & view it
            context.scene.camera = bpy.data.objects["Trim Camera"]
            bpy.ops.view3d.view_camera()
        except:
            traceback.print_exc()
            self.report({'ERROR'}, "Trim Camera not found, either you haven't set up the scene or you have excluded it from the View Layer.")
        return{'FINISHED'}


class GRABDOC_OT_leave_modal(OpInfo, Operator):
    bl_idname = "grab_doc.leave_modal"
    bl_label = "Leave Map Preview"
    bl_description = "Leave Map Preview mode"

    @classmethod
    def poll(cls, context):
        return(context.scene.grabDocPrefs.modalState)

    def execute(self, context):
        context.scene.grabDocPrefs.modalState = False
        return{'FINISHED'}


def find_tallest_object(self, context):
    tallest_verts = []

    for ob in context.view_layer.objects:
        if ob.name in self.render_list:
            if ob.name != "BG Plane":
                # get the z-coordinates from each vertex and the maximum
                z_coords = [v.co[2] for v in ob.data.vertices]
                index = z_coords.index(max(z_coords))

                vert = ob.data.vertices[index].co
                mat = ob.matrix_world
                loc = mat @ vert

                tallest_verts.append(loc[2])

    if tallest_verts:
        context.scene.grabDocPrefs.heightGuide = max(tallest_verts)


class GRABDOC_OT_send_to_marmo(OpInfo, Operator):
    bl_idname = "grab_doc.bake_marmoset"
    bl_label = "Open / Refresh in Marmoset"
    bl_description = "Export your models, open and bake (if turned on) in Marmoset Toolbag utilizing the settings set within the 'View / Edit Maps' tab"
    
    send_type: EnumProperty(items=(('open',"Open",""),
                                   ('refresh', "Refresh", "")))

    @classmethod
    def poll(cls, context):
        return(os.path.exists(context.scene.marmoset_exe_filepath))

    def execute(self, context):
        grabDocPrefs = context.scene.grabDocPrefs

        if not os.path.exists(context.scene.grab_doc_filepath):
            self.report({'ERROR'}, "There is no file path set")
            return{'FINISHED'}

        if grabDocPrefs.image_type != "PNG":
            self.report({'ERROR'}, "Non PNG formats are currently not supported in Blender GrabDoc for external baking")
            return{'FINISHED'}

        get_rendered_objects(self, context)

        for ob in context.view_layer.objects:
            if ob.name in self.render_list:
                for mod in ob.modifiers:
                    if mod.type == "DISPLACE":
                        if context.scene.grabDocPrefs.manualHeightRange == 'AUTO':
                            self.report({'ERROR'}, "While using Displace modifiers you must use the manual height range option for accuracy (0-1 range affects the clipping plane)")
                            return{'FINISHED'}

        # Add-on root path 
        addon_path = os.path.dirname(__file__)
        
        # Temporary model path 
        temp_models_path = os.path.join(addon_path, "Temp Models")

        # Create the directory 
        if not os.path.exists(temp_models_path):
            os.mkdir(temp_models_path)

        selectedCallback = context.view_layer.objects.selected.keys()

        if context.active_object:
            bpy.ops.object.mode_set(mode = 'OBJECT')

        if grabDocPrefs.exportHeight:
            if grabDocPrefs.manualHeightRange == 'AUTO':
                find_tallest_object(self, context)

        for ob in context.view_layer.objects:
            ob.select_set(False)
            if ob.type == 'MESH':
                if not ob.hide_get():
                    if ob.name in self.render_list:
                        ob.select_set(True)
                        if ob.name == 'BG Plane':
                            obCopy = ob.copy()
                            context.collection.objects.link(obCopy)
                            obCopy.name = "GrabDoc_high BG Plane"

                            ob.name = "GrabDoc_low " + ob.name
                        else:
                            ob.name = "GrabDoc_high " + ob.name

        # Reselect BG Plane high poly
        bpy.data.objects['GrabDoc_high BG Plane'].select_set(True)

        # Parent Directory path 
        addon_path = os.path.join(os.path.dirname(__file__))

        # Path 
        temp_models_path = os.path.join(addon_path, "Temp Models")

        # Export models
        bpy.ops.export_scene.fbx(filepath=temp_models_path + "\\" + grabDocPrefs.exportName + ".fbx",
                                    use_selection=True,
                                    path_mode='ABSOLUTE')

        if "GrabDoc_high BG Plane" in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects["GrabDoc_high BG Plane"], do_unlink=True)

        for ob in context.selected_objects:
            if ob.name == "GrabDoc_low BG Plane":
                ob.name = ob.name.lstrip("GrabDoc_low ")
            else:
                ob.name = ob.name.lstrip("GrabDoc_high ")
            ob.select_set(False)
            

        for o in selectedCallback:
            if not ob.hide_get():
                ob = context.scene.objects.get(o)
                ob.select_set(True)

        # Create a dictionary of variables to transfer into Marmoset
        marmo_vars = {'file_path': f'{context.scene.grab_doc_filepath}{grabDocPrefs.exportName}.{grabDocPrefs.image_type.lower()}',
                      'file_path_no_ext': context.scene.grab_doc_filepath,
                      'marmo_sky_path': f'{os.path.dirname(context.scene.marmoset_exe_filepath)}\\data\\sky\\Evening Clouds.tbsky',
                      'grab_doc_import': f'{temp_models_path}\\{grabDocPrefs.exportName}.fbx',

                      'resolution_x': grabDocPrefs.exportResX,
                      'resolution_y': grabDocPrefs.exportResY,
                      'bits_per_channel': int(grabDocPrefs.bitDepth),
                      'samples': int(grabDocPrefs.samplesMarmoset),

                      'auto_bake': grabDocPrefs.autoBake,
                      'close_after_bake': grabDocPrefs.closeAfterBake,
                      'open_folder': grabDocPrefs.openFolderOnExport,

                      'export_normals': grabDocPrefs.exportNormals,
                      'flipy_normals': grabDocPrefs.normalsFlipY,

                      'export_curvature': grabDocPrefs.exportCurvature,

                      'export_occlusion': grabDocPrefs.exportOcclusion,
                      'ray_count_occlusion': grabDocPrefs.aoRayCount,

                      'export_height': grabDocPrefs.exportHeight,
                      'flat_height': grabDocPrefs.onlyFlatValues,
                      'cage_height': grabDocPrefs.heightGuide * 100 * 2,

                      'export_matid': grabDocPrefs.exportMatID}

        # Flip the slashes of the first Dict value (It's gross but I don't know how to do it any other way without an error in Marmoset)
        for key, value in marmo_vars.items():
            marmo_vars[key] = value.replace("\\", "/")
            break
        
        # Serializing
        marmo_json = json.dumps(marmo_vars, indent = 4)

        # Writing
        with open(addon_path + "\\" + "marmo_vars.json", "w") as outfile:
            outfile.write(marmo_json)
        
        path_ext_only = os.path.basename(os.path.normpath(context.scene.marmoset_exe_filepath)).encode()

        if self.send_type == 'refresh':
            subproc = subprocess.check_output('tasklist', shell=True)
            if not path_ext_only in subproc:
                subprocess.Popen([context.scene.marmoset_exe_filepath, os.path.join(addon_path, "grabdoc_marmo.py")])

                self.report({'INFO'}, "Export completed! Opening Marmoset Toolbag...")
            else:
                if grabDocPrefs.autoBake:
                    self.report({'INFO'}, "Models re-exported! Check Marmoset Toolbag.")
                else:
                    self.report({'INFO'}, "Models re-exported! Check Marmoset Toolbag. (Rebake required)")
        else:
            subprocess.Popen([context.scene.marmoset_exe_filepath, os.path.join(addon_path, "grabdoc_marmo.py")])

            self.report({'INFO'}, "Export completed! Opening Marmoset Toolbag...")
        return{'FINISHED'}


def point_cloud(ob_name, cameraVectorsList, faces = [(0,1,2,3)]):
    grabDocPrefs = bpy.context.scene.grabDocPrefs

    # Make a tuple for the planes vertex positions
    cameraVectorsList = tuple(tuple(vec) for vec in bpy.data.objects["Trim Camera"].data.view_frame(scene = bpy.context.scene))

    if grabDocPrefs.exportHeight and grabDocPrefs.manualHeightRange == 'MANUAL':
        edges = [(0,4), (1,5), (2,6), (3,7), (4,5), (5,6), (6,7), (7,4)]

        # Make a new tuple for the height bounding box
        def change_vector_z(tuple):
            newVectorTuple = (tuple[0], tuple[1], grabDocPrefs.heightGuide - 1)
            return newVectorTuple

        extraVectorsList = tuple([change_vector_z(vec) for vec in cameraVectorsList])

        # Combine both tuples
        cameraVectorsList = cameraVectorsList + extraVectorsList
    else:
        edges = []

    # Create new mesh & object data blocks
    meNew = bpy.data.meshes.new(ob_name)
    obNew = bpy.data.objects.new(ob_name, meNew)

    # Make a mesh from a list of vertices / edges / faces
    meNew.from_pydata(cameraVectorsList, edges, faces)

    # Display name and update the mesh
    meNew.update()
    return obNew


def scene_refresh(self, context):
    grabDocPrefs = context.scene.grabDocPrefs

    savedActiveColl = context.view_layer.active_layer_collection
    selectedCallback = context.view_layer.objects.selected.keys()

    modeCallback = None

    if context.active_object:
        modeCallback = context.object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT')

    # Do some checks to see if the user wants to only render out the objects in a specific collection (for perf reasons)
    objectsColl = "GrabDoc Objects (put objects here)"

    if context.scene.grabDocPrefs.onlyRenderColl:
        for collection in context.view_layer.layer_collection.children:
            if collection.name == objectsColl:
                break
        else:
            bpy.data.collections.new(name = objectsColl)
            context.scene.collection.children.link(bpy.data.collections[objectsColl])
            context.view_layer.active_layer_collection = context.view_layer.layer_collection.children[-1]
    else:
        # Move the objects from GrabDoc Objects to the master collection (rather than outright deleting them)
        for coll in bpy.data.collections:
            if coll.name == objectsColl:
                for ob in coll.all_objects:
                    context.scene.collection.objects.link(ob)
                    bpy.data.collections[objectsColl].objects.unlink(ob)
                break

        # Delete the collection
        for block in bpy.data.collections:
            if block.name == objectsColl:
                bpy.data.collections.remove(block)
                break

    # Make the GrabDoc collection the active one
    for collection in context.view_layer.layer_collection.children:
        if collection.name == "GrabDoc (do not touch)":
            context.view_layer.active_layer_collection = collection

    # If actively viewing a camera, set a variable to remind the script later on
    if [area.spaces.active.region_3d.view_perspective for area in context.screen.areas if area.type == 'VIEW_3D'] == ['CAMERA']:
        repositionCam = True
        bpy.ops.view3d.view_camera()
    else:
        repositionCam = False

    # Remove pre existing camera & related data blocks
    camName = "Trim Camera"
    
    if camName in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[camName], do_unlink=True)

    for block in bpy.data.cameras:
        if not block.users and block.name == camName:
            bpy.data.cameras.remove(block)
            break

    # Add camera & change settings
    bpy.ops.object.camera_add(location = (0, 0, grabDocPrefs.camHeight), rotation = (0, 0, 0))

    if repositionCam:
        bpy.ops.view3d.view_camera() # Needed to do twice or else Blender decides where the user camera is located when we exit

    context.object.name = camName
    context.object.data.name = camName
    context.object.data.type = 'ORTHO'
    context.object.data.display_size = .01
    context.object.data.passepartout_alpha = 0.9
    context.object.data.show_name = True

    # Change the camera scaling based on user preferences
    if grabDocPrefs.scalingType == "scaling_matchRes":
        if grabDocPrefs.exportResX >= grabDocPrefs.exportResY:
            context.object.data.ortho_scale = grabDocPrefs.exportResX / 1000
        else:
            context.object.data.ortho_scale = grabDocPrefs.exportResY / 1000
    else:
        context.object.data.ortho_scale = grabDocPrefs.scalingSet

    # Remove pre existing BG Plane and all related data blocks 
    planeName = "BG Plane"

    hadMaterial = False

    if planeName in bpy.data.objects:
        if bpy.data.objects[planeName].active_material != None:
            savedMat = bpy.data.objects[planeName].active_material
            hadMaterial = True

        bpy.data.objects.remove(bpy.data.objects[planeName], do_unlink=True)

    for block in bpy.data.meshes:
        if not block.users and block.name == planeName:
            bpy.data.meshes.remove(block)
            break

    # Create object & link new object to the active collection
    pc = point_cloud(planeName, [(.0, .0, .0)])
    context.collection.objects.link(pc)

    # Grab the newly made object and shift it to the grid
    plane_ob = bpy.data.objects[planeName]
    plane_ob.location[2] = 1

    if hadMaterial:
        plane_ob.active_material = savedMat

    context.view_layer.objects.active = plane_ob
    plane_ob.select_set(True)
    bpy.ops.object.transform_apply(location=True)
    plane_ob.select_set(False)

    for ob in context.selected_objects:
        ob.select_set(False)

    bpy.ops.object.mode_set(mode = 'EDIT')

    savedSelMode = tuple(context.scene.tool_settings.mesh_select_mode)

    # Change twice incase in face mode already
    context.tool_settings.mesh_select_mode = (False, True, False)
    context.tool_settings.mesh_select_mode = (False, False, True)
    bpy.ops.mesh.flip_normals()
    bpy.ops.uv.unwrap(margin=0.00001)
    plane_ob.rotation_euler[2] = 3.14159

    if grabDocPrefs.creatingGrid:
        plane_ob.show_wire = True
        bpy.ops.mesh.subdivide(number_cuts = grabDocPrefs.creatingGridSubdivs)

    # Refresh selection & context mode
    context.scene.tool_settings.mesh_select_mode = savedSelMode
    bpy.ops.object.mode_set(mode = 'OBJECT')

    # Select original active collection & active object
    if savedActiveColl:
        context.view_layer.active_layer_collection = savedActiveColl

    # Deselect all objects
    for ob in context.selected_objects:
        ob.select_set(False)

    # Select original object(s)
    for o in selectedCallback:
        ob = context.scene.objects.get(o)
        ob.select_set(True)

    if modeCallback:
        bpy.ops.object.mode_set(mode = modeCallback)


class GRABDOC_OT_setup_scene(Operator):
    bl_idname = "grab_doc.setup_scene"
    bl_label = "Setup / Refresh Scene"
    bl_description = "Setup/Refresh your current scene. Useful if you messed up something within the GrabDoc collections that you don't know how to perfectly revert" 
    bl_options = {'UNDO'}

    def execute(self, context):
        grabDocPrefs = context.scene.grabDocPrefs

        selectedCallback = context.view_layer.objects.selected.keys()

        activeSelected = False
        if context.active_object:
            if context.object.type in {'MESH', 'CURVE', 'FONT', 'SURFACE', 'META', 'LATTICE', 'ARMATURE', 'CAMERA'}:
                activeCallback = context.active_object.name
                modeCallback = context.object.mode

                bpy.ops.object.mode_set(mode = 'OBJECT')
                activeSelected = True

        # Set scene resolution
        context.scene.render.resolution_x = grabDocPrefs.exportResX
        context.scene.render.resolution_y = grabDocPrefs.exportResY

        # Create, link & select collection
        savedActiveColl = context.view_layer.active_layer_collection

        for block in bpy.data.collections:
            if block.name == "GrabDoc (do not touch)":
                bpy.data.collections.remove(block)

        bpy.data.collections.new(name = "GrabDoc (do not touch)")

        grabDocCollection = bpy.data.collections["GrabDoc (do not touch)"]

        context.scene.collection.children.link(grabDocCollection)

        context.view_layer.active_layer_collection = context.view_layer.layer_collection.children[-1]

        # Add plane & camera
        scene_refresh(self, context)
        
        # Make the new collection (un)selectable
        grabDocCollection.hide_select = not grabDocPrefs.collSelectable

        # Make the new collection hidden / visible
        grabDocCollection.hide_viewport = grabDocPrefs.collHidden

        # Select original active collection
        context.view_layer.active_layer_collection = savedActiveColl

        # De-select all objects
        for ob in context.selected_objects:
            ob.select_set(False)

        # Re-Select original object(s)
        for o in selectedCallback:
            ob = context.scene.objects.get(o)
            ob.select_set(True)

        # Call for Original Context Mode (Use bpy.ops so that Blenders viewport refreshes)
        if activeSelected:
            context.view_layer.objects.active = bpy.data.objects[activeCallback]
            bpy.ops.object.mode_set(mode = modeCallback)
        return{'FINISHED'}


############################################################
# SETUP & REFRESH
############################################################


def is_in_bounding_vectors(vec_check):
    planeName = bpy.data.objects["BG Plane"]

    vec1 = Vector((planeName.dimensions.x * -1.25, planeName.dimensions.y * -1.25, -100))
    vec2 = Vector((planeName.dimensions.x * 1.25, planeName.dimensions.y * 1.25, 100))

    for i in range(0, 3):
        if (vec_check[i] < vec1[i] and vec_check[i] < vec2[i] or vec_check[i] > vec1[i] and vec_check[i] > vec2[i]):
            return False
    return True


def get_rendered_objects(self, context):
    self.render_list = []
    self.ob_hidden_render_list = []
    self.ob_hidden_vp_list = []

    if context.scene.grabDocPrefs.onlyRenderColl:  
        for coll in bpy.data.collections:
            if coll.name == "GrabDoc Objects (put objects here)" or coll.name == "GrabDoc (do not touch)":
                for ob in coll.all_objects:
                    if not ob.hide_get():
                        if ob.type == 'MESH':
                            self.render_list.append(ob.name)
    else:
        for ob in context.view_layer.objects:
            if not ob.hide_get():
                if ob.type == 'MESH':
                    local_bbox_center = 0.125 * sum((Vector(b) for b in ob.bound_box), Vector())
                    global_bbox_center = ob.matrix_world @ local_bbox_center

                    if(is_in_bounding_vectors(global_bbox_center)):
                        self.render_list.append(ob.name)

        
def export_and_preview_setup(self, context):
    # Look for Trim Camera (only thing required to render)
    for ob in context.view_layer.objects:
        if ob.name == "Trim Camera":
            break
    else:
        self.report({'ERROR'}, "Trim Camera not found, either you haven't set up the scene or you have excluded it from the View Layer.")
        return{'FINISHED'}

    grabDocPrefs = context.scene.grabDocPrefs
    render = context.scene.render
    sceneShading = bpy.data.scenes[str(context.scene.name)].display.shading
    
    get_rendered_objects(self, context)

    # Set - Active camera
    context.scene.camera = bpy.data.objects["Trim Camera"]

    # Save - View layer
    self.currentViewLayer = context.window.view_layer.name

    self.savedViewLayerUse = context.scene.view_layers[self.currentViewLayer].use
    self.savedUseSingleLayer = context.scene.render.use_single_layer

    # Set - View layer
    context.scene.view_layers[self.currentViewLayer].use = True
    context.scene.render.use_single_layer = True

    # Set - Scene resolution
    render.resolution_x = grabDocPrefs.exportResX
    render.resolution_y = grabDocPrefs.exportResY
    render.resolution_percentage = 100

    # Save - Render Engine
    self.savedRenderer = render.engine

    # Save - Render sampling
    self.savedWorkbenchSampling = context.scene.display.render_aa
    self.savedEeveeSampling = context.scene.eevee.taa_render_samples

    # Save - Post Processing
    self.savedUseSequencer = render.use_sequencer
    self.savedUseCompositer = render.use_compositing

    self.savedDitherIntensity = render.dither_intensity

    # Set - Post Processing
    render.use_sequencer = False
    render.use_compositing = False

    render.dither_intensity = 0

    if bpy.app.version >= (2, 82, 0):
        # Save - Performance        
        self.savedHQNormals = render.use_high_quality_normals

        # Set - Performance
        render.use_high_quality_normals = True

    # Save - Scene Shading (Some are context sensitive so will be saved individually when required)
    self.savedLight = sceneShading.light
    self.savedColorType = sceneShading.color_type
    self.savedBackface = sceneShading.show_backface_culling
    self.savedXray = sceneShading.show_xray
    self.savedShadows = sceneShading.show_shadows
    self.savedCavity = sceneShading.show_cavity
    self.savedDOF = sceneShading.use_dof
    self.savedOutline = sceneShading.show_object_outline
    self.savedShowSpec = sceneShading.show_specular_highlight

    # Save - Color Management
    self.savedDisplayDevice = context.scene.display_settings.display_device
    self.savedViewTransform = context.scene.view_settings.view_transform
    self.savedContrastType = context.scene.view_settings.look
    self.savedExposure = context.scene.view_settings.exposure
    self.savedGamma = context.scene.view_settings.gamma

    self.savedColorMode = render.image_settings.color_mode
    self.savedFileFormat = render.image_settings.file_format

    render.image_settings.file_format = grabDocPrefs.image_type

    # Set - Color Management
    context.scene.view_settings.view_transform = 'Standard'
    context.scene.view_settings.look = 'None'
    context.scene.view_settings.exposure = 0
    context.scene.view_settings.gamma = 1

    # Set - General disabling
    sceneShading.use_dof = False
    sceneShading.show_shadows = False
    sceneShading.show_xray = False
    sceneShading.show_backface_culling = False
    sceneShading.show_object_outline = False
    sceneShading.show_specular_highlight = False
    sceneShading.show_cavity = False

    # Save - Ambient Occlusion
    self.savedUseAO = context.scene.eevee.use_gtao
    self.savedAODistance = context.scene.eevee.gtao_distance

    context.scene.eevee.use_gtao = False # Ambient Occlusion

    context.scene.use_nodes = False # Disable scene nodes unless needed (Prevents black render)
    
    # Add non-rendered objects to a list and hide them from the render & viewport
    for ob in context.view_layer.objects:
        if not ob.name in self.render_list and ob.name != "Trim Camera":
            # Hide in render
            if not ob.hide_render:
                self.ob_hidden_render_list.append(ob.name)
            ob.hide_render = True

            # Hide in viewport
            if not ob.hide_viewport:
                self.ob_hidden_vp_list.append(ob.name)
            ob.hide_viewport = True


def export_refresh(self, context):
    render = context.scene.render
    sceneShading = bpy.data.scenes[str(context.scene.name)].display.shading
    viewSettings = context.scene.view_settings

    # Refresh - View layer settings
    context.scene.view_layers[self.currentViewLayer].use = self.savedViewLayerUse
    context.scene.render.use_single_layer = self.savedUseSingleLayer

    # Refresh - Scene Shading 
    sceneShading.show_cavity = self.savedCavity
    sceneShading.color_type = self.savedColorType
    sceneShading.show_backface_culling = self.savedBackface
    sceneShading.show_xray = self.savedXray
    sceneShading.show_shadows = self.savedShadows
    sceneShading.use_dof = self.savedDOF
    sceneShading.show_object_outline = self.savedOutline
    sceneShading.show_specular_highlight = self.savedShowSpec
    sceneShading.light = self.savedLight

    # Refresh - Color Management
    viewSettings.look = self.savedContrastType
    context.scene.display_settings.display_device = self.savedDisplayDevice
    viewSettings.view_transform = self.savedViewTransform
    viewSettings.exposure = self.savedExposure
    viewSettings.gamma = self.savedGamma

    render.image_settings.color_mode = self.savedColorMode
    render.image_settings.file_format = self.savedFileFormat

    # Refresh - Render sampling
    context.scene.display.render_aa = self.savedWorkbenchSampling
    context.scene.eevee.taa_render_samples = self.savedEeveeSampling

    # Refresh - Render Engine
    render.engine = self.savedRenderer

    # Refresh - Post Processing
    render.use_sequencer = self.savedUseSequencer
    render.use_compositing = self.savedUseCompositer

    render.dither_intensity = self.savedDitherIntensity

    if bpy.app.version >= (2, 82, 0):
        # Refresh - Performance        
        render.use_high_quality_normals = self.savedHQNormals

    # Refresh - objects hidden in render
    for ob in context.view_layer.objects:
        # Unhide in render
        if ob.name in self.ob_hidden_render_list:
            ob.hide_render = False
        
        # Unhide in viewport
        if ob.name in self.ob_hidden_vp_list:
            ob.hide_viewport = False


############################################################
# EXPORT & OFFLINE RENDERER
############################################################


def grabdoc_export(self, context):
    grabDocPrefs = context.scene.grabDocPrefs
    render = context.scene.render
    
    # Save - file output path
    savedPath = render.filepath

    # Set - map type suffix
    if self.exporterNormals:
        exportSuffix = "_normal"
        self.exporterNormals = False
    elif self.exporterCurvature:
        exportSuffix = "_curve"
        self.exporterCurvature = False
    elif self.exporterMatID:
        exportSuffix = "_matID"
        self.exporterMatID = False
    elif self.exporterHeight:
        exportSuffix = "_height"
        self.exporterHeight = False
    elif self.exporterAO:
        exportSuffix = "_ao"
        self.exporterAO = False

    # Set - Output path to add-on path + add-on name + the type of map exported (file extensions handled automatically)
    render.filepath = context.scene.grab_doc_filepath + grabDocPrefs.exportName + exportSuffix

    bpy.ops.render.render(write_still = True)

    # Refresh - file output path
    render.filepath = savedPath


def offline_render(self, context):
    bpy.ops.render.render()

    # Call user prefs window
    bpy.ops.screen.userpref_show("INVOKE_DEFAULT")

    # Change area & image type
    area = context.window_manager.windows[-1].screen.areas[0]
    area.type = "IMAGE_EDITOR"
    area.spaces.active.image = bpy.data.images['Render Result']


############################################################
# MATERIAL SETUP & CLEANUP
############################################################


class GRABDOC_OT_quick_mat_setup(Operator):
    bl_idname = "grab_doc.quick_mat_setup"
    bl_label = "ID Material Setup"
    bl_description = "Quickly sets up materials on all related objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.active_object:
            bpy.ops.object.mode_set(mode = 'OBJECT')

        for mat in bpy.data.materials:
            if mat.name.startswith("GrabDoc_ID"):
                bpy.data.materials.remove(mat)

        get_rendered_objects(self, context)

        for ob in context.view_layer.objects:
            if ob.type == 'MESH':
                if ob.name in self.render_list:
                    if ob.name != "BG Plane":
                        context.view_layer.objects.active = ob

                        bpy.ops.object.material_slot_remove_unused()

                        ob.active_material_index = 0

                        self.mat = bpy.data.materials.new("GrabDoc_ID." + str(randint(0, 10000000)))
                        self.mat.diffuse_color = random(), random(), random(), 1

                        ob.active_material = bpy.data.materials[self.mat.name]
        return{'FINISHED'}


class GRABDOC_OT_quick_remove_mats(Operator):
    bl_idname = "grab_doc.quick_remove_mats"
    bl_label = "Remove ID Materials"
    bl_description = "Removes all GrabDoc Mat ID materials from all related objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.active_object:
            bpy.ops.object.mode_set(mode = 'OBJECT')

        for mat in bpy.data.materials:
            if mat.name.startswith("GrabDoc_ID"):
                bpy.data.materials.remove(mat)
        
        for ob in context.view_layer.objects:
            if ob.type == "MESH":
                context.view_layer.objects.active = ob

                bpy.ops.object.material_slot_remove_unused()
        return{'FINISHED'}


def grabdoc_material_apply(self, context):
    # Save the active materials of every selected object to a list
    self.active_material_list = []

    for ob in context.view_layer.objects:
        if ob.type == 'MESH':
            if ob.name in self.render_list:
                context.view_layer.objects.active = ob
                bpy.ops.object.material_slot_remove_unused()

                ob.active_material_index = 0

                if ob.active_material:
                    savedMaterial = ob.active_material.name
                    self.active_material_list.append(savedMaterial)
                else:
                    self.active_material_list.append(None)
                
                ob.active_material = bpy.data.materials[self.mat.name]


def grabdoc_material_cleanup(self, context):
    for material in bpy.data.materials:
        if material.name.startswith("GrabDoc_Temp"):
            # 'Refresh' every selected objects original material using the list we made earlier
            for ob in context.view_layer.objects:
                if ob.type == 'MESH':
                    if ob.name in self.render_list:
                        if self.active_material_list[0] != None:
                            ob.active_material = bpy.data.materials[self.active_material_list[0]]
                        self.active_material_list.pop(0)

            # Cleanup - remove the Trim Height material
            bpy.data.materials.remove(bpy.data.materials[self.mat.name])
            break


############################################################
# NORMALS
############################################################


def normals_setup(self, context):
    grabDocPrefs = context.scene.grabDocPrefs
    render = context.scene.render

    render.engine = 'BLENDER_EEVEE'
    context.scene.eevee.taa_render_samples = grabDocPrefs.samplesNormals
    render.image_settings.color_mode = 'RGB'
    context.scene.display_settings.display_device = 'None'

    # Create a new material & turn on node use
    self.mat = bpy.data.materials.new(name = "GrabDoc_Temp_Normals")
    self.mat.use_nodes = True

    # Remove default node
    self.mat.node_tree.nodes.remove(self.mat.node_tree.nodes.get('Principled BSDF'))

    # Get /  load in nodes
    mat_output_node = self.mat.node_tree.nodes.get('Material Output')

    geo_node = self.mat.node_tree.nodes.new('ShaderNodeNewGeometry')

    vec_transform_node = self.mat.node_tree.nodes.new('ShaderNodeVectorTransform')
    vec_transform_node.vector_type = 'NORMAL'
    vec_transform_node.convert_to = 'CAMERA'

    sep_xyz_node = self.mat.node_tree.nodes.new('ShaderNodeSeparateXYZ')

    math_multiply_x_node = self.mat.node_tree.nodes.new('ShaderNodeMath')
    math_multiply_x_node.operation = 'MULTIPLY' 
    math_multiply_x_node.inputs[1].default_value = .5

    math_multiply_y_node = self.mat.node_tree.nodes.new('ShaderNodeMath')
    math_multiply_y_node.operation = 'MULTIPLY'
    math_multiply_y_node.inputs[1].default_value = .5

    math_multiply_z_node = self.mat.node_tree.nodes.new('ShaderNodeMath')
    math_multiply_z_node.operation = 'MULTIPLY'
    math_multiply_z_node.inputs[1].default_value = -.5

    math_add_x_node = self.mat.node_tree.nodes.new('ShaderNodeMath')
    math_add_x_node.operation = 'ADD'
    math_add_x_node.use_clamp = True
    math_add_x_node.inputs[1].default_value = .5

    math_add_y_node = self.mat.node_tree.nodes.new('ShaderNodeMath')
    math_add_y_node.operation = 'ADD'
    math_add_y_node.use_clamp = True
    math_add_y_node.inputs[1].default_value = .5

    math_add_z_node = self.mat.node_tree.nodes.new('ShaderNodeMath')
    math_add_z_node.operation = 'ADD'
    math_add_z_node.use_clamp = True
    math_add_z_node.inputs[1].default_value = .5

    combine_xyz_node = self.mat.node_tree.nodes.new('ShaderNodeCombineXYZ') 

    sep_rgb_node = self.mat.node_tree.nodes.new('ShaderNodeSeparateRGB')

    self.invert_node = self.mat.node_tree.nodes.new('ShaderNodeInvert')
    self.invert_node.inputs[0].default_value = 1 if grabDocPrefs.normalsFlipY else 0

    combine_rgb_node = self.mat.node_tree.nodes.new('ShaderNodeCombineRGB')

    emission_node = self.mat.node_tree.nodes.new('ShaderNodeEmission')

    # Link materials
    links = self.mat.node_tree.links

    links.new(vec_transform_node.inputs["Vector"], geo_node.outputs["Normal"])

    links.new(sep_xyz_node.inputs["Vector"], vec_transform_node.outputs["Vector"])

    links.new(math_multiply_x_node.inputs["Value"], sep_xyz_node.outputs["X"])
    links.new(math_multiply_y_node.inputs["Value"], sep_xyz_node.outputs["Y"])
    links.new(math_multiply_z_node.inputs["Value"], sep_xyz_node.outputs["Z"])

    links.new(math_add_x_node.inputs["Value"], math_multiply_x_node.outputs["Value"])
    links.new(math_add_y_node.inputs["Value"], math_multiply_y_node.outputs["Value"])
    links.new(math_add_z_node.inputs["Value"], math_multiply_z_node.outputs["Value"])

    links.new(combine_xyz_node.inputs["X"], math_add_x_node.outputs["Value"])
    links.new(combine_xyz_node.inputs["Y"], math_add_y_node.outputs["Value"])
    links.new(combine_xyz_node.inputs["Z"], math_add_z_node.outputs["Value"])

    links.new(sep_rgb_node.inputs["Image"], combine_xyz_node.outputs["Vector"])

    links.new(combine_rgb_node.inputs["R"], sep_rgb_node.outputs["R"])
    links.new(self.invert_node.inputs["Color"], sep_rgb_node.outputs["G"])
    links.new(combine_rgb_node.inputs["G"], self.invert_node.outputs["Color"])
    links.new(combine_rgb_node.inputs["B"], sep_rgb_node.outputs["B"])

    links.new(emission_node.inputs["Color"], combine_rgb_node.outputs["Image"])
    links.new(mat_output_node.inputs["Surface"], emission_node.outputs["Emission"])

def normals_export(self, context):
    grabDocPrefs = context.scene.grabDocPrefs

    # Export / Render
    if self.renderer_type != "None":
        if self.renderer_type == "Normals":
            offline_render(self, context)
    else:
        self.exporterNormals = True
        grabdoc_export(self, context)

        # Reimport the Normal map as a material (if the option is turned on)
        if grabDocPrefs.reimportAsMat:
            for material in bpy.data.materials:
                if material.name == grabDocPrefs.exportName + "_normal":
                    bpy.data.materials.remove(material)
                    break

            mat = bpy.data.materials.new(name=grabDocPrefs.exportName + "_normal")
            mat.use_nodes = True

            bsdf = mat.node_tree.nodes["Principled BSDF"]

            texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
            texImage.image = bpy.data.images.load(context.scene.grab_doc_filepath + grabDocPrefs.exportName + "_normal.png")
            texImage.image.colorspace_settings.name = 'Linear'

            normalMap = mat.node_tree.nodes.new('ShaderNodeNormalMap')

            # Make links
            links = mat.node_tree.links

            links.new(normalMap.inputs['Color'], texImage.outputs['Color'])
            links.new(bsdf.inputs['Normal'], normalMap.outputs['Normal'])


############################################################
# CURVATURE
############################################################


def curvature_setup(self, context):
    grabDocPrefs = context.scene.grabDocPrefs
    render = context.scene.render
    sceneShading = bpy.data.scenes[str(context.scene.name)].display.shading
    viewSettings = context.scene.view_settings

    render.engine = 'BLENDER_WORKBENCH'
    context.scene.display.render_aa = grabDocPrefs.samplesCurvature
    sceneShading.light = 'FLAT'
    sceneShading.color_type =  'SINGLE'
    context.scene.display_settings.display_device = 'sRGB'

    if grabDocPrefs.colorCurvature != Color((.21404114365577698, .21404114365577698, .21404114365577698)):
        render.image_settings.color_mode = 'RGB'
    else:
        render.image_settings.color_mode = 'BW'

    # Save cavity stuff
    self.savedCavityType = sceneShading.cavity_type
    self.savedCavityRidgeFactor = sceneShading.cavity_ridge_factor
    self.savedCurveRidgeFactor = sceneShading.curvature_ridge_factor
    self.savedCavityValleyFactor = sceneShading.cavity_valley_factor
    self.savedCurveValleyFactor = sceneShading.curvature_valley_factor
    self.savedCavity = sceneShading.show_cavity

    self.initialColorList = sceneShading.single_color
    self.savedSingleList = [] # List for single_color because saving the variable on its own isn't enough

    for i in self.initialColorList:
        self.savedSingleList.append(i)
    
    sceneShading.show_cavity = True
    sceneShading.cavity_type = 'BOTH'
    sceneShading.cavity_ridge_factor = grabDocPrefs.WSRidge
    sceneShading.curvature_ridge_factor = grabDocPrefs.SSRidge
    sceneShading.cavity_valley_factor = 0
    sceneShading.curvature_valley_factor = grabDocPrefs.SSValley
    sceneShading.single_color = grabDocPrefs.colorCurvature
    
    viewSettings.look = grabDocPrefs.contrastCurvature.replace('_', ' ')

def curvature_export(self, context):
    if self.renderer_type != "None":
        if self.renderer_type == "Curvature":
            offline_render(self, context)
    else:
        self.exporterCurvature = True
        grabdoc_export(self, context)


############################################################
# AMBIENT OCCLUSION
############################################################


def occlusion_setup(self, context):
    grabDocPrefs = context.scene.grabDocPrefs
    render = context.scene.render
    viewSettings = context.scene.view_settings

    render.engine = 'BLENDER_EEVEE'
    context.scene.eevee.taa_render_samples = grabDocPrefs.samplesOcclusion
    render.image_settings.color_mode = 'BW'
    context.scene.display_settings.display_device = 'None'

    # Save & turn on overscan to help with screenspace effects
    self.savedUseOverscan = context.scene.eevee.use_overscan
    self.savedOverscanSize = context.scene.eevee.overscan_size

    context.scene.eevee.use_overscan = True
    context.scene.eevee.overscan_size = 10

    # Set - Ambient Occlusion
    context.scene.eevee.use_gtao = True
    context.scene.eevee.gtao_distance = 1

    # Create a new material & turn on node use
    self.mat = bpy.data.materials.new(name = "GrabDoc_Temp_AO")
    self.mat.use_nodes = True

    # Remove default node
    self.mat.node_tree.nodes.remove(self.mat.node_tree.nodes.get('Principled BSDF'))

    # Get / create nodes
    material_output_node = self.mat.node_tree.nodes.get('Material Output')

    ao_node = self.mat.node_tree.nodes.new('ShaderNodeAmbientOcclusion')
    ao_node.samples = 32

    gamma_node = self.mat.node_tree.nodes.new('ShaderNodeGamma')
    gamma_node.inputs[1].default_value = grabDocPrefs.gammaOcclusion

    emission_node = self.mat.node_tree.nodes.new('ShaderNodeEmission')

    # Link materials
    links = self.mat.node_tree.links

    links.new(gamma_node.inputs["Color"], ao_node.outputs["Color"])
    links.new(emission_node.inputs["Color"], gamma_node.outputs["Color"])
    links.new(material_output_node.inputs["Surface"], emission_node.outputs["Emission"])

    viewSettings.look = grabDocPrefs.contrastOcclusion.replace('_', ' ')

def occlusion_export(self, context):
    if self.renderer_type != "None":
        if self.renderer_type == "Occlusion":
            offline_render(self, context)
    else:
        self.exporterAO = True
        grabdoc_export(self, context)


############################################################
# HEIGHT
############################################################


def height_setup(self, context):
    grabDocPrefs = context.scene.grabDocPrefs
    render = context.scene.render

    render.engine = 'BLENDER_EEVEE'
    context.scene.eevee.taa_render_samples = grabDocPrefs.samplesHeight
    render.image_settings.color_mode = 'BW'
    context.scene.display_settings.display_device = 'None'

    if grabDocPrefs.manualHeightRange == 'AUTO':
        find_tallest_object(self, context)

    # Create a new material & turn on node use
    self.mat = bpy.data.materials.new(name = "GrabDoc_Temp_Height")
    self.mat.use_nodes = True

    # Remove default node
    self.mat.node_tree.nodes.remove(self.mat.node_tree.nodes.get('Principled BSDF'))

    # Get /  load in nodes
    material_output = self.mat.node_tree.nodes.get('Material Output')

    camera_data = self.mat.node_tree.nodes.new('ShaderNodeCameraData')

    self.map_range_node = self.mat.node_tree.nodes.new('ShaderNodeMapRange')
    if grabDocPrefs.onlyFlatValues:
        self.map_range_node.inputs[1].default_value = grabDocPrefs.camHeight - .001
    else:
        self.map_range_node.inputs[1].default_value = grabDocPrefs.heightGuide * -1 + grabDocPrefs.camHeight
    self.map_range_node.inputs[2].default_value = grabDocPrefs.camHeight

    invert_node = self.mat.node_tree.nodes.new('ShaderNodeInvert')

    emission_node = self.mat.node_tree.nodes.new('ShaderNodeEmission')

    # Link materials
    links = self.mat.node_tree.links

    links.new(self.map_range_node.inputs["Value"], camera_data.outputs["View Z Depth"])
    links.new(invert_node.inputs["Color"], self.map_range_node.outputs["Result"])
    links.new(emission_node.inputs["Color"], invert_node.outputs["Color"])
    links.new(material_output.inputs["Surface"], emission_node.outputs["Emission"])

def height_export(self, context):
    if self.renderer_type != "None":
        if self.renderer_type == "Height":
            offline_render(self, context)
    else:
        self.exporterHeight = True
        grabdoc_export(self, context)


############################################################
# MAT ID
############################################################


def id_setup(self, context):
    grabDocPrefs = context.scene.grabDocPrefs
    render = context.scene.render
    sceneShading = bpy.data.scenes[str(context.scene.name)].display.shading

    render.engine = 'BLENDER_WORKBENCH'
    context.scene.display.render_aa = grabDocPrefs.samplesMatID
    sceneShading.light = 'FLAT'
    render.image_settings.color_mode = 'RGB'
    context.scene.display_settings.display_device = 'sRGB'

    # Choose the method of ID creation based on user preference
    sceneShading.color_type = grabDocPrefs.matID_method

def id_export(self, context):
    if self.renderer_type != "None":
        if self.renderer_type == "ID":
            offline_render(self, context)
    else:
        self.exporterMatID = True
        grabdoc_export(self, context)


############################################################
# EXPORT MAPS
############################################################


class GRABDOC_OT_export_maps(OpInfo, Operator):
    bl_idname = "grab_doc.export_maps"
    bl_label = "Export Maps"
    bl_description = "Export all enabled maps to the designated file path"

    @classmethod
    def poll(cls, context):
        return(not context.scene.grabDocPrefs.modalState)

    renderer_type: EnumProperty(items=(('None',"None",""),
                                       ('Normals', "Normals", ""),
                                       ('Curvature', "Curvature", ""),
                                       ('Occlusion', "Ambient Occlusion", ""),
                                       ('Height', "Height", ""),
                                       ('ID', "Material ID", "")))

    def execute(self, context):
        # Declare propertygroup as a variable
        grabDocPrefs = context.scene.grabDocPrefs
        
        # Setup Scene
        export_and_preview_setup(self, context)

        for ob in context.view_layer.objects:
            if ob.name in self.render_list:
                for mod in ob.modifiers:
                    if mod.type == "DISPLACE":
                        if context.scene.grabDocPrefs.manualHeightRange == 'AUTO':
                            self.report({'ERROR'}, "While using Displace modifiers you must use the manual height range option for accuracy (0-1 range affects the clipping plane)")
                            return{'FINISHED'}

        if self.renderer_type == "None":
            # General checks & variables
            if not os.path.exists(context.scene.grab_doc_filepath):
                self.report({'ERROR'}, "There is no file path set")
                return{'FINISHED'}

            # Start counting execution time
            start = time.time()

        self.exporterNormals = False
        self.exporterCurvature = False
        self.exporterHeight = False
        self.exporterMatID = False
        
        activeSelected = False

        if context.active_object:
            if context.object.type in {'MESH', 'CURVE', 'FONT', 'SURFACE', 'META', 'LATTICE', 'ARMATURE', 'CAMERA'}:
                activeCallback = context.active_object.name
                modeCallback = context.object.mode

                bpy.ops.object.mode_set(mode = 'OBJECT')
                activeSelected = True

        # Scale up BG Plane (helps overscan & border pixels)
        plane_ob = bpy.data.objects["BG Plane"]
        plane_ob.scale[0] = 1.1
        plane_ob.scale[1] = 1.1

        if grabDocPrefs.exportMatID or self.renderer_type == "ID":
           id_setup(self, context)
           id_export(self, context)

        if grabDocPrefs.exportHeight or self.renderer_type == "Height":
            height_setup(self, context)
            grabdoc_material_apply(self, context)
            height_export(self, context)
            grabdoc_material_cleanup(self, context)

        if grabDocPrefs.exportCurvature or self.renderer_type == "Curvature":
            curvature_setup(self, context)
            curvature_export(self, context)

            # Set - Scene
            sceneShading = bpy.data.scenes[str(context.scene.name)].display.shading

            # Refresh specific preferences
            sceneShading.cavity_ridge_factor = self.savedCavityRidgeFactor
            sceneShading.curvature_ridge_factor = self.savedCurveRidgeFactor
            sceneShading.cavity_valley_factor = self.savedCavityValleyFactor
            sceneShading.curvature_valley_factor = self.savedCurveValleyFactor
            sceneShading.single_color = self.savedSingleList
            sceneShading.cavity_type = self.savedCavityType
            sceneShading.show_cavity = self.savedCavity

            context.scene.view_settings.look = self.savedContrastType

        if grabDocPrefs.exportOcclusion or self.renderer_type == "Occlusion":        
            occlusion_setup(self, context)
            grabdoc_material_apply(self, context)
            occlusion_export(self, context)
            grabdoc_material_cleanup(self, context)

            # Refresh specific preferences
            context.scene.eevee.use_overscan = self.savedUseOverscan
            context.scene.eevee.overscan_size = self.savedOverscanSize

            context.scene.eevee.use_gtao = self.savedUseAO
            context.scene.eevee.gtao_distance = self.savedAODistance

        if grabDocPrefs.exportNormals or self.renderer_type == "Normals":
            normals_setup(self, context)
            grabdoc_material_apply(self, context)
            normals_export(self, context)
            grabdoc_material_cleanup(self, context)

        # Scale down BG Plane (helps overscan & border pixels)
        plane_ob = bpy.data.objects["BG Plane"]
        plane_ob.scale[0] = 1
        plane_ob.scale[1] = 1

        # Refresh all original settings
        export_refresh(self, context)

        # Call for Original Context Mode (Use bpy.ops so that Blenders viewport refreshes)
        if activeSelected:
            context.view_layer.objects.active = bpy.data.objects[activeCallback]
            bpy.ops.object.mode_set(mode = modeCallback)

        if self.renderer_type == "None":
            if grabDocPrefs.openFolderOnExport:
                bpy.ops.wm.path_open(filepath = context.scene.grab_doc_filepath)

            # End the timer
            end = time.time()
            timeSpent = end - start

            self.report({'INFO'}, f"Export completed! (execution time: {str((round(timeSpent, 2)))}s)")
        else:
            if self.renderer_type in ('Normals', 'Occlusion', 'Height'):
                self.report({'WARNING'}, "Offline render completed! Result will appear wrong until you set display device to 'None' [Render Properties > Color Management]")
            else:
                self.report({'INFO'}, "Offline render completed!")

        self.renderer_type = "None"
        return{'FINISHED'}


############################################################
# MAP PREVIEWER
############################################################


def draw_callback_px(self, context):
    font_id = 0

    blf.position(font_id, 15, 140, 0)
    blf.size(font_id, 26, 72)
    blf.draw(font_id, f"{self.preview_type} Preview | 'ESC' to leave")

    blf.position(font_id, 15, 100, 0)
    blf.size(font_id, 18, 72)
    blf.draw(font_id, "You are currently in Map Preview mode!")

class GRABDOC_OT_export_current_preview(OpInfo, Operator):
    """Export the currently previewed material"""
    bl_idname = "grab_doc.export_preview"
    bl_label = "Export Previewed Map"

    preview_export_type: EnumProperty(items=(('Normals', "", ""),
                                             ('Curvature', "", ""),
                                             ('Occlusion', "", ""),
                                             ('Height', "", ""),
                                             ('ID', "", "")))

    @classmethod
    def poll(cls, context):
        return(context.scene.grabDocPrefs.modalState)

    def execute(self, context):
        # Look for Trim Camera (only thing required to render)
        for ob in context.view_layer.objects:
            if ob.name == "Trim Camera":
                break
        else:
            self.report({'ERROR'}, "Trim Camera not found, either you haven't set up the scene or you have excluded it from the View Layer.")
            return{'FINISHED'}

        # General checks & variables
        if not os.path.exists(context.scene.grab_doc_filepath):
            self.report({'ERROR'}, "There is no file path set")
            return{'FINISHED'}

        get_rendered_objects(self, context)

        for ob in context.view_layer.objects:
            if ob.name in self.render_list:
                for mod in ob.modifiers:
                    if mod.type == "DISPLACE":
                        if context.scene.grabDocPrefs.manualHeightRange == 'AUTO':
                            self.report({'ERROR'}, "While using Displace modifiers you must use the manual height range option for accuracy (0-1 range affects the clipping plane)")
                            return{'FINISHED'}

        # Start counting execution time
        start = time.time()

        # Save - file output path
        render = context.scene.render

        savedPath = render.filepath

        # Set - map type suffix
        if self.preview_export_type == 'Normals':
            exportSuffix = "_normal"
        elif self.preview_export_type == 'Curvature':
            exportSuffix = "_curve"
        elif self.preview_export_type == 'Occlusion':
            exportSuffix = "_ao"
        elif self.preview_export_type == 'Height':
            exportSuffix = "_height"
        else: # ID
            exportSuffix = "_matID"

        grabDocPrefs = context.scene.grabDocPrefs

        # Set - Output path to add-on path + add-on name + the type of map exported (file extensions handled automatically)
        render.filepath = context.scene.grab_doc_filepath + grabDocPrefs.exportName + exportSuffix

        bpy.ops.render.render(write_still = True)

        # Refresh - file output path
        render.filepath = savedPath

        if self.preview_export_type == 'Normals':
            # Reimport the Normal map as a material (if the option is turned on)
            if grabDocPrefs.reimportAsMat:
                for material in bpy.data.materials:
                    if material.name == grabDocPrefs.exportName + "_normal":
                        bpy.data.materials.remove(material)
                        break

                mat = bpy.data.materials.new(name=grabDocPrefs.exportName + "_normal")
                mat.use_nodes = True

                bsdf = mat.node_tree.nodes["Principled BSDF"]

                texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
                texImage.image = bpy.data.images.load(context.scene.grab_doc_filepath + grabDocPrefs.exportName + "_normal.png")
                texImage.image.colorspace_settings.name = 'Linear'

                normalMap = mat.node_tree.nodes.new('ShaderNodeNormalMap')

                # Make links
                links = mat.node_tree.links

                links.new(normalMap.inputs['Color'], texImage.outputs['Color'])
                links.new(bsdf.inputs['Normal'], normalMap.outputs['Normal'])
           
        if grabDocPrefs.openFolderOnExport:
            bpy.ops.wm.path_open(filepath = context.scene.grab_doc_filepath)

        # End the timer
        end = time.time()
        timeSpent = end - start

        self.report({'INFO'}, f"Export completed! (execution time: {str((round(timeSpent, 2)))}s)")
        return{'FINISHED'}


class GRABDOC_OT_preview_map(OpInfo, Operator):
    """Preview the selected material"""
    bl_idname = "grab_doc.preview_map"
    bl_label = ""

    preview_type: EnumProperty(items=(('Normals', "", ""),
                                      ('Curvature', "", ""),
                                      ('Occlusion', "", ""),
                                      ('Height', "", ""),
                                      ('ID', "", ""))) 

    def modal(self, context, event):
        grabDocPrefs = context.scene.grabDocPrefs
        viewSettings = context.scene.view_settings
        sceneShading = bpy.data.scenes[str(context.scene.name)].display.shading
        
        try:
            if self.preview_type == "Curvature":
                if not self.emergency_exit:
                    context.scene.display.render_aa = grabDocPrefs.samplesCurvature

                    if grabDocPrefs.colorCurvature != Color((.21404114365577698, .21404114365577698, .21404114365577698)):
                        context.scene.render.image_settings.color_mode = 'RGB'
                    else:
                        context.scene.render.image_settings.color_mode = 'BW'

                    viewSettings.look = grabDocPrefs.contrastCurvature.replace('_', ' ')

                if self.done:
                    sceneShading.cavity_ridge_factor = self.savedCavityRidgeFactor
                    sceneShading.curvature_ridge_factor = self.savedCurveRidgeFactor
                    sceneShading.cavity_valley_factor = self.savedCavityValleyFactor
                    sceneShading.curvature_valley_factor = self.savedCurveValleyFactor
                    sceneShading.single_color = self.savedSingleList
                    sceneShading.cavity_type = self.savedCavityType
                    sceneShading.show_cavity = self.savedCavity

                    sceneShading.cavity_ridge_factor = self.savedCavityRidgeFactor
                    sceneShading.curvature_ridge_factor = self.savedCurveRidgeFactor
                    sceneShading.cavity_valley_factor = self.savedCavityValleyFactor
                    sceneShading.curvature_valley_factor = self.savedCurveValleyFactor
                    sceneShading.single_color = self.savedSingleList
                    sceneShading.cavity_type = self.savedCavityType
                    sceneShading.show_cavity = self.savedCavity

            elif self.preview_type == "Occlusion":
                if not self.emergency_exit:
                    context.scene.eevee.taa_render_samples = grabDocPrefs.samplesOcclusion

                    context.scene.eevee.gtao_distance = grabDocPrefs.distanceOcclusion

                    viewSettings.look = grabDocPrefs.contrastOcclusion.replace('_', ' ')

                if self.done:
                    context.scene.eevee.use_gtao = self.savedUseAO
                    context.scene.eevee.gtao_distance = self.savedAODistance

            elif not self.emergency_exit:
                if self.preview_type == "Normals":
                    context.scene.eevee.taa_render_samples = grabDocPrefs.samplesNormals

                    self.invert_node.inputs[0].default_value = 1 if grabDocPrefs.normalsFlipY else 0

                elif self.preview_type == "Height":
                    context.scene.eevee.taa_render_samples = grabDocPrefs.samplesHeight

                    context.scene.render.image_settings.file_format = grabDocPrefs.image_type

                elif self.preview_type == "ID":
                    context.scene.display.render_aa = grabDocPrefs.samplesMatID

                    # Choose the method of ID creation based on user preference
                    sceneShading.color_type = grabDocPrefs.matID_method

            # Check if user wants the grid preview to be on
            if grabDocPrefs.creatingGrid:
                plane_ob = bpy.data.objects["BG Plane"]
                plane_ob.show_wire = grabDocPrefs.wirePreview

            # Exiting    
            if self.done:
                # Refresh - Camera view
                for area in context.screen.areas:
                    if area.type == 'VIEW_3D':
                        for space in area.spaces:
                            space.shading.type = 'SOLID'
                            if [area.spaces.active.region_3d.view_perspective for area in context.screen.areas if area.type == 'VIEW_3D'] == ['CAMERA']:
                                try:
                                    context.scene.camera = bpy.data.objects["Trim Camera"]
                                    bpy.ops.view3d.view_camera()
                                except:
                                    traceback.print_exc() # I have no idea why an error occurs here seemingly randomly.
                                    pass
                            break
                    
                grabdoc_material_cleanup(self, context)

                export_refresh(self, context)

                # Refresh - Grid view
                if grabDocPrefs.creatingGrid:
                    plane_ob.show_wire = True

                # Refresh - Modal checks
                grabDocPrefs.preview_type = 'None'

                if context.preferences.addons[__package__].preferences.drawMatPreviewUI_Pref:
                    bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')

                if self.emergency_exit == 1:
                    self.report({'ERROR'}, "Map preview has safely exited after encountering an error. Please send the latest error code in the system console to the add-on devs.")
                return {'CANCELLED'}

            # Exit checking                     
            if not grabDocPrefs.modalState or event.type in {'ESC'}:
                self.done = True
                return {'PASS_THROUGH'}
        except:
            traceback.print_exc()
            self.done = True

            # This is a failsafe for if the modal operator breaks. The first time it breaks, the modal attempts to safely exit. 
            # Once it errors out 2 times it force exits without resetting the proper value and warns the user to reset the session.
            self.emergency_exit += 1
            if self.emergency_exit == 2:
                self.report({'ERROR'}, "Critical error, please restart your session without saving.")
            return {'PASS_THROUGH'}
        return {'PASS_THROUGH'}
        
    def invoke(self, context, event):
        grabDocPrefs = context.scene.grabDocPrefs

        if grabDocPrefs.onlyRenderColl:  
            for coll in bpy.data.collections:
                if coll.name == "GrabDoc Objects (put objects here)":
                    if len(coll.all_objects) == 0:
                        self.report({'ERROR'}, "You have 'Manually pick rendered' turned on, but no objects are in that collection")
                        return{'FINISHED'}

        self.done = False
        self.emergency_exit = 0

        export_and_preview_setup(self, context)

        if [area.spaces.active.region_3d.view_perspective for area in context.screen.areas if area.type == 'VIEW_3D'] != ['CAMERA']:
            bpy.ops.view3d.view_camera()

        if context.active_object:
            bpy.ops.object.mode_set(mode = 'OBJECT')

        if self.preview_type == 'Normals':
            normals_setup(self, context)
            grabdoc_material_apply(self, context)

        elif self.preview_type == 'Curvature':
            curvature_setup(self, context)

        elif self.preview_type == 'Occlusion':
            occlusion_setup(self, context)
            grabdoc_material_apply(self, context)

        elif self.preview_type == 'Height':
            height_setup(self, context)
            grabdoc_material_apply(self, context)

        elif self.preview_type == 'ID':
            id_setup(self, context)

        # Set - Rendered view
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    space.shading.type = 'RENDERED'
                    break

        grabDocPrefs.preview_type = self.preview_type
        grabDocPrefs.modalState = True

        if context.preferences.addons[__package__].preferences.drawMatPreviewUI_Pref:
            # Draw text handler
            args = (self, context)
            self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')

        # Modal handler
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

active_modals = set()

def callback(modal):
    def modal_wrapper(self, context, event):
        GRABDOC_OT_preview_map = type(self)
        _ret, = ret = modal(self, context, event)
        if _ret in {'RUNNING_MODAL', 'PASS_THROUGH'}:
            active_modals.add(GRABDOC_OT_preview_map)
        elif _ret in {'FINISHED', 'CANCELLED'}:
            active_modals.discard(GRABDOC_OT_preview_map)
            context.scene.grabDocPrefs.modalState = False
        return ret
    return modal_wrapper

for GRABDOC_OT_preview_map in bpy.types.Operator.__subclasses__():
    if hasattr(GRABDOC_OT_preview_map, "modal"):
        GRABDOC_OT_preview_map.modal = callback(GRABDOC_OT_preview_map.modal)


############################################################
# REGISTRATION
############################################################


classes = (GRABDOC_OT_open_folder,
           GRABDOC_OT_view_cam,
           GRABDOC_OT_leave_modal,
           GRABDOC_OT_setup_scene,
           GRABDOC_OT_quick_mat_setup,
           GRABDOC_OT_quick_remove_mats,
           GRABDOC_OT_export_maps,
           GRABDOC_OT_preview_map,
           GRABDOC_OT_export_current_preview,
           GRABDOC_OT_send_to_marmo)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.directory = StringProperty(subtype = 'DIR_PATH')

    bpy.types.Scene.grab_doc_filepath = bpy.props.StringProperty \
        (name = "",
         default = " ",
         description = "",
         subtype = 'DIR_PATH')

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