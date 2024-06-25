import os
import time
import numpy

import bpy
import blf
from bpy.types import SpaceView3D, Event, Context, Operator, UILayout
from bpy.props import StringProperty

from ..constants import Global, Error
from ..utils.render import get_rendered_objects
from ..utils.node import apply_node_to_objects, node_cleanup
from ..utils.scene import scene_setup, remove_setup
from ..utils.generic import (
    OpInfo,
    get_format,
    proper_scene_setup,
    bad_setup_check,
    export_plane,
    is_camera_in_3d_view,
    poll_message_error,
    get_create_addon_temp_dir
)
from ..utils.baker import (
    baker_init,
    get_bake_maps,
    baker_cleanup,
    get_bakers,
    reimport_as_material
)


################################################
# MISC
################################################


class GRABDOC_OT_load_reference(OpInfo, Operator):
    """Import a reference onto the background plane"""
    bl_idname = "grab_doc.load_reference"
    bl_label = "Load Reference"

    filepath: StringProperty(subtype="FILE_PATH")

    def execute(self, context: Context):
        bpy.data.images.load(self.filepath, check_existing=True)
        context.scene.gd.reference = \
            bpy.data.images[
                os.path.basename(os.path.normpath(self.filepath))
            ]
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
                filepath=bpy.path.abspath(context.scene.gd.export_path)
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
# MAP EXPORT
################################################


class GRABDOC_OT_export_maps(OpInfo, Operator, UILayout):
    """Export all enabled bake maps"""
    bl_idname = "grab_doc.export_maps"
    bl_label = "Export Maps"
    bl_options = {'INTERNAL'}

    progress_factor = 0.0

    @classmethod
    def poll(cls, context: Context) -> bool:
        return not context.scene.gd.preview_state

    @staticmethod
    def export(context: Context, suffix: str, path: str = None) -> str:
        gd = context.scene.gd
        render = context.scene.render
        saved_path = render.filepath

        name = f"{gd.export_name}_{suffix}"
        if path is None:
            path = bpy.path.abspath(gd.export_path)
        path = os.path.join(path, name + get_format())
        render.filepath = path

        context.scene.camera = bpy.data.objects[Global.TRIM_CAMERA_NAME]

        bpy.ops.render.render(write_still=True)
        render.filepath = saved_path
        return path

    def execute(self, context: Context):
        gd = context.scene.gd
        report_value, report_string = \
            bad_setup_check(context, active_export=True)
        if report_value:
            self.report({'ERROR'}, report_string)
            return {'CANCELLED'}
        if gd.use_pack_maps is True and not is_pack_maps_enabled():
            self.report(
                {'ERROR'},
                "Map packing enabled but incorrect export maps enabled"
            )
            return {'CANCELLED'}

        self.map_name = 'export'

        bake_maps = get_bake_maps()

        start = time.time()
        context.window_manager.progress_begin(0, 9999)
        completion_step = 100 / (1 + len(bake_maps))
        completion_percent = 0

        baker_init(self, context)

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

        rendered_objects = get_rendered_objects()
        for bake_map in bake_maps:
            bake_map.setup()
            if bake_map.NODE:
                result = apply_node_to_objects(bake_map.NODE, rendered_objects)
                if result is False:
                    self.report({'INFO'}, Error.MAT_SLOTS_WITHOUT_LINKS)

            self.export(context, bake_map.suffix)
            bake_map.cleanup()
            if bake_map.NODE:
                node_cleanup(bake_map.NODE)

            completion_percent += completion_step
            context.window_manager.progress_update(completion_percent)

        # Reimport textures to render result material
        map_names = [bake.ID for bake in bake_maps if bake.reimport]
        reimport_as_material(map_names)

        # Refresh all original settings
        baker_cleanup(self, context)

        plane_ob = bpy.data.objects[Global.BG_PLANE_NAME]
        plane_ob.scale[0] = plane_ob.scale[1] = 1

        if gd.export_plane:
            export_plane(context)

        if active_selected:
            context.view_layer.objects.active = bpy.data.objects[activeCallback]
            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode=modeCallback)

        end = time.time()
        exc_time = round(end - start, 2)
        self.report(
            {'INFO'}, f"{Error.EXPORT_COMPLETE} (execution time: {exc_time}s)"
        )
        context.window_manager.progress_end()

        if gd.use_pack_maps is True:
            bpy.ops.grab_doc.pack_maps()
        return {'FINISHED'}


class GRABDOC_OT_single_render(OpInfo, Operator):
    """Renders the selected material and previews it inside Blender"""
    bl_idname = "grab_doc.single_render"
    bl_options = {'INTERNAL'}

    map_name: StringProperty()

    # TODO:
    # - Might be able to have this uniquely
    #   utilize compositing for mixing maps?
    # - Support Reimport as Materials
    # - Support correct default color spaces

    @classmethod
    def poll(cls, context: Context) -> bool:
        return True if not context.scene.gd.preview_state else poll_message_error(
            cls, "Cannot render, in a Modal State"
        )

    def open_render_image(self, filepath: str):
        new_image = bpy.data.images.load(filepath, check_existing=True)
        bpy.ops.screen.userpref_show("INVOKE_DEFAULT")
        area = bpy.context.window_manager.windows[-1].screen.areas[0]
        area.type = "IMAGE_EDITOR"
        area.spaces.active.image = new_image

    def execute(self, context: Context):
        report_value, report_string = \
            bad_setup_check(context, active_export=False)
        if report_value:
            self.report({'ERROR'}, report_string)
            return {'CANCELLED'}

        start = time.time()

        active_selected = False
        if context.object:
            activeCallback = context.object.name
            modeCallback = context.object.mode
            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode='OBJECT')
            active_selected = True

        plane_ob = bpy.data.objects[Global.BG_PLANE_NAME]
        plane_ob.scale[0] = plane_ob.scale[1] = 3

        baker_init(self, context)

        gd = context.scene.gd
        self.baker = getattr(gd, self.map_name)[0]
        self.baker.setup()
        if self.baker.NODE:
            result = apply_node_to_objects(
                self.baker.NODE, get_rendered_objects()
            )
            if result is False:
                self.report({'INFO'}, Error.MAT_SLOTS_WITHOUT_LINKS)
        path = GRABDOC_OT_export_maps.export(
            context, self.baker.suffix, path=get_create_addon_temp_dir()[1]
        )
        self.open_render_image(path)
        self.baker.cleanup()
        if self.baker.NODE:
            node_cleanup(self.baker.NODE)

        # Reimport textures to render result material
        if self.baker.reimport:
            reimport_as_material([self.baker.ID])

        baker_cleanup(self, context)

        plane_ob = bpy.data.objects[Global.BG_PLANE_NAME]
        plane_ob.scale[0] = plane_ob.scale[1] = 1

        if active_selected:
            context.view_layer.objects.active = bpy.data.objects[activeCallback]
            # NOTE: Also helps refresh viewport
            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode=modeCallback)

        end = time.time()
        exc_time = round(end - start, 2)

        self.report(
            {'INFO'},
            f"{Error.OFFLINE_RENDER_COMPLETE} (execution time: {exc_time}s)"
        )
        return {'FINISHED'}


################################################
# MAP PREVIEW
################################################


class GRABDOC_OT_leave_map_preview(Operator):
    """Exit the current Map Preview"""
    bl_idname = "grab_doc.leave_modal"
    bl_label = "Exit Map Preview"
    bl_options = {'INTERNAL', 'REGISTER'}

    def execute(self, context: Context):
        context.scene.gd.preview_state = False
        return {'FINISHED'}


class GRABDOC_OT_map_preview_warning(OpInfo, Operator):
    """Preview the selected material"""
    bl_idname = "grab_doc.preview_warning"
    bl_label = "MATERIAL PREVIEW WARNING"
    bl_options = {'INTERNAL'}

    map_name: StringProperty()

    def invoke(self, context: Context, _event: Event):
        return context.window_manager.invoke_props_dialog(self, width=525)

    def draw(self, _context: Context):
        self.layout.label(text=Global.PREVIEW_WARNING)
        #col = self.layout.column(align=True)
        #for line in Global.PREVIEW_WARNING.split('\n')[1:][:-1]:
        #    col.label(text=line)
        #    col.separator()

    def execute(self, context: Context):
        context.scene.gd.preview_first_time = False
        bpy.ops.grab_doc.preview_map(map_name=self.map_name)
        return {'FINISHED'}


def draw_callback_px(self, context: Context) -> None:
    """This needs to be outside of the class
    because of how draw_handler_add handles args"""
    font_id = 0
    font_size = 25
    font_opacity = .8
    font_x_pos = 15
    font_y_pos = 80
    font_pos_offset = 50

    # NOTE: Handle small viewports
    for area in context.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        for region in area.regions:
            if region.type != 'WINDOW':
                continue
            if region.width <= 700 or region.height <= 400:
                font_size *= .5
                font_pos_offset *= .5
            break

    blf.enable(font_id, 4)
    blf.shadow(font_id, 0, *(0, 0, 0, font_opacity))
    blf.position(font_id, font_x_pos, (font_y_pos + font_pos_offset), 0)
    blf.size(font_id, font_size)
    blf.color(font_id, *(1, 1, 1, font_opacity))
    render_text = self.map_name.capitalize()
    blf.draw(font_id, f"{render_text} Preview  |  [ESC] to exit")
    blf.position(font_id, font_x_pos, font_y_pos, 0)
    blf.size(font_id, font_size+1)
    blf.color(font_id, *(1, 1, 0, font_opacity))
    blf.draw(font_id, "You are in Map Preview mode!")


class GRABDOC_OT_map_preview(OpInfo, Operator):
    """Preview the selected material"""
    bl_idname = "grab_doc.preview_map"
    bl_options = {'INTERNAL'}

    map_name: StringProperty()

    def modal(self, context: Context, event: Event):
        scene = context.scene
        gd = scene.gd

        scene.camera = bpy.data.objects[Global.TRIM_CAMERA_NAME]

        # Exporter settings
        # NOTE: Use alpha channel if background plane not visible in render
        image_settings = scene.render.image_settings
        if not gd.coll_rendered:
            scene.render.film_transparent = True
            image_settings.color_mode = 'RGBA'
        else:
            scene.render.film_transparent = False
            image_settings.color_mode = 'RGB'

        # Get correct file format and color depth
        image_settings.file_format = gd.format
        if gd.format == 'OPEN_EXR':
            image_settings.color_depth = gd.exr_depth
        elif gd.format != 'TARGA':
            image_settings.color_depth = gd.depth

        # Exit check
        if not gd.preview_state \
        or event.type in {'ESC'} \
        or not proper_scene_setup():
            self.modal_cleanup(context)
            return {'CANCELLED'}
        return {'PASS_THROUGH'}

    def modal_cleanup(self, context: Context) -> None:
        gd = context.scene.gd
        gd.preview_state = False

        SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')

        self.baker.cleanup()
        node_cleanup(self.baker.NODE)
        baker_cleanup(self, context)

        # Current workspace shading type
        for area in context.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for space in area.spaces:
                space.shading.type = self.saved_render_view
                break

        # Current workspace shading type
        for screens in bpy.data.workspaces[self.savedWorkspace].screens:
            for area in screens.areas:
                if area.type != 'VIEW_3D':
                    continue
                for space in area.spaces:
                    space.shading.type = self.saved_render_view
                    break

        gd.baker_type = self.savedBakerType
        context.scene.render.engine = self.savedEngine

        # Check for auto exit camera option, keep this
        # at the end of the stack to avoid pop in
        if not proper_scene_setup():
            bpy.ops.grab_doc.view_cam(from_modal=True)

    def execute(self, context: Context):
        report_value, report_string = \
            bad_setup_check(context, active_export=False)
        if report_value:
            self.report({'ERROR'}, report_string)
            return {'CANCELLED'}

        gd = context.scene.gd
        self.savedBakerType = gd.baker_type
        self.savedWorkspace = context.workspace.name
        self.savedEngine = context.scene.render.engine
        gd.preview_state = True
        gd.preview_type = self.map_name
        gd.baker_type = 'blender'

        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    self.saved_render_view = space.shading.type
                    space.shading.type = 'RENDERED'
                    break
        if not is_camera_in_3d_view():
            bpy.ops.view3d.view_camera()

        baker_init(self, context)

        self.baker = getattr(gd, self.map_name)[0]
        self.baker.setup()
        if self.baker.NODE:
            rendered_objects = get_rendered_objects()
            result = apply_node_to_objects(self.baker.NODE, rendered_objects)
            if result is False:
                self.report({'INFO'}, Error.MAT_SLOTS_WITHOUT_LINKS)
        self._handle = SpaceView3D.draw_handler_add(
            draw_callback_px, (self, context), 'WINDOW', 'POST_PIXEL'
        )
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class GRABDOC_OT_export_current_preview(OpInfo, Operator):
    """Export the currently previewed material"""
    bl_idname = "grab_doc.export_preview"
    bl_label = "Export Previewed Map"

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.scene.gd.preview_state

    def execute(self, context: Context):
        gd = context.scene.gd

        report_value, report_string = \
            bad_setup_check(context, active_export=True)
        if report_value:
            self.report({'ERROR'}, report_string)
            return {'CANCELLED'}

        start = time.time()

        # NOTE: Manual plane scale to account for overscan
        plane_ob = bpy.data.objects[Global.BG_PLANE_NAME]
        scale_plane = False
        if plane_ob.scale[0] == 1:
            scale_plane = True
            plane_ob.scale[0] = plane_ob.scale[1] = 3

        baker = getattr(gd, gd.preview_type)[0]

        GRABDOC_OT_export_maps.export(context, baker.suffix)
        if baker.reimport:
            reimport_as_material([baker.ID])

        if scale_plane:
            plane_ob.scale[0] = plane_ob.scale[1] = 1

        if gd.export_plane:
            export_plane(context)

        end = time.time()
        exc_time = round(end - start, 2)

        self.report(
            {'INFO'}, f"{Error.EXPORT_COMPLETE} (execution time: {exc_time}s)"
        )
        return {'FINISHED'}


class GRABDOC_OT_config_maps(Operator):
    """Configure bake map UI visibility, will also disable baking"""
    bl_idname = "grab_doc.config_maps"
    bl_label = "Configure Map Visibility"
    bl_options = {'REGISTER'}

    def execute(self, _context):
        return {'FINISHED'}

    def invoke(self, context: Context, _event: Event):
        return context.window_manager.invoke_props_dialog(self, width=200)

    def draw(self, _context: Context):
        layout = self.layout
        col = layout.column(align=True)

        bakers = get_bakers()
        for baker in bakers:
            icon = \
                "BLENDER" if not baker[0].MARMOSET_COMPATIBLE else "WORLD"
            col.prop(
                baker[0], 'visibility',
                text=baker[0].NAME, icon=icon
            )


################################################
# CHANNEL PACKING
################################################


def pack_image_channels(pack_order, PackName):
    """
    NOTE: Original code sourced from:
    https://blender.stackexchange.com/questions/274712/how-to-channel-pack-texture-in-python
    """
    dst_array = None
    has_alpha = False

    # Build the packed pixel array
    for pack_item in pack_order:
        image = pack_item[0]
        # Initialize arrays on the first iteration
        if dst_array is None:
            w, h = image.size
            src_array = numpy.empty(w * h * 4, dtype=numpy.float32)
            dst_array = numpy.ones(w * h * 4, dtype=numpy.float32)
        assert image.size[:] == (w, h), "Images must be same size"

        # Fetch pixels from the source image and copy channels
        image.pixels.foreach_get(src_array)
        for src_chan, dst_chan in pack_item[1:]:
            if dst_chan == 3:
                has_alpha = True
            dst_array[dst_chan::4] = src_array[src_chan::4]

    # Create image from the packed pixels
    dst_image = bpy.data.images.new(PackName, w, h, alpha=has_alpha)
    dst_image.pixels.foreach_set(dst_array)

    return dst_image


def get_channel_path(channel: str) -> str | None:
    """Get the channel path of the given channel name.

    If the channel path is not found returns `None`."""
    gd = bpy.context.scene.gd
    fmt = get_format()
    filename = ""
    if channel == 'normals':
        filename = gd.export_name + '_' + gd.occlusion[0].suffix + fmt
    elif channel == 'curvature':
        filename = gd.export_name + '_' + gd.curvature[0].suffix + fmt
    elif channel == 'occlusion':
        filename = gd.export_name + '_' + gd.occlusion[0].suffix + fmt
    elif channel == 'height':
        filename = gd.export_name + '_' + gd.height[0].suffix + fmt
    elif channel == 'id':
        filename = gd.export_name + '_' + gd.id[0].suffix + fmt
    elif channel == 'alpha':
        filename = gd.export_name + '_' + gd.alpha[0].suffix + fmt
    elif channel == 'color':
        filename = gd.export_name + '_' + gd.color[0].suffix + fmt
    elif channel == 'emissive':
        filename = gd.export_name + '_' + gd.emissive[0].suffix + fmt
    elif channel == 'roughness':
        filename = gd.export_name + '_' + gd.roughness[0].suffix + fmt
    elif channel == 'metallic':
        filename = gd.export_name + '_' + gd.metallic[0].suffix + fmt
    if filename == "":
        return None
    filepath = os.path.join(gd.export_path, filename)
    if not os.path.exists(filepath):
        return None
    return filepath


def is_pack_maps_enabled() -> bool:
    """Checks if the chosen pack channels
    match the enabled maps to export.

    This function also returns True if a required
    bake map is not enabled but the texture exists."""
    bake_maps = get_bake_maps()
    bake_map_names = ['none']
    for bake_map in bake_maps:
        bake_map_names.append(bake_map.ID)

    gd = bpy.context.scene.gd
    if gd.channel_r not in bake_map_names \
    and get_channel_path(gd.channel_r) is None:
        return False
    if gd.channel_g not in bake_map_names \
    and get_channel_path(gd.channel_g) is None:
        return False
    if gd.channel_b not in bake_map_names \
    and get_channel_path(gd.channel_b) is None:
        return False
    if gd.channel_a not in bake_map_names \
    and get_channel_path(gd.channel_a) is None:
        return False
    return True


class GRABDOC_OT_pack_maps(OpInfo, Operator):
    """Merge previously exported bake maps into single packed texture"""
    bl_idname = "grab_doc.pack_maps"
    bl_label = "Run Pack"

    @classmethod
    def poll(cls, context: Context) -> bool:
        gd = context.scene.gd
        r = get_channel_path(gd.channel_r)
        g = get_channel_path(gd.channel_g)
        b = get_channel_path(gd.channel_b)
        a = get_channel_path(gd.channel_a)
        if not all((r, g, b)):
            return False
        if gd.channel_a != 'none' and a is None:
            return False
        return True

    def execute(self, context):
        gd = context.scene.gd

        pack_name = gd.export_name + "_" + gd.pack_name
        path = gd.export_path

        # Loads all images into blender to avoid using a
        # separate python module to convert to np array
        image_r = bpy.data.images.load(get_channel_path(gd.channel_r))
        image_g = bpy.data.images.load(get_channel_path(gd.channel_g))
        image_b = bpy.data.images.load(get_channel_path(gd.channel_b))
        pack_order = [
            (image_r, (0, 0)),
            (image_g, (0, 1)),
            (image_b, (0, 2))
        ]
        if gd.channel_a != 'none':
            image_a = bpy.data.images.load(get_channel_path(gd.channel_a))
            pack_order.append((image_a, (0, 3)))

        dst_image = pack_image_channels(pack_order, pack_name)
        dst_image.filepath_raw = path+"//"+pack_name+get_format()
        dst_image.file_format = gd.format
        dst_image.save()

        # Remove images from blend file to keep it clean
        bpy.data.images.remove(image_r)
        bpy.data.images.remove(image_g)
        bpy.data.images.remove(image_b)
        if gd.channel_a != 'none':
            bpy.data.images.remove(image_a)
        bpy.data.images.remove(dst_image)

        # Option to delete the extra maps through the operator panel
        if gd.remove_original_maps is True:
            if os.path.exists(get_channel_path(gd.channel_r)):
                os.remove(get_channel_path(gd.channel_r))

            if os.path.exists(get_channel_path(gd.channel_g)):
                os.remove(get_channel_path(gd.channel_g))

            if os.path.exists(get_channel_path(gd.channel_b)):
                os.remove(get_channel_path(gd.channel_b))
                
            if gd.channel_a != 'none':
                if os.path.exists(get_channel_path(gd.channel_a)):
                    os.remove(get_channel_path(gd.channel_a))
        return {'FINISHED'}


################################################
# REGISTRATION
################################################


classes = (
    GRABDOC_OT_load_reference,
    GRABDOC_OT_open_folder,
    GRABDOC_OT_view_cam,
    GRABDOC_OT_setup_scene,
    GRABDOC_OT_remove_setup,
    GRABDOC_OT_single_render,
    GRABDOC_OT_export_maps,
    GRABDOC_OT_map_preview_warning,
    GRABDOC_OT_map_preview,
    GRABDOC_OT_leave_map_preview,
    GRABDOC_OT_export_current_preview,
    GRABDOC_OT_config_maps,
    GRABDOC_OT_pack_maps
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
