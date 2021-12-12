
import bpy, time, os, blf
from bpy.types import Operator
from bpy.props import EnumProperty
from .generic_utils import OpInfo, proper_scene_setup, bad_setup_check, export_bg_plane, get_format_extension
from .node_group_utils import cleanup_ng_from_mat
from .scene_setup_utils import scene_setup, remove_setup
from .baker_setup_cleanup_utils import *


################################################################################################################
# SCENE SETUP & CLEANUP
################################################################################################################


class GRABDOC_OT_setup_scene(OpInfo, Operator):
    """Setup / Refresh your current scene. Useful if you messed up something within the GrabDoc collections that you don't know how to properly revert"""
    bl_idname = "grab_doc.setup_scene"
    bl_label = "Setup / Refresh GrabDoc Scene"

    def execute(self, context):
        scene_setup(self, context)
        return{'FINISHED'}


class GRABDOC_OT_remove_setup(OpInfo, Operator):
    """Completely removes every element of GrabDoc from the scene, not including images reimported after bakes"""
    bl_idname = "grab_doc.remove_setup"
    bl_label = "Remove Setup"

    def execute(self, context):
        remove_setup(context)
        return{'FINISHED'}


################################################################################################################
# MAP EXPORTER
################################################################################################################


class GRABDOC_OT_export_maps(OpInfo, Operator):
    """Export all enabled bake maps"""
    bl_idname = "grab_doc.export_maps"
    bl_label = "Export Maps"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return not context.scene.grabDoc.modalState

    def grabdoc_export(self, context, export_suffix: str) -> None:
        grabDoc = context.scene.grabDoc
        render = context.scene.render
        
        # Save - file output path
        saved_path = render.filepath

        # Set - Output path to add-on path + add-on name + the type of map exported (file extensions handled automatically)
        render.filepath = bpy.path.abspath(grabDoc.exportPath) + grabDoc.exportName + '_' + export_suffix

        context.scene.camera = bpy.data.objects["GD_Trim Camera"]

        bpy.ops.render.render(write_still = True)

        # Refresh - file output path
        render.filepath = saved_path

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
        operation_counter = 1

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

        active_selected = False
        if context.object:
            activeCallback = context.object.name
            modeCallback = context.object.mode

            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode = 'OBJECT')

            active_selected = True

        # Scale up BG Plane (helps overscan & border pixels)
        plane_ob = bpy.data.objects["GD_Background Plane"]
        plane_ob.scale[0] = plane_ob.scale[1] = 3

        percent_till_completed += percentage_division
        context.window_manager.progress_update(percent_till_completed)

        if grabDoc.uiVisibilityNormals and grabDoc.exportNormals:
            normals_setup(self, context)
            self.grabdoc_export(context, export_suffix=grabDoc.suffixNormals)

            if grabDoc.reimportAsMatNormals:
                reimport_as_material(grabDoc.suffixNormals)

            cleanup_ng_from_mat('GD_Normal')

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if grabDoc.uiVisibilityCurvature and grabDoc.exportCurvature:
            curvature_setup(self, context)
            self.grabdoc_export(context, export_suffix=grabDoc.suffixCurvature)
            curvature_refresh(self, context)

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if grabDoc.uiVisibilityOcclusion and grabDoc.exportOcclusion:
            occlusion_setup(self, context)
            self.grabdoc_export(context, export_suffix=grabDoc.suffixOcclusion)

            if grabDoc.reimportAsMatOcclusion:
                reimport_as_material(grabDoc.suffixOcclusion)

            cleanup_ng_from_mat('GD_Ambient Occlusion')
            occlusion_refresh(self, context)

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if grabDoc.uiVisibilityHeight and grabDoc.exportHeight:
            height_setup(self, context)
            self.grabdoc_export(context, export_suffix=grabDoc.suffixHeight)
            cleanup_ng_from_mat('GD_Height')

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if grabDoc.uiVisibilityAlpha and grabDoc.exportAlpha:
            alpha_setup(self, context)
            self.grabdoc_export(context, export_suffix=grabDoc.suffixAlpha)
            cleanup_ng_from_mat('GD_Alpha')

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if grabDoc.uiVisibilityMatID and grabDoc.exportMatID:
            id_setup(self, context)
            self.grabdoc_export(context, export_suffix=grabDoc.suffixID)

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if grabDoc.uiVisibilityAlbedo and grabDoc.exportAlbedo:
            albedo_setup(self, context)
            self.grabdoc_export(context, export_suffix=grabDoc.suffixAlbedo)
            cleanup_ng_from_mat('GD_Albedo')

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if grabDoc.uiVisibilityRoughness and grabDoc.exportRoughness:
            roughness_setup(self, context)
            self.grabdoc_export(context, export_suffix=grabDoc.suffixRoughness)
            cleanup_ng_from_mat('GD_Roughness')

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if grabDoc.uiVisibilityMetalness and grabDoc.exportMetalness:
            metalness_setup(self, context)
            self.grabdoc_export(context, export_suffix=grabDoc.suffixMetalness)
            cleanup_ng_from_mat('GD_Metalness')

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        # Refresh all original settings
        export_refresh(self, context)

        plane_ob = bpy.data.objects["GD_Background Plane"]
        plane_ob.scale[0] = plane_ob.scale[1] = 1

        if grabDoc.exportPlane:
            export_bg_plane(context)

        if grabDoc.openFolderOnExport:
            bpy.ops.wm.path_open(filepath = bpy.path.abspath(grabDoc.exportPath))

        # Call for Original Context Mode (Use bpy.ops so that Blenders viewport refreshes)
        if active_selected:
            context.view_layer.objects.active = bpy.data.objects[activeCallback]

            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode = modeCallback)

        # End the timer
        end = time.time()
        execution_time = end - start

        self.report({'INFO'}, f"Export completed! (execution time: {str((round(execution_time, 2)))}s)")

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
        
    # TODO - might be able to have this uniquely utilize compositing for mixing maps?
    #      - support Reimport as Materials
    #      - Support correct default colorspaces

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

        # Save & Set - file output path
        saved_path = render.filepath

        image_name = 'GD_Render Result'

        render.filepath = os.path.join(temp_folder_path, image_name + get_format_extension())

        # Delete original image
        if image_name in bpy.data.images:
            bpy.data.images.remove(bpy.data.images[image_name])

        bpy.ops.render.render(write_still = True)

        # Load in the newly rendered image
        new_image = bpy.data.images.load(render.filepath)
        new_image.name = image_name

        # Refresh - file output path
        render.filepath = saved_path

        # Call user prefs window
        bpy.ops.screen.userpref_show("INVOKE_DEFAULT")

        # Change area & image type
        area = context.window_manager.windows[-1].screen.areas[0]
        area.type = "IMAGE_EDITOR"
        area.spaces.active.image = new_image

    def execute(self, context):
        report_value, report_string = bad_setup_check(self, context, active_export=False)

        if report_value:
            self.report({'ERROR'}, report_string)
            return{'CANCELLED'}

        # Start execution timer
        start = time.time()
        
        export_and_preview_setup(self, context)

        active_selected = False
        if context.object:
            activeCallback = context.object.name
            modeCallback = context.object.mode

            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode = 'OBJECT')

            active_selected = True

        # Scale up BG Plane (helps overscan & border pixels)
        plane_ob = bpy.data.objects["GD_Background Plane"]
        plane_ob.scale[0] = plane_ob.scale[1] = 3

        if self.render_type == "normals":
            normals_setup(self, context)
            self.offline_render(context)
            cleanup_ng_from_mat('GD_Normal')

        elif self.render_type == "curvature":
            curvature_setup(self, context)
            self.offline_render(context)
            curvature_refresh(self, context)

        elif self.render_type == "occlusion":
            occlusion_setup(self, context)
            self.offline_render(context)
            cleanup_ng_from_mat('GD_Ambient Occlusion')
            occlusion_refresh(self, context)

        elif self.render_type == "height":
            height_setup(self, context)
            self.offline_render(context)
            cleanup_ng_from_mat('GD_Height')

        elif self.render_type == "ID":
            id_setup(self, context)
            self.offline_render(context)

        elif self.render_type == "alpha":
            alpha_setup(self, context)
            self.offline_render(context)
            cleanup_ng_from_mat('GD_Alpha')

        elif self.render_type == "albedo":
            albedo_setup(self, context)
            self.offline_render(context)
            cleanup_ng_from_mat('GD_Albedo')

        elif self.render_type == "roughness":
            roughness_setup(self, context)
            self.offline_render(context)
            cleanup_ng_from_mat('GD_Roughness')

        elif self.render_type == "metalness":
            metalness_setup(self, context)
            self.offline_render(context)
            cleanup_ng_from_mat('GD_Metalness')

        # Refresh all original settings
        export_refresh(self, context)

        # Scale down BG Plane (helps overscan & border pixels)
        plane_ob = bpy.data.objects["GD_Background Plane"]
        plane_ob.scale[0] = plane_ob.scale[1] = 1

        # Call for Original Context Mode (Use bpy.ops so that Blenders viewport refreshes)
        if active_selected:
            context.view_layer.objects.active = bpy.data.objects[activeCallback]

            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode = modeCallback)

        # End the timer
        end = time.time()
        execution_time = end - start

        self.report({'INFO'}, f"Offline render completed! (execution time: {str((round(execution_time, 2)))}s)")
        return{'FINISHED'}


################################################################################################################
# MAP PREVIEWER
################################################################################################################


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


def draw_callback_px(self, context) -> None: # This needs to be outside of the class because of how draw_handler_add handles args
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
        
        if not grabDoc.collRendered: # If background plane not visible in render, create alpha channel
            scene.render.film_transparent = True

            image_settings.color_mode = 'RGBA'
        else:
            scene.render.film_transparent = False

            image_settings.color_mode = 'RGB'

        image_settings.file_format = grabDoc.imageType

        if grabDoc.imageType == 'OPEN_EXR':
            image_settings.color_depth = grabDoc.colorDepthEXR

        elif grabDoc.imageType != 'TARGA':
            image_settings.color_depth = grabDoc.colorDepth

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
                cleanup_ng_from_mat('GD_Normal')
            elif self.preview_type == "occlusion":
                cleanup_ng_from_mat('GD_Ambient Occlusion')
            elif self.preview_type == "height":
                cleanup_ng_from_mat('GD_Height')
            elif self.preview_type == "alpha":
                cleanup_ng_from_mat('GD_Alpha')
            elif self.preview_type == "albedo":
                cleanup_ng_from_mat('GD_Albedo')
            elif self.preview_type == "roughness":
                cleanup_ng_from_mat('GD_Roughness')
            elif self.preview_type == "metalness":
                cleanup_ng_from_mat('GD_Metalness')

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
            if grabDoc.autoExitCamera or not proper_scene_setup():
                bpy.ops.grab_doc.view_cam(from_modal=True)
            return {'CANCELLED'}

        # Exit checking
        if not grabDoc.modalState or event.type in {'ESC'} or not proper_scene_setup():
            bpy.ops.grab_doc.leave_modal()
            self.done = True
        return {'PASS_THROUGH'}

    def execute(self, context):
        grabDoc = context.scene.grabDoc

        report_value, report_string = bad_setup_check(self, context, active_export=False)

        if report_value:
            self.report({'ERROR'}, report_string)
            return{'CANCELLED'}

        self.done = False
        grabDoc.modalState = True

        if bpy.ops.object.mode_set.poll():
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
        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, (self, context), 'WINDOW', 'POST_PIXEL')

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

        report_value, report_string = bad_setup_check(self, context, active_export=True)

        if report_value:
            self.report({'ERROR'}, report_string)
            return{'CANCELLED'}

        # Start counting execution time
        start = time.time()

        # Save - file output path
        render = context.scene.render
        saved_path = render.filepath

        if grabDoc.modalPreviewType == 'normals':
            export_suffix = grabDoc.suffixNormals
        elif grabDoc.modalPreviewType == 'curvature':
            export_suffix = grabDoc.suffixCurvature
        elif grabDoc.modalPreviewType == 'occlusion':
            export_suffix = grabDoc.suffixOcclusion
        elif grabDoc.modalPreviewType == 'height':
            export_suffix = grabDoc.suffixHeight
        elif grabDoc.modalPreviewType == 'ID':
            export_suffix = grabDoc.suffixID
        elif grabDoc.modalPreviewType == 'alpha':
            export_suffix = grabDoc.suffixAlpha
        elif grabDoc.modalPreviewType == 'albedo':
            export_suffix = grabDoc.suffixAlbedo
        elif grabDoc.modalPreviewType == 'roughness':
            export_suffix = grabDoc.suffixRoughness
        elif grabDoc.modalPreviewType == 'metalness':
            export_suffix = grabDoc.suffixMetalness

        # Set - Output path to add-on path + add-on name + the type of map exported (file extensions get handled automatically)
        render.filepath = bpy.path.abspath(grabDoc.exportPath) + grabDoc.exportName + f"_{export_suffix}"

        # Set - Scale up the plane
        plane_ob = bpy.data.objects["GD_Background Plane"]
        plane_ob.scale[0] = plane_ob.scale[1] = 3

        bpy.ops.render.render(write_still = True)

        # Refresh - file output path
        render.filepath = saved_path

        # Reimport the Normal map as a material if requested
        if grabDoc.modalPreviewType == 'normals' and grabDoc.reimportAsMatNormals:
            reimport_as_material(grabDoc.suffixNormals)

        # Reimport the Occlusion map as a material if requested
        elif grabDoc.modalPreviewType == 'occlusion' and grabDoc.reimportAsMatOcclusion:
            reimport_as_material(grabDoc.suffixOcclusion)

        # Refresh - Scale down the plane
        plane_ob = bpy.data.objects["GD_Background Plane"]
        plane_ob.scale[0] = plane_ob.scale[1] = 1

        if grabDoc.exportPlane:
            export_bg_plane(context)
        
        # Open export path location if requested
        if grabDoc.openFolderOnExport:
            bpy.ops.wm.path_open(filepath = bpy.path.abspath(grabDoc.exportPath))

        # End the timer
        end = time.time()
        execution_time = end - start

        self.report({'INFO'}, f"Export completed! (execution time: {str((round(execution_time, 2)))}s)")
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
