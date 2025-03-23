import os
import time

import bpy
import blf
from bpy.types import SpaceView3D, Event, Context, Operator, UILayout
from bpy.props import StringProperty, IntProperty

from ..constants import Global, Error
from ..ui import register_baker_panels
from ..utils.io import get_format, get_temp_path
from ..utils.render import get_rendered_objects
from ..utils.generic import get_user_preferences
from ..utils.node import link_group_to_object, node_cleanup
from ..utils.scene import (
    camera_in_3d_view, is_scene_valid,
    scene_setup, scene_cleanup, validate_scene
)
from ..utils.baker import (
    get_baker_collections, import_baker_textures, baker_setup,
    baker_cleanup, get_bakers, get_baker_by_index
)
from ..utils.pack import (
    get_channel_path, pack_image_channels, is_pack_maps_enabled
)


class GRABDOC_OT_load_reference(Operator):
    """Import a reference onto the background plane"""
    bl_idname  = "grabdoc.load_reference"
    bl_label   = "Load Reference"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: StringProperty(subtype="FILE_PATH")

    def execute(self, context: Context):
        bpy.data.images.load(self.filepath, check_existing=True)
        path = os.path.basename(os.path.normpath(self.filepath))
        context.scene.gd.reference = bpy.data.images[path]
        return {'FINISHED'}

    def invoke(self, context: Context, _event: Event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class GRABDOC_OT_open_folder(Operator):
    """Opens up the File Explorer to the designated folder location"""
    bl_idname  = "grabdoc.open_folder"
    bl_label   = "Open Export Folder"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: Context):
        try:
            bpy.ops.wm.path_open(filepath=context.scene.gd.filepath)
        except RuntimeError:
            self.report({'ERROR'}, Error.NO_VALID_PATH_SET)
            return {'CANCELLED'}
        return {'FINISHED'}


class GRABDOC_OT_toggle_camera_view(Operator):
    """View or leave the GrabDoc camera view"""
    bl_idname = "grabdoc.toggle_camera_view"
    bl_label  = "Toggle Camera View"

    def execute(self, context: Context):
        context.scene.camera = bpy.data.objects[Global.TRIM_CAMERA_NAME]
        bpy.ops.view3d.view_camera()
        return {'FINISHED'}


class GRABDOC_OT_scene_setup(Operator):
    """Setup or rebuild GrabDoc in your current scene.

Useful for rare cases where GrabDoc isn't compatible with an existing setup.

Can also potentially fix console spam from UI elements"""
    bl_idname  = "grabdoc.scene_setup"
    bl_label   = "Setup GrabDoc Scene"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return GRABDOC_OT_baker_export_single.poll(context)

    def execute(self, context: Context):
        for baker_prop in get_baker_collections():
            baker_prop.clear()
            baker = baker_prop.add()

        register_baker_panels()
        scene_setup(self, context)

        for baker in get_bakers():
            baker.node_setup()
        return {'FINISHED'}


class GRABDOC_OT_scene_cleanup(Operator):
    """Remove all GrabDoc objects from the scene; keeps reimported textures"""
    bl_idname  = "grabdoc.scene_cleanup"
    bl_label   = "Remove GrabDoc Scene"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return GRABDOC_OT_baker_export_single.poll(context)

    def execute(self, context: Context):
        scene_cleanup(context)
        return {'FINISHED'}


class GRABDOC_OT_baker_add(Operator):
    """Add a new baker of this type to the current scene"""
    bl_idname  = "grabdoc.baker_add"
    bl_label   = "Add Bake Map"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    map_type: StringProperty()

    def execute(self, context: Context):
        baker_prop = getattr(context.scene.gd, self.map_type)
        baker = baker_prop.add()
        register_baker_panels()
        baker.node_setup()
        return {'FINISHED'}


class GRABDOC_OT_baker_remove(Operator):
    """Remove the current baker from the current scene"""
    bl_idname  = "grabdoc.baker_remove"
    bl_label   = "Remove Baker"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    map_type:    StringProperty()
    baker_index: IntProperty()

    def execute(self, context: Context):
        baker_prop = getattr(context.scene.gd, self.map_type)
        baker = get_baker_by_index(baker_prop, self.baker_index)
        if baker.node_tree:
            bpy.data.node_groups.remove(baker.node_tree)
        for idx, bake_map in enumerate(baker_prop):
            if bake_map.index == baker.index:
                baker_prop.remove(idx)
                break
        register_baker_panels()
        return {'FINISHED'}


class GRABDOC_OT_baker_export(Operator, UILayout):
    """Bake and export all enabled bake maps"""
    bl_idname = "grabdoc.baker_export"
    bl_label   = "Export Maps"
    bl_options = {'REGISTER', 'INTERNAL'}

    progress_factor = 0.0
    map_type = ''

    @classmethod
    def poll(cls, context: Context) -> bool:
        gd = context.scene.gd
        if gd.filepath == "//" and not bpy.data.filepath:
            cls.poll_message_set("Relative export path set but file not saved")
            return False
        if gd.preview_state:
            cls.poll_message_set("Cannot run while in Map Preview")
            return False
        return True

    @staticmethod
    def export(context: Context, suffix: str, path: str = None) -> str:
        gd = context.scene.gd
        render = context.scene.render
        saved_path = render.filepath

        name = f"{gd.filename}_{suffix}"
        if path is None:
            path = gd.filepath
        path = os.path.join(path, name + get_format())
        render.filepath = path

        context.scene.camera = bpy.data.objects[Global.TRIM_CAMERA_NAME]

        bpy.ops.render.render(write_still=True)
        render.filepath = saved_path
        return path

    def execute(self, context: Context):
        gd = context.scene.gd
        report_value, report_string = validate_scene(context)
        if report_value:
            self.report({'ERROR'}, report_string)
            return {'CANCELLED'}
        bakers = get_bakers(filter_enabled=True)
        if not bakers:
            self.report({'ERROR'}, Error.ALL_MAPS_DISABLED)
            return {'CANCELLED'}
        if gd.use_pack_maps is True and not is_pack_maps_enabled():
            self.report(
                {'ERROR'},
                "Map packing enabled but incorrect export maps enabled"
            )
            return {'CANCELLED'}

        self.map_type = 'export'

        start = time.time()
        context.window_manager.progress_begin(0, 9999)
        completion_step = 100 / (1 + len(bakers))
        completion_percent = 0

        saved_properties = baker_setup(context)

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
        for baker in bakers:
            baker.setup()
            if not baker.node_tree:
                continue
            for ob in rendered_objects:
                sockets = link_group_to_object(ob, baker.node_tree)
                sockets = baker.filter_required_sockets(sockets)
                if not sockets:
                    continue
                self.report(
                    {'WARNING'},
                    f"{ob.name}: {sockets} {Error.MISSING_SLOT_LINKS}"
                )

            self.export(context, baker.suffix)
            baker.cleanup()
            if baker.node_tree:
                node_cleanup(baker.node_tree)

            completion_percent += completion_step
            context.window_manager.progress_update(completion_percent)

        # Reimport textures to render result material
        bakers_to_reimport = [baker for baker in bakers if baker.reimport]
        if bakers_to_reimport:
            import_baker_textures(bakers_to_reimport)

        # Refresh all original settings
        baker_cleanup(context, saved_properties)

        plane_ob = bpy.data.objects[Global.BG_PLANE_NAME]
        plane_ob.scale[0] = plane_ob.scale[1] = 1

        if active_selected:
            context.view_layer.objects.active = bpy.data.objects[activeCallback]
            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode=modeCallback)

        elapsed = round(time.time() - start, 2)
        self.report(
            {'INFO'}, f"{Error.EXPORT_COMPLETE} (execution time: {elapsed}s)"
        )
        context.window_manager.progress_end()

        if gd.use_pack_maps is True:
            bpy.ops.grabdoc.baker_pack()
        return {'FINISHED'}


class GRABDOC_OT_baker_export_single(Operator):
    """Render the selected bake map and preview it within Blender.

Rendering a second time will overwrite the internal image"""
    bl_idname  = "grabdoc.baker_export_single"
    bl_label   = ""
    bl_options = {'REGISTER', 'INTERNAL'}

    map_type: StringProperty()
    baker_index: IntProperty()

    @classmethod
    def poll(cls, context: Context) -> bool:
        if context.scene.gd.preview_state:
            cls.poll_message_set("Cannot do this while in Map Preview")
            return False
        return True

    def open_render_image(self, filepath: str):
        bpy.ops.screen.userpref_show("INVOKE_DEFAULT")
        area = bpy.context.window_manager.windows[-1].screen.areas[0]
        area.type = "IMAGE_EDITOR"
        area.spaces.active.image = bpy.data.images.load(
            filepath, check_existing=True
        )

    def execute(self, context: Context):
        report_value, report_string = validate_scene(context, False)
        if report_value:
            self.report({'ERROR'}, report_string)
            return {'CANCELLED'}

        start = time.time()

        activeCallback = None
        if context.object:
            activeCallback = context.object.name
            modeCallback = context.object.mode
            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode='OBJECT')

        plane_ob = bpy.data.objects[Global.BG_PLANE_NAME]
        plane_ob.scale[0] = plane_ob.scale[1] = 3

        saved_properties = baker_setup(context)

        gd = context.scene.gd
        self.baker = getattr(gd, self.map_type)[self.baker_index]
        self.baker.setup()
        if self.baker.node_tree:
            for ob in get_rendered_objects():
                sockets = link_group_to_object(ob, self.baker.node_tree)
                sockets = self.baker.filter_required_sockets(sockets)
                if not sockets:
                    continue
                self.report(
                    {'WARNING'},
                    f"{ob.name}: {sockets} {Error.MISSING_SLOT_LINKS}"
                )
        path = GRABDOC_OT_baker_export.export(
            context, self.baker.suffix, path=get_temp_path()
        )
        self.open_render_image(path)
        self.baker.cleanup()
        if self.baker.node_tree:
            node_cleanup(self.baker.node_tree)

        # Reimport textures to render result material
        if self.baker.reimport:
            import_baker_textures([self.baker])

        baker_cleanup(context, saved_properties)

        plane_ob = bpy.data.objects[Global.BG_PLANE_NAME]
        plane_ob.scale[0] = plane_ob.scale[1] = 1

        if activeCallback:
            context.view_layer.objects.active = bpy.data.objects[activeCallback]
            # NOTE: Also helps refresh viewport
            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode=modeCallback)

        elapsed = round(time.time() - start, 2)
        self.report(
            {'INFO'}, f"{Error.EXPORT_COMPLETE} (execute time: {elapsed}s)"
        )
        return {'FINISHED'}


class GRABDOC_OT_baker_preview_exit(Operator):
    """Exit the current Map Preview"""
    bl_idname  = "grabdoc.baker_preview_exit"
    bl_label   = "Exit Map Preview"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context: Context):
        context.scene.gd.preview_state = False
        return {'FINISHED'}


# NOTE: This needs to be outside of the class due
#       to how `draw_handler_add` handles args
def draw_callback_px(self, context: Context) -> None:
    font_id         = 0
    font_size       = 25
    font_opacity    = .8
    font_x_pos      = 15
    font_y_pos      = 80
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
    render_text = f"{self.preview_name.capitalize()} Preview"
    if self.disable_binds:
        render_text += "  |  [ESC] to exit"
    blf.draw(font_id, render_text)
    blf.position(font_id, font_x_pos, font_y_pos, 0)
    blf.size(font_id, font_size+1)
    blf.color(font_id, *(1, 1, 0, font_opacity))
    blf.draw(font_id, "You are in Map Preview mode!")


class GRABDOC_OT_baker_preview(Operator):
    """Preview the selected bake map type"""
    bl_idname = "grabdoc.baker_preview"
    bl_label   = ""
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    baker_index:    IntProperty()
    map_type:       StringProperty()
    last_ob_amount: int  = 0
    disable_binds:  bool = False

    def modal(self, context: Context, event: Event):
        scene = context.scene
        gd    = scene.gd

        # Format
        # NOTE: Set alpha channel if background plane not visible in render
        image_settings = scene.render.image_settings
        if not gd.coll_rendered:
            scene.render.film_transparent = True
            image_settings.color_mode     = 'RGBA'
        else:
            scene.render.film_transparent = False
            image_settings.color_mode     = 'RGB'

        image_settings.file_format     = gd.format
        if gd.format == 'OPEN_EXR':
            image_settings.color_depth = gd.exr_depth
        elif gd.format != 'TARGA':
            image_settings.color_depth = gd.depth

        # Handle newly added object materials
        ob_amount = len(bpy.data.objects)
        if ob_amount > self.last_ob_amount and self.baker.node_tree:
            link_group_to_object(context.object, self.baker.node_tree)
        self.last_ob_amount = ob_amount

        # Exit check
        if not gd.preview_state \
        or (event.type in {'ESC'} and self.disable_binds) \
        or not is_scene_valid():
            self.cleanup(context)
            return {'CANCELLED'}
        return {'PASS_THROUGH'}

    def cleanup(self, context: Context) -> None:
        context.scene.gd.preview_state = False

        SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')

        self.baker.cleanup()
        if self.baker.node_tree:
            node_cleanup(self.baker.node_tree)
        baker_cleanup(context, self.saved_properties)

        for screens in self.original_workspace.screens:
            for area in screens.areas:
                if area.type != 'VIEW_3D':
                    continue
                for space in area.spaces:
                    space.shading.type = self.saved_render_view
                    break

        if self.user_preferences.exit_camera_preview and is_scene_valid():
            context.scene.camera = bpy.data.objects[Global.TRIM_CAMERA_NAME]
            bpy.ops.view3d.view_camera()

    def execute(self, context: Context):
        report_value, report_string = validate_scene(context, False)
        if report_value:
            self.report({'ERROR'}, report_string)
            return {'CANCELLED'}

        self.user_preferences = get_user_preferences()

        gd = context.scene.gd
        self.saved_properties = baker_setup(context)
        # TODO: Necessary to save?
        self.saved_properties['bpy.context.scene.gd.engine'] = gd.engine

        gd.preview_state    = True
        gd.preview_map_type = self.map_type
        gd.engine           = 'grabdoc'

        self.last_ob_amount = len(bpy.data.objects)
        self.disable_binds = not self.user_preferences.disable_preview_binds

        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        self.original_workspace = context.workspace
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    self.saved_render_view = space.shading.type
                    space.shading.type = 'RENDERED'
                    break

        context.scene.camera = bpy.data.objects[Global.TRIM_CAMERA_NAME]
        if not camera_in_3d_view():
            bpy.ops.view3d.view_camera()

        gd.preview_index = self.baker_index
        baker_prop = getattr(gd, self.map_type)
        self.baker = get_baker_by_index(baker_prop, self.baker_index)
        self.baker.setup()

        self.preview_name = self.map_type
        if self.baker.ID == 'custom':
            self.preview_name = self.baker.suffix.capitalize()
        self._handle = SpaceView3D.draw_handler_add(  # pylint: disable=E1120
            draw_callback_px, (self, context), 'WINDOW', 'POST_PIXEL'
        )
        context.window_manager.modal_handler_add(self)

        if self.baker.node_tree:
            for ob in get_rendered_objects():
                sockets = link_group_to_object(ob, self.baker.node_tree)
                sockets = self.baker.filter_required_sockets(sockets)
                if not sockets:
                    continue
                self.report(
                    {'WARNING'},
                    f"{ob.name}: {sockets} {Error.MISSING_SLOT_LINKS}"
                )
        return {'RUNNING_MODAL'}


class GRABDOC_OT_baker_preview_export(Operator):
    """Export the currently previewed material"""
    bl_idname  = "grabdoc.baker_export_preview"
    bl_label   = "Export Preview"
    bl_options = {'REGISTER'}

    baker_index: IntProperty()

    @classmethod
    def poll(cls, context: Context) -> bool:
        gd = context.scene.gd
        if gd.filepath == "//" and not bpy.data.filepath:
            cls.poll_message_set("Relative export path set but file not saved")
            return False
        return not GRABDOC_OT_baker_export_single.poll(context)

    def execute(self, context: Context):
        report_value, report_string = validate_scene(context)
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

        gd = context.scene.gd
        baker = getattr(gd, gd.preview_map_type)[self.baker_index]

        GRABDOC_OT_baker_export.export(context, baker.suffix)
        if baker.reimport:
            import_baker_textures([baker])

        if scale_plane:
            plane_ob.scale[0] = plane_ob.scale[1] = 1

        elapsed = round(time.time() - start, 2)
        self.report(
            {'INFO'}, f"{Error.EXPORT_COMPLETE} (execution time: {elapsed}s)"
        )
        return {'FINISHED'}


class GRABDOC_OT_baker_visibility(Operator):
    """Configure bake map UI visibility, will also disable baking"""
    bl_idname  = "grabdoc.baker_visibility"
    bl_label   = "Configure Baker Visibility"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return GRABDOC_OT_baker_export_single.poll(context)

    def execute(self, _context: Context):
        return {'FINISHED'}

    def invoke(self, context: Context, _event: Event):
        return context.window_manager.invoke_props_dialog(self, width=200)

    def draw(self, _context: Context):
        col = self.layout.column(align=True)
        for baker in get_bakers():
            icon = "BLENDER" if not baker.MARMOSET_COMPATIBLE else "WORLD"
            col.prop(baker, 'visibility', icon=icon,
                     text=f"{baker.NAME} {baker.index+1}")


class GRABDOC_OT_baker_pack(Operator):
    """Merge previously exported bake maps into single packed texture"""
    bl_idname  = "grabdoc.baker_pack"
    bl_label   = "Run Pack"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        gd = context.scene.gd
        r = get_channel_path(gd.channel_r)
        g = get_channel_path(gd.channel_g)
        b = get_channel_path(gd.channel_b)
        a = get_channel_path(gd.channel_a)
        if not all((r, g, b)):
            cls.poll_message_set("No bake maps exported yet")
            return False
        if gd.channel_a != 'none' and a is None:
            cls.poll_message_set("The A channel set but texture not exported")
            return False
        return True

    def execute(self, context: Context):
        gd = context.scene.gd
        pack_name = gd.filename + "_" + gd.pack_name
        path = gd.filepath

        # Loads all images into blender to avoid using a
        # separate python module to convert to np array
        image_r = bpy.data.images.load(get_channel_path(gd.channel_r))
        image_g = bpy.data.images.load(get_channel_path(gd.channel_g))
        image_b = bpy.data.images.load(get_channel_path(gd.channel_b))
        pack_order = [(image_r, (0, 0)),
                      (image_g, (0, 1)),
                      (image_b, (0, 2))]
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
            if gd.channel_a != 'none' and \
            os.path.exists(get_channel_path(gd.channel_a)):
                os.remove(get_channel_path(gd.channel_a))
        return {'FINISHED'}


################################################
# REGISTRATION
################################################


classes = (
    GRABDOC_OT_load_reference,
    GRABDOC_OT_open_folder,
    GRABDOC_OT_toggle_camera_view,
    GRABDOC_OT_scene_setup,
    GRABDOC_OT_scene_cleanup,
    GRABDOC_OT_baker_add,
    GRABDOC_OT_baker_remove,
    GRABDOC_OT_baker_export,
    GRABDOC_OT_baker_export_single,
    GRABDOC_OT_baker_preview,
    GRABDOC_OT_baker_preview_exit,
    GRABDOC_OT_baker_preview_export,
    GRABDOC_OT_baker_visibility,
    GRABDOC_OT_baker_pack
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
