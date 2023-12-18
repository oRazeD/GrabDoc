import os
import time

import bpy
import blf
from bpy.types import SpaceView3D, Event, Context, Operator, UILayout
from bpy.props import EnumProperty

from ..utils.node import cleanup_ng_from_mat
from ..utils.scene import scene_setup, remove_setup
from ..utils.baker import (
    export_and_preview_setup,
    normals_setup,
    curvature_setup,
    curvature_refresh,
    occlusion_setup,
    occlusion_refresh,
    height_setup,
    alpha_setup,
    id_setup,
    albedo_setup,
    roughness_setup,
    metalness_setup,
    reimport_as_material,
    export_refresh
)

from ..constants import GlobalVariableConstants as Global
from ..constants import ErrorCodeConstants as Error
from ..utils.generic import (
    proper_scene_setup,
    bad_setup_check,
    export_bg_plane,
    get_format_extension,
    is_camera_in_3d_view,
    get_create_addon_temp_dir,
    poll_message_error
)


class OpInfo:
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = ""


################################################
# MISC
################################################


class GRABDOC_OT_load_ref(OpInfo, Operator):
    """Import a reference onto the background plane"""
    bl_idname = "grab_doc.load_ref"
    bl_label = "Load Reference"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context: Context):
        # Load a new image into the main database
        bpy.data.images.load(self.filepath, check_existing=True)

        context.scene.grabDoc.refSelection = \
            bpy.data.images[os.path.basename(os.path.normpath(self.filepath))]
        return {'FINISHED'}

    def invoke(self, context: Context, _event: Event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class GRABDOC_OT_open_folder(OpInfo, Operator):
    """Opens up the File Explorer to the designated folder location"""
    bl_idname = "grab_doc.open_folder"
    bl_label = "Open Folder"

    def execute(self, context: Context):
        try:
            bpy.ops.wm.path_open(
                filepath=bpy.path.abspath(context.scene.grabDoc.exportPath)
            )
        except RuntimeError:
            self.report({'ERROR'}, Error.NO_VALID_PATH_SET)
            return {'CANCELLED'}
        return {'FINISHED'}


class GRABDOC_OT_view_cam(OpInfo, Operator):
    """View the GrabDoc camera"""
    bl_idname = "grab_doc.view_cam"

    from_modal: bpy.props.BoolProperty(default=False, options={'HIDDEN'})

    def execute(self, context: Context):
        context.scene.camera = bpy.data.objects[Global.TRIM_CAMERA_NAME]

        # TODO: I don't know what the intention was here
        if self.from_modal and is_camera_in_3d_view():
            bpy.ops.view3d.view_camera()
        else:
            bpy.ops.view3d.view_camera()

        self.from_modal = False
        return {'FINISHED'}


################################################
# SCENE SETUP & CLEANUP
################################################


class GRABDOC_OT_setup_scene(OpInfo, Operator):
    """Setup / Refresh your current scene. Useful if you messed
up something within the GrabDoc collections that you don't
know how to properly revert"""
    bl_idname = "grab_doc.setup_scene"
    bl_label = "Setup / Refresh GrabDoc Scene"

    def execute(self, context: Context):
        scene_setup(self, context)
        return {'FINISHED'}


class GRABDOC_OT_remove_setup(OpInfo, Operator):
    """Completely removes every element of GrabDoc from the
scene, not including images reimported after bakes"""
    bl_idname = "grab_doc.remove_setup"
    bl_label = "Remove Setup"

    def execute(self, context: Context):
        remove_setup(context)
        return {'FINISHED'}


################################################
# MAP EXPORTER
################################################


class GRABDOC_OT_export_maps(OpInfo, Operator, UILayout):
    """Export all enabled bake maps"""
    bl_idname = "grab_doc.export_maps"
    bl_label = "Export Maps"
    bl_options = {'INTERNAL'}

    progress_factor = 0.0

    @classmethod
    def poll(cls, context: Context) -> bool:
        return not context.scene.grabDoc.modalState

    def grabdoc_export(self, context: Context, export_suffix: str) -> None:
        gd = context.scene.grabDoc
        render = context.scene.render

        # Save - file output path
        saved_path = render.filepath

        # Set - Output path to add-on path + add-on name + the
        # type of map exported (file extensions handled automatically)
        render.filepath = \
            bpy.path.abspath(gd.exportPath) + gd.exportName + '_' + export_suffix

        context.scene.camera = bpy.data.objects[Global.TRIM_CAMERA_NAME]

        bpy.ops.render.render(write_still=True)

        # Refresh - file output path
        render.filepath = saved_path

    def draw(self, context: Context):
        layout = self.layout
        print("Layout:", layout)

    def execute(self, context: Context):
        gd = context.scene.grabDoc

        #print(self.map_types)
        self.map_types = 'export'
        print(self.map_types)

        report_value, report_string = bad_setup_check(self, context, active_export=True)
        if report_value:
            self.report({'ERROR'}, report_string)
            return {'CANCELLED'}

        # Start execution timer & UI progress bar
        start = time.time()
        context.window_manager.progress_begin(0, 9999)

        # System for dynamically deciding the progress percentage
        operation_counter = (
            (gd.uiVisibilityNormals   and gd.exportNormals),
            (gd.uiVisibilityCurvature and gd.exportCurvature),
            (gd.uiVisibilityOcclusion and gd.exportOcclusion),
            (gd.uiVisibilityHeight    and gd.exportHeight),
            (gd.uiVisibilityAlpha     and gd.exportAlpha),
            (gd.uiVisibilityMatID     and gd.exportMatID),
            (gd.uiVisibilityAlbedo    and gd.exportAlbedo),
            (gd.uiVisibilityRoughness and gd.exportRoughness),
            (gd.uiVisibilityMetalness and gd.exportMetalness)
        )

        percentage_division = 100 / (1 + sum(operation_counter))
        percent_till_completed = 0

        export_and_preview_setup(self, context)

        active_selected = False
        if context.object:
            activeCallback = context.object.name
            modeCallback = context.object.mode

            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode='OBJECT')

            active_selected = True

        # Scale up BG Plane (helps overscan & border pixels)
        plane_ob = bpy.data.objects[Global.BG_PLANE_NAME]
        plane_ob.scale[0] = plane_ob.scale[1] = 3

        percent_till_completed += percentage_division
        context.window_manager.progress_update(percent_till_completed)

        if gd.uiVisibilityNormals and gd.exportNormals:
            normals_setup(self, context)
            self.grabdoc_export(context, export_suffix=gd.suffixNormals)

            if gd.reimportAsMatNormals:
                reimport_as_material(gd.suffixNormals)

            cleanup_ng_from_mat(Global.NG_NORMAL_NAME)

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if gd.uiVisibilityCurvature and gd.exportCurvature:
            curvature_setup(self, context)
            self.grabdoc_export(context, export_suffix=gd.suffixCurvature)
            curvature_refresh(self, context)

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if gd.uiVisibilityOcclusion and gd.exportOcclusion:
            occlusion_setup(self, context)
            self.grabdoc_export(context, export_suffix=gd.suffixOcclusion)

            if gd.reimportAsMatOcclusion:
                reimport_as_material(gd.suffixOcclusion)

            cleanup_ng_from_mat(Global.NG_AO_NAME)
            occlusion_refresh(self, context)

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if gd.uiVisibilityHeight and gd.exportHeight:
            height_setup(self, context)
            self.grabdoc_export(context, export_suffix=gd.suffixHeight)
            cleanup_ng_from_mat(Global.NG_HEIGHT_NAME)

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if gd.uiVisibilityAlpha and gd.exportAlpha:
            alpha_setup(self, context)
            self.grabdoc_export(context, export_suffix=gd.suffixAlpha)
            cleanup_ng_from_mat(Global.NG_ALPHA_NAME)

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if gd.uiVisibilityMatID and gd.exportMatID:
            id_setup(self, context)
            self.grabdoc_export(context, export_suffix=gd.suffixID)

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if gd.uiVisibilityAlbedo and gd.exportAlbedo:
            albedo_setup(self, context)
            self.grabdoc_export(context, export_suffix=gd.suffixAlbedo)
            cleanup_ng_from_mat(Global.NG_ALBEDO_NAME)

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if gd.uiVisibilityRoughness and gd.exportRoughness:
            roughness_setup(self, context)
            self.grabdoc_export(context, export_suffix=gd.suffixRoughness)
            cleanup_ng_from_mat(Global.NG_ROUGHNESS_NAME)

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        if gd.uiVisibilityMetalness and gd.exportMetalness:
            metalness_setup(self, context)
            self.grabdoc_export(context, export_suffix=gd.suffixMetalness)
            cleanup_ng_from_mat(Global.NG_METALNESS_NAME)

            percent_till_completed += percentage_division
            context.window_manager.progress_update(percent_till_completed)

        # Refresh all original settings
        export_refresh(self, context)

        plane_ob = bpy.data.objects[Global.BG_PLANE_NAME]
        plane_ob.scale[0] = plane_ob.scale[1] = 1

        if gd.exportPlane:
            export_bg_plane(context)

        if gd.openFolderOnExport:
            bpy.ops.wm.path_open(filepath=bpy.path.abspath(gd.exportPath))

        # Call for Original Context Mode, use bpy.ops
        # so that Blenders viewport refreshes
        if active_selected:
            context.view_layer.objects.active = bpy.data.objects[activeCallback]

            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode=modeCallback)

        # End the timer & UI progress bar
        end = time.time()
        exc_time = round(end - start, 2)

        self.report(
            {'INFO'}, f"{Error.EXPORT_COMPLETE} (execution time: {exc_time}s)"
        )

        context.window_manager.progress_end()
        return {'FINISHED'}


################################################
# OFFLINE RENDERER
################################################


class MapEnum():
    map_types: EnumProperty(
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


class GRABDOC_OT_offline_render(OpInfo, MapEnum, Operator):
    """Renders the selected material and previews it inside Blender"""
    bl_idname = "grab_doc.offline_render"
    bl_options = {'INTERNAL'}

    # TODO:
    # - Might be able to have this uniquely
    #   utilize compositing for mixing maps?
    # - Support Reimport as Materials
    # - Support correct default colorspaces

    @classmethod
    def poll(cls, context: Context) -> bool:
        return True if not context.scene.grabDoc.modalState else poll_message_error(
            cls, "Cannot render, in a Modal State"
        )

    def offline_render(self):
        render = bpy.context.scene.render

        _addon_path, temps_path = get_create_addon_temp_dir()

        # Save & Set - file output path
        saved_path = render.filepath

        image_name = 'GD_Render Result'

        render.filepath = os.path.join(temps_path, image_name + get_format_extension())

        # Delete original image
        if image_name in bpy.data.images:
            bpy.data.images.remove(bpy.data.images[image_name])

        bpy.ops.render.render(write_still=True)

        # Load in the newly rendered image
        new_image = bpy.data.images.load(render.filepath)
        new_image.name = image_name

        # Refresh - file output path
        render.filepath = saved_path

        # Call user prefs window
        bpy.ops.screen.userpref_show("INVOKE_DEFAULT")

        # Change area & image type
        area = bpy.context.window_manager.windows[-1].screen.areas[0]
        area.type = "IMAGE_EDITOR"
        area.spaces.active.image = new_image

    def execute(self, context: Context):
        report_value, report_string = \
            bad_setup_check(self, context, active_export=False)
        if report_value:
            self.report({'ERROR'}, report_string)
            return {'CANCELLED'}

        # Start execution timer after basic error checking
        start = time.time()

        export_and_preview_setup(self, context)

        active_selected = False
        if context.object:
            activeCallback = context.object.name
            modeCallback = context.object.mode

            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode='OBJECT')

            active_selected = True

        # Scale up BG Plane (helps overscan & border pixels)
        plane_ob = bpy.data.objects[Global.BG_PLANE_NAME]
        plane_ob.scale[0] = plane_ob.scale[1] = 3

        # NOTE: Match case exists, looks slightly better vs conditional in this case
        match self.map_types:
            case "normals":
                normals_setup(self, context)
                self.offline_render()
                cleanup_ng_from_mat(Global.NG_NORMAL_NAME)
            case "curvature":
                curvature_setup(self, context)
                self.offline_render()
                curvature_refresh(self, context)
            case "occlusion":
                occlusion_setup(self, context)
                self.offline_render()
                cleanup_ng_from_mat(Global.NG_AO_NAME)
                occlusion_refresh(self, context)
            case "height":
                height_setup(self, context)
                self.offline_render()
                cleanup_ng_from_mat(Global.NG_HEIGHT_NAME)
            case "ID":
                id_setup(self, context)
                self.offline_render()
            case "alpha":
                alpha_setup(self, context)
                self.offline_render()
                cleanup_ng_from_mat(Global.NG_ALPHA_NAME)
            case "albedo":
                albedo_setup(self, context)
                self.offline_render()
                cleanup_ng_from_mat(Global.NG_ALBEDO_NAME)
            case "roughness":
                roughness_setup(self, context)
                self.offline_render()
                cleanup_ng_from_mat(Global.NG_ROUGHNESS_NAME)
            case "metalness":
                metalness_setup(self, context)
                self.offline_render()
                cleanup_ng_from_mat(Global.NG_METALNESS_NAME)

        # Refresh all original settings
        export_refresh(self, context)

        # Scale down BG Plane (helps overscan & border pixels)
        plane_ob = bpy.data.objects[Global.BG_PLANE_NAME]
        plane_ob.scale[0] = plane_ob.scale[1] = 1

        # Call for Original Context Mode, use bpy.ops so
        # that Blenders viewport refreshes
        if active_selected:
            context.view_layer.objects.active = bpy.data.objects[activeCallback]

            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode=modeCallback)

        # End the timer
        end = time.time()
        exc_time = round(end - start, 2)

        self.report(
            {'INFO'}, f"{Error.OFFLINE_RENDER_COMPLETE} (execution time: {exc_time}s)"
        )
        return {'FINISHED'}


################################################
# MAP PREVIEWER
################################################


class GRABDOC_OT_leave_map_preview(Operator):
    """Exit the current Map Preview"""
    bl_idname = "grab_doc.leave_modal"
    bl_label = "Exit Map Preview"
    bl_options = {'INTERNAL', 'REGISTER'}

    def execute(self, context: Context):
        # NOTE: A lot of the modal system relies on this particular
        # switch, if it notices this has been disabled it will begin
        # the exiting sequence in the properties update function and
        # also in the modal method itself
        context.scene.grabDoc.modalState = False
        return {'FINISHED'}


class GRABDOC_OT_map_preview_warning(OpInfo, MapEnum, Operator):
    """Preview the selected material"""
    bl_idname = "grab_doc.preview_warning"
    bl_label = "MATERIAL PREVIEW WARNING"
    bl_options = {'INTERNAL'}

    def invoke(self, context: Context, _event: Event):
        return context.window_manager.invoke_props_dialog(self, width=525)

    def draw(self, _context: Context):
        col = self.layout.column(align=True)
        for line in Global.PREVIEW_WARNING.split('\n')[1:][:-1]:
            col.label(text=line)

    def execute(self, context: Context):
        context.scene.grabDoc.firstBakePreview = False

        bpy.ops.grab_doc.preview_map(map_types=self.map_types)
        return {'FINISHED'}


def draw_callback_px(self, context: Context) -> None:
    """This needs to be outside of the class
    because of how draw_handler_add handles args"""
    render_text = self.map_types.capitalize()
    if self.map_types == 'ID': # Exception for Material ID preview
        render_text = "Material ID"

    font_id = 0
    font_size = 25
    font_opacity = .8
    font_x_pos = 15
    font_y_pos = 80
    font_pos_offset = 50

    # Manually handle small viewports
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    if region.width < 700 or region.height < 400:
                        font_size = 15
                        font_pos_offset = 30
                    break

    # Enable shadow
    blf.enable(font_id, 4)
    blf.shadow(font_id, 0, *(0, 0, 0, font_opacity))

    # Draw text
    blf.position(font_id, font_x_pos, (font_y_pos + font_pos_offset), 0)
    blf.size(font_id, font_size)
    blf.color(font_id, *(1, 1, 1, font_opacity))
    blf.draw(font_id, f"{render_text} Preview  |  [ESC] to exit")

    blf.position(font_id, font_x_pos, font_y_pos, 0)
    blf.size(font_id, font_size+1)
    blf.color(font_id, *(1, 1, 0, font_opacity))
    blf.draw(font_id, "You are in Map Preview mode!")

class GRABDOC_OT_map_preview(OpInfo, MapEnum, Operator):
    """Preview the selected material"""
    bl_idname = "grab_doc.preview_map"
    bl_options = {'INTERNAL'}

    def modal(self, context: Context, event: Event):
        scene = context.scene
        gd = scene.grabDoc

        scene.camera = bpy.data.objects[Global.TRIM_CAMERA_NAME]

        # Set - Exporter settings
        image_settings = scene.render.image_settings

        # If background plane not visible in render, enable alpha channel
        if not gd.collRendered:
            scene.render.film_transparent = True

            image_settings.color_mode = 'RGBA'
        else:
            scene.render.film_transparent = False

            image_settings.color_mode = 'RGB'

        # Get correct file format and color depth
        image_settings.file_format = gd.imageType

        if gd.imageType == 'OPEN_EXR':
            image_settings.color_depth = gd.colorDepthEXR
        elif gd.imageType != 'TARGA':
            image_settings.color_depth = gd.colorDepth

        # Bake map specific settings that are forcibly kept in check
        # TODO: update the node group input values for Mixed Normal
        view_settings = scene.view_settings

        if self.map_types == "curvature":
            view_settings.look = gd.contrastCurvature.replace('_', ' ')

            bpy.data.objects[Global.BG_PLANE_NAME].color[3] = .9999

        elif self.map_types == "occlusion":
            view_settings.look = gd.contrastOcclusion.replace('_', ' ')

            #ao = bpy.data.node_groups[NG_AO_NAME].nodes.get('Ambient Occlusion')
            #ao.inputs[1].default_value = gd.distanceOcclusion

        elif self.map_types == "height":
            view_settings.look = gd.contrastHeight.replace('_', ' ')

        elif self.map_types == "ID":
            scene.display.shading.color_type = gd.methodMatID

        # Exit check
        if not gd.modalState or event.type in {'ESC'} or not proper_scene_setup():
            self.modal_cleanup(context)
            return {'CANCELLED'}
        return {'PASS_THROUGH'}

    def modal_cleanup(self, context: Context) -> None:
        gd = context.scene.grabDoc

        gd.modalState = False

        SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')

        if self.map_types == "normals":
            cleanup_ng_from_mat(Global.NG_NORMAL_NAME)
        elif self.map_types == "curvature":
            curvature_refresh(self, context)
        elif self.map_types == "occlusion":
            occlusion_refresh(self, context)
            cleanup_ng_from_mat(Global.NG_AO_NAME)
        elif self.map_types == "height":
            cleanup_ng_from_mat(Global.NG_HEIGHT_NAME)
        elif self.map_types == "alpha":
            cleanup_ng_from_mat(Global.NG_ALPHA_NAME)
        elif self.map_types == "albedo":
            cleanup_ng_from_mat(Global.NG_ALBEDO_NAME)
        elif self.map_types == "roughness":
            cleanup_ng_from_mat(Global.NG_ROUGHNESS_NAME)
        elif self.map_types == "metalness":
            cleanup_ng_from_mat(Global.NG_METALNESS_NAME)

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

        gd.bakerType = self.savedBakerType

        # Check for auto exit camera option, keep this
        # at the end of the stack to avoid pop in
        if gd.autoExitCamera or not proper_scene_setup():
            bpy.ops.grab_doc.view_cam(from_modal=True)

    def execute(self, context: Context):
        gd = context.scene.grabDoc

        report_value, report_string = \
            bad_setup_check(self, context, active_export=False)
        if report_value:
            self.report({'ERROR'}, report_string)
            return {'CANCELLED'}

        gd.modalState = True

        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        export_and_preview_setup(self, context)

        if not is_camera_in_3d_view():
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
        self.savedBakerType = gd.bakerType
        gd.bakerType = 'Blender'

        # Set - Preview type
        gd.modalPreviewType = self.map_types

        if self.map_types == 'normals':
            normals_setup(self, context)
        elif self.map_types == 'curvature':
            curvature_setup(self, context)
        elif self.map_types == 'occlusion':
            occlusion_setup(self, context)
        elif self.map_types == 'height':
            height_setup(self, context)
        elif self.map_types == 'alpha':
            alpha_setup(self, context)
        elif self.map_types == 'albedo':
            albedo_setup(self, context)
        elif self.map_types == 'roughness':
            roughness_setup(self, context)
        elif self.map_types == 'metalness':
            metalness_setup(self, context)
        else: # ID
            id_setup(self, context)

        # Draw text handler
        self._handle = SpaceView3D.draw_handler_add(
            draw_callback_px, (self, context), 'WINDOW', 'POST_PIXEL'
        )

        # Modal handler
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class GRABDOC_OT_export_current_preview(OpInfo, Operator):
    """Export the currently previewed material"""
    bl_idname = "grab_doc.export_preview"
    bl_label = "Export Previewed Map"

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.scene.grabDoc.modalState

    def execute(self, context: Context):
        gd = context.scene.grabDoc

        report_value, report_string = bad_setup_check(self, context, active_export=True)
        if report_value:
            self.report({'ERROR'}, report_string)
            return {'CANCELLED'}

        # Start counting execution time
        start = time.time()

        # Save - file output path
        render = context.scene.render
        saved_path = render.filepath

        if gd.modalPreviewType == 'normals':
            export_suffix = gd.suffixNormals
        elif gd.modalPreviewType == 'curvature':
            export_suffix = gd.suffixCurvature
        elif gd.modalPreviewType == 'occlusion':
            export_suffix = gd.suffixOcclusion
        elif gd.modalPreviewType == 'height':
            export_suffix = gd.suffixHeight
        elif gd.modalPreviewType == 'ID':
            export_suffix = gd.suffixID
        elif gd.modalPreviewType == 'alpha':
            export_suffix = gd.suffixAlpha
        elif gd.modalPreviewType == 'albedo':
            export_suffix = gd.suffixAlbedo
        elif gd.modalPreviewType == 'roughness':
            export_suffix = gd.suffixRoughness
        elif gd.modalPreviewType == 'metalness':
            export_suffix = gd.suffixMetalness

        # Set - Output path to add-on path + add-on name + the
        # type of map exported (file extensions get handled automatically)
        render.filepath = \
            bpy.path.abspath(gd.exportPath) + gd.exportName + f"_{export_suffix}"

        # Set - Scale up the plane
        plane_ob = bpy.data.objects[Global.BG_PLANE_NAME]
        plane_ob.scale[0] = plane_ob.scale[1] = 3

        bpy.ops.render.render(write_still=True)

        # Refresh - file output path
        render.filepath = saved_path

        # Reimport the Normal/Occlusion map as a material if requested
        if gd.modalPreviewType == 'normals' and gd.reimportAsMatNormals:
            reimport_as_material(gd.suffixNormals)
        elif gd.modalPreviewType == 'occlusion' and gd.reimportAsMatOcclusion:
            reimport_as_material(gd.suffixOcclusion)

        # Refresh - Scale down the plane
        plane_ob = bpy.data.objects[Global.BG_PLANE_NAME]
        plane_ob.scale[0] = plane_ob.scale[1] = 1

        if gd.exportPlane:
            export_bg_plane(context)

        # Open export path location if requested
        if gd.openFolderOnExport:
            bpy.ops.wm.path_open(filepath=bpy.path.abspath(gd.exportPath))

        # End the timer
        end = time.time()
        exc_time = round(end - start, 2)

        self.report(
            {'INFO'}, f"{Error.EXPORT_COMPLETE} (execution time: {exc_time}s)"
        )
        return {'FINISHED'}


#class GRABDOC_OT_map_pack_info(OpInfo, Operator):
#    """Information about Map Packing and current limitations"""
#    bl_idname = "grab_doc.map_pack_info"
#    bl_label = "MAP PACKING INFORMATION"
#    bl_options = {'INTERNAL'}#

#    def invoke(self, context: Context, _event: Event):
#        return context.window_manager.invoke_props_dialog(self, width=500)

#    def draw(self, _context: Context):
#        col = self.layout.column(align=True)
#        for line in Global.PACK_MAPS_WARNING.split('\n')[1:][:-1]:
#            col.label(text=line)
#
#    def execute(self, context: Context):
#        return {'FINISHED'}


################################################
# REGISTRATION
################################################


classes = (
    GRABDOC_OT_load_ref,
    GRABDOC_OT_open_folder,
    GRABDOC_OT_view_cam,
    GRABDOC_OT_setup_scene,
    GRABDOC_OT_remove_setup,
    GRABDOC_OT_offline_render,
    GRABDOC_OT_export_maps,
    GRABDOC_OT_map_preview_warning,
    GRABDOC_OT_map_preview,
    GRABDOC_OT_leave_map_preview,
    GRABDOC_OT_export_current_preview
    #GRABDOC_OT_map_pack_info
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
