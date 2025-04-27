import os

import bpy
from bpy.types import Context, Panel, UILayout, NodeTree

from .preferences import GRABDOC_PT_presets
from .utils.baker import get_baker_collections
from .utils.generic import get_version, get_user_preferences
from .utils.scene import camera_in_3d_view, is_scene_valid


class GDPanel(Panel):
    bl_category    = 'GrabDoc'
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label       = ""


class GRABDOC_PT_grabdoc(GDPanel):
    bl_label      = "GrabDoc " + get_version()
    documentation = "https://github.com/oRazeD/GrabDoc/wiki"

    def draw_header_preset(self, _context: Context):
        row = self.layout.row()
        if is_scene_valid():
            GRABDOC_PT_presets.draw_menu(row, text="Presets")
        row.operator(
            "wm.url_open", text="", icon='HELP'
        ).url = self.documentation
        row.separator(factor=.2)

    def draw(self, _context: Context):
        if is_scene_valid():
            return
        row = self.layout.row(align=True)
        row.scale_y = 1.5
        row.operator("grabdoc.scene_setup",
                     text="Setup Scene", icon='TOOL_SETTINGS')


class GRABDOC_PT_scene(GDPanel):
    bl_label     = 'Scene'
    bl_parent_id = "GRABDOC_PT_grabdoc"

    @classmethod
    def poll(cls, _context: Context) -> bool:
        return is_scene_valid()

    def draw_header(self, _context: Context):
        self.layout.label(icon='SCENE_DATA')

    def draw_header_preset(self, _context: Context):
        row2 = self.layout.row(align=True)
        row2.operator("grabdoc.toggle_camera_view",
                      text="Leave" if camera_in_3d_view() else "View",
                      icon="OUTLINER_OB_CAMERA")

    def draw(self, context: Context):
        gd = context.scene.gd
        layout = self.layout

        row = self.layout.row(align=True)
        row.scale_x = row.scale_y = 1.25
        row.operator("grabdoc.scene_setup",
                     text="Rebuild Scene", icon='FILE_REFRESH')
        row.operator("grabdoc.scene_cleanup", text="", icon="CANCEL")

        box = layout.box()
        row = box.row(align=True)
        row.scale_y = .9
        row.label(text="Camera Restrictions")
        row.prop(gd, "coll_selectable", text="", emboss=False,
    icon='RESTRICT_SELECT_OFF' if gd.coll_selectable else 'RESTRICT_SELECT_ON')
        row.prop(gd, "coll_visible", text="", emboss=False,
    icon='RESTRICT_VIEW_OFF' if gd.coll_visible else 'RESTRICT_VIEW_ON')
        row.prop(gd, "coll_rendered", text="", emboss=False,
    icon='RESTRICT_RENDER_OFF' if gd.coll_rendered else 'RESTRICT_RENDER_ON')

        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(gd, "scale", text='Scaling', expand=True)
        row = col.row()
        row.prop(gd, "grid_subdivs", text="Grid")
        row.separator()
        row.prop(gd, "use_grid", text="")
        row = col.row()
        row.enabled = not gd.preview_state
        row.prop(gd, "reference", text='Reference')
        row.operator("grabdoc.load_reference", text="", icon='FILE_FOLDER')


class GRABDOC_PT_output(GDPanel):
    bl_label     = 'Output'
    bl_parent_id = "GRABDOC_PT_grabdoc"

    @classmethod
    def poll(cls, _context: Context) -> bool:
        return is_scene_valid()

    def draw_header(self, _context: Context):
        self.layout.label(icon='OUTPUT')

    def draw_header_preset(self, context: Context):
        mt_executable = get_user_preferences().mt_executable
        if context.scene.gd.engine == 'marmoset' \
        and not os.path.exists(mt_executable):
            self.layout.enabled = False
        self.layout.scale_x = 1
        self.layout.operator("grabdoc.baker_export",
                             text="Export", icon="EXPORT")

    def mt_header_layout(self, layout: UILayout):
        preferences = get_user_preferences()
        mt_executable = preferences.mt_executable

        col = layout.column(align=True)
        row = col.row()
        if not os.path.exists(mt_executable):
            row.alignment = 'CENTER'
            row.label(text="Marmoset Toolbag Executable Required", icon='INFO')
            row = col.row()
            row.prop(preferences, 'mt_executable', text="Executable Path")
            return
        row.prop(preferences, 'mt_executable', text="Executable Path")
        row = col.row(align=True)
        row.scale_y = 1.25
        row.operator("grabdoc.bake_marmoset", text="Bake in Marmoset",
                     icon="EXPORT").send_type = 'open'
        row.operator("grabdoc.bake_marmoset",
                     text="", icon='FILE_REFRESH').send_type = 'refresh'

    def draw(self, context: Context):
        gd = context.scene.gd

        layout = self.layout
        layout.activate_init = True
        layout.use_property_split = True
        layout.use_property_decorate = False

        if gd.engine == 'marmoset':
            self.mt_header_layout(layout)

        col2 = layout.column()
        row = col2.row()
        row.prop(gd, 'engine')
        row = col2.row()
        row.prop(gd, 'filepath', text="Path")
        row.operator("grabdoc.open_folder",
                     text="", icon="FOLDER_REDIRECT")
        col2.prop(gd, "filename", text="Name")
        row = col2.row()
        row.prop(gd, "resolution_x", text='Resolution')
        row.prop(gd, "resolution_y", text='')
        row.prop(gd, 'resolution_lock', icon_only=True,
                 icon="LOCKED" if gd.resolution_lock else "UNLOCKED")

        row = col2.row()
        if gd.engine == "marmoset":
            image_format = "mt_format"
        else:
            image_format = "format"
        row.prop(gd, image_format)

        row2 = row.row()
        if gd.format == "OPEN_EXR":
            row2.prop(gd, "exr_depth", expand=True)
        elif gd.format != "TARGA" or gd.engine == 'marmoset':
            row2.prop(gd, "depth", expand=True)
        else:
            row2.enabled = False
            row2.prop(gd, "tga_depth", expand=True)
        if gd.format != "TARGA":
            image_settings = bpy.context.scene.render.image_settings
            row = col2.row(align=True)
            if gd.format == "PNG":
                row.prop(gd, "png_compression", text="Compression")
            elif gd.format == "OPEN_EXR":
                row.prop(image_settings, "exr_codec", text="Codec")
            else:  # TIFF
                row.prop(image_settings, "tiff_codec", text="Codec")

        row = col2.row()
        row.prop(gd, "filter_width", text="Filtering")
        row.separator()  # NOTE: Odd spacing without these
        row.prop(gd, "use_filtering", text="")

        if gd.engine == "marmoset":
            row = col2.row(align=True)
            row.prop(gd, "mt_samples", text="Samples", expand=True)

        col = layout.column(align=True)
        col.prop(gd, "use_bake_collection", text="Bake Groups")
        col.prop(gd, 'use_pack_maps')
        if gd.use_pack_maps:
            col.prop(gd, 'remove_original_maps')
        if gd.engine == "marmoset":
            col.prop(gd, 'mt_auto_bake', text='Bake on Import')
            row = col.row()
            row.enabled = gd.mt_auto_bake
            row.prop(gd, 'mt_auto_close', text='Close after Baking')


class GRABDOC_PT_bake_maps(GDPanel):
    bl_label     = 'Bake Maps'
    bl_parent_id = "GRABDOC_PT_grabdoc"

    @classmethod
    def poll(cls, _context: Context) -> bool:
        return is_scene_valid()

    def draw_header(self, _context: Context):
        self.layout.label(icon='SHADING_RENDERED')

    def draw_header_preset(self, _context: Context):
        self.layout.operator("grabdoc.baker_visibility",
                             emboss=False, text="", icon="SETTINGS")

    def draw(self, context: Context):
        gd = context.scene.gd
        if not gd.preview_state:
            return

        layout = self.layout
        col = layout.column(align=True)

        row = col.row(align=True)
        row.alert = True
        row.scale_y = 1.5
        row.operator("grabdoc.baker_preview_exit", icon="CANCEL")

        row = col.row(align=True)
        row.scale_y = 1.1
        baker = getattr(gd, gd.preview_map_type)[0]
        row.operator(
            "grabdoc.baker_export_preview",
            text=f"Export {baker.NAME}", icon="EXPORT"
        ).baker_index = baker.index
        baker.draw(context, layout)


class GRABDOC_PT_pack_maps(GDPanel):
    bl_label     = 'Pack Maps'
    bl_parent_id = "GRABDOC_PT_grabdoc"
    bl_options   = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        if context.scene.gd.preview_state:
            return False
        return is_scene_valid()

    def draw_header(self, _context: Context):
        self.layout.label(icon='RENDERLAYERS')

    # TODO: Idk if I like this from a UX persp anymore
    #def draw_header_preset(self, _context: Context):
    #    self.layout.scale_x = .9
    #    self.layout.operator("grabdoc.baker_pack")

    def draw(self, context: Context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        gd = context.scene.gd
        col = layout.column(align=True)
        col.prop(gd, 'channel_r')
        col.prop(gd, 'channel_g')
        col.prop(gd, 'channel_b')
        col.prop(gd, 'channel_a')
        col.prop(gd, 'pack_name', text="Suffix")


class GRABDOC_PT_Baker(GDPanel):
    bl_parent_id = "GRABDOC_PT_bake_maps"
    bl_options   = {'DEFAULT_CLOSED', 'HEADER_LAYOUT_EXPAND'}

    baker = None

    @classmethod
    def poll(cls, context: Context) -> bool:
        if cls.baker is None:
            return False
        return not context.scene.gd.preview_state and cls.baker.visibility

    def draw_header(self, _context: Context):
        row = self.layout.row(align=True)
        row2 = row.row(align=True)
        if self.baker.ID == 'custom' \
        and not isinstance(self.baker.node_tree, NodeTree):
            row2.enabled = False
        row2.separator(factor=.5)
        row2.prop(self.baker, 'enabled', text="")
        text = f"{self.baker.get_display_name()} Preview"
        preview = row2.operator("grabdoc.baker_preview", text=text)
        preview.map_type    = self.baker.ID
        preview.baker_index = self.baker.index
        row2.operator("grabdoc.baker_export_single",
                      text="", icon='RENDER_STILL').map_type = self.baker.ID

        if self.baker.index == 0:
            row.operator("grabdoc.baker_add",
                         text="", icon='ADD').map_type = self.baker.ID
            return
        remove = row.operator("grabdoc.baker_remove", text="", icon='TRASH')
        remove.map_type    = self.baker.ID
        remove.baker_index = self.baker.index

    def draw(self, context: Context):
        self.baker.draw(context, self.layout)


################################################
# REGISTRATION
################################################


def register_baker_panels():
    """Unregister and re-register all baker panels."""
    for cls in GRABDOC_PT_Baker.__subclasses__():
        try:
            bpy.utils.unregister_class(cls)
            classes.remove(cls)
        except RuntimeError:
            continue
    for cls in subclass_panels():
        bpy.utils.register_class(cls)
        classes.append(cls)

def subclass_panels():
    """Creates panels for every item in the baker
    `CollectionProperty`s via dynamic subclassing."""
    baker_classes = []
    for baker_prop in get_baker_collections():
        for baker in baker_prop:
            # NOTE: Old versions don't init correctly
            if bpy.app.version < (4, 4, 0):
                baker.__init__() # pylint: disable=C2801
            class_name = f"GRABDOC_PT_{baker.ID}_{baker.index}"
            panel_cls = type(class_name, (GRABDOC_PT_Baker,), {})
            panel_cls.baker = baker
            baker_classes.append(panel_cls)
    return baker_classes


classes = [
    GRABDOC_PT_grabdoc,
    GRABDOC_PT_scene,
    GRABDOC_PT_output,
    GRABDOC_PT_bake_maps,
    GRABDOC_PT_pack_maps
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
