import os

import bpy
from bpy.types import Context, Panel, UILayout

from .constants import Global
from .operators.operators import GRABDOC_OT_export_maps
from .preferences import GRABDOC_PT_presets
from .utils.generic import (
    PanelInfo,
    proper_scene_setup,
    camera_in_3d_view,
    get_version
)


################################################
# UI
################################################


class GRABDOC_PT_grabdoc(Panel, PanelInfo):
    bl_label = "GrabDoc " + get_version()

    def draw_header_preset(self, _context: Context):
        if proper_scene_setup():
            # NOTE: This method already has
            # self but the IDE trips on it
            # pylint: disable=no-value-for-parameter
            GRABDOC_PT_presets.draw_panel_header(self.layout)

    def draw(self, context: Context):
        gd = context.scene.gd

        layout = self.layout
        box = layout.box()
        scene_setup = proper_scene_setup()
        split = box.split(factor=.65 if scene_setup else .9)
        split.label(text="Scene Settings", icon="SCENE_DATA")
        if scene_setup:
            col = split.column(align=True)
            in_trim_cam = camera_in_3d_view()
            col.operator(
                "grab_doc.view_cam",
                text="Leave" if in_trim_cam else "View",
                icon="OUTLINER_OB_CAMERA"
            )
            col = box.column(align=True)
            col.label(text="Camera Restrictions")
            row = col.row(align=True)
            row.prop(
                gd, "coll_selectable", text="Select",
                icon='RESTRICT_SELECT_OFF' if gd.coll_selectable else 'RESTRICT_SELECT_ON'
            )
            row.prop(
                gd, "coll_visible", text="Visible",
                icon='RESTRICT_VIEW_OFF' if gd.coll_visible else 'RESTRICT_VIEW_ON'
            )
            row.prop(
                gd, "coll_rendered", text="Render",
                icon='RESTRICT_RENDER_OFF' if gd.coll_rendered else 'RESTRICT_RENDER_ON'
            )

        box.use_property_split = True
        box.use_property_decorate = False

        col = box.column(align=True)
        row = col.row(align=True)
        row.scale_x = 1.25
        row.scale_y = 1.25
        row.operator(
            "grab_doc.setup_scene",
            text="Rebuild Scene" if scene_setup else "Setup Scene",
            icon="FILE_REFRESH"
        )
        if not scene_setup:
            return

        row.operator("grab_doc.remove_setup", text="", icon="CANCEL")

        col = box.column()
        col.prop(gd, "scale", text='Scaling', expand=True)
        row = col.row()
        row.prop(gd, "filter_width", text="Filtering")
        row.separator() # NOTE: Odd spacing without these
        row.prop(gd, "filter", text="")
        row = col.row()
        row.prop(gd, "grid_subdivs", text="Grid")
        row.separator()
        row.prop(gd, "use_grid", text="")
        row = col.row()
        row.enabled = not gd.preview_state
        row.prop(gd, "reference", text='Reference')
        row.operator("grab_doc.load_reference", text="", icon='FILE_FOLDER')


class GRABDOC_PT_export(PanelInfo, Panel):
    bl_label = 'Export Maps'
    bl_parent_id = "GRABDOC_PT_grabdoc"

    @classmethod
    def poll(cls, _context: Context) -> bool:
        return proper_scene_setup()

    def draw_header_preset(self, context: Context):
        gd = context.scene.gd
        preferences = bpy.context.preferences.addons[__package__].preferences
        marmo_executable = preferences.marmo_executable

        layout = self.layout
        if gd.baker_type == 'marmoset' \
        and not os.path.exists(marmo_executable):
            layout.enabled = False
        layout.operator(
            "grab_doc.export_maps",
            text="Export", icon="EXPORT"
        )

    def marmo_header_layout(self, layout: UILayout):
        preferences = bpy.context.preferences.addons[__package__].preferences
        marmo_executable = preferences.marmo_executable

        col = layout.column(align=True)
        row = col.row()
        if not os.path.exists(marmo_executable):
            row.alignment = 'CENTER'
            row.label(text="Marmoset Toolbag Executable Required", icon='INFO')
            row = col.row()
            row.prop(preferences, 'marmo_executable', text="Executable Path")
            return
        row.prop(preferences, 'marmo_executable', text="Executable Path")
        row = col.row(align=True)
        row.scale_y = 1.25
        row.operator(
            "grab_doc.bake_marmoset",
            text="Bake in Marmoset", icon="EXPORT"
        ).send_type = 'open'
        row.operator(
            "grab_doc.bake_marmoset",
            text="", icon='FILE_REFRESH'
        ).send_type = 'refresh'

    def draw(self, context: Context):
        gd = context.scene.gd
        self.export_path_exists = \
            os.path.exists(bpy.path.abspath(gd.export_path))

        layout = self.layout
        layout.activate_init = True
        layout.use_property_split = True
        layout.use_property_decorate = False

        if gd.baker_type == 'marmoset':
            self.marmo_header_layout(layout)

        box = layout.box()
        box.label(text="Output Settings", icon="OUTPUT")

        col2 = box.column()
        #row = col2.row()
        #row.enabled = not gd.preview_state
        #row.prop(gd, 'baker_type', text="Baker")
        #col2.separator(factor=.5)

        row = col2.row()
        row.alert = not self.export_path_exists
        row.prop(gd, 'export_path', text="Path")
        row.alert = False
        row.operator(
            "grab_doc.open_folder",
            text="",
            icon="FOLDER_REDIRECT"
        )
        col2.prop(gd, "export_name", text="Name")
        row = col2.row()
        row.prop(gd, "resolution_x", text='Resolution')
        row.prop(gd, "resolution_y", text='')
        row.prop(
            gd, 'lock_res',
            icon_only=True,
            icon="LOCKED" if gd.lock_res else "UNLOCKED"
        )

        row = col2.row()
        if gd.baker_type == "marmoset":
            image_format = "marmo_format"
        else:
            image_format = "format"
        row.prop(gd, image_format)

        row2 = row.row()
        if gd.format == "OPEN_EXR":
            row2.prop(gd, "exr_depth", expand=True)
        elif gd.format != "TARGA" or gd.baker_type == 'marmoset':
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
            else: # TIFF
                row.prop(image_settings, "tiff_codec", text="Codec")

        if gd.baker_type == "marmoset":
            row = col2.row(align=True)
            row.prop(gd, "marmo_samples", text="Samples", expand=True)

        col = box.column(align=True)
        col.prop(
            gd, "use_bake_collections",
            text="Bake Groups"
        )
        col.prop(
            gd, "export_plane",
            text='Export Plane'
        )
        col.prop(gd, 'use_pack_maps')
        if gd.use_pack_maps:
            col.prop(gd, 'remove_original_maps')
        if gd.baker_type == "marmoset":
            col.prop(
                gd, 'marmo_auto_bake',
                text='Bake on Import'
            )
            row = col.row()
            row.enabled = gd.marmo_auto_bake
            row.prop(
                gd, 'marmo_auto_close',
                text='Close after Baking'
            )


class GRABDOC_PT_view_edit_maps(PanelInfo, Panel):
    bl_label = 'Edit Maps'
    bl_parent_id = "GRABDOC_PT_grabdoc"

    @classmethod
    def poll(cls, _context: Context) -> bool:
        return proper_scene_setup()

    def draw_header_preset(self, _context: Context):
        self.layout.operator(
            "grab_doc.config_maps",
            emboss=False,
            text="",
            icon="SETTINGS"
        )

    def draw(self, context: Context):
        gd = context.scene.gd

        layout = self.layout
        col = layout.column(align=True)

        if not gd.preview_state:
            return

        row = col.row(align=True)
        row.scale_y = 1.5
        row.operator("grab_doc.leave_modal", icon="CANCEL")

        row = col.row(align=True)
        row.scale_y = 1.1
        baker = getattr(gd, gd.preview_type)[0]
        row.operator(
            "grab_doc.export_preview",
            text=f"Export {baker.NAME}",
            icon="EXPORT"
        )
        baker.draw(context, layout)


class GRABDOC_PT_pack_maps(PanelInfo, Panel):
    bl_label = 'Pack Maps'
    bl_parent_id = "GRABDOC_PT_grabdoc"

    @classmethod
    def poll(cls, context: Context) -> bool:
        return proper_scene_setup() and GRABDOC_OT_export_maps.poll(context)

    def draw_header_preset(self, _context: Context):
        self.layout.operator("grab_doc.pack_maps", icon='IMAGE_DATA')

    def draw(self, context: Context):
        gd = context.scene.gd

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align=True)
        col.prop(gd, 'channel_r')
        col.prop(gd, 'channel_g')
        col.prop(gd, 'channel_b')
        col.prop(gd, 'channel_a')
        col.prop(gd, 'pack_name', text="Suffix")


################################################
# BAKER UI
################################################


class BakerPanel():
    ID = ""
    NAME = ""

    bl_parent_id = "GRABDOC_PT_view_edit_maps"
    bl_options = {'HEADER_LAYOUT_EXPAND', 'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        baker = getattr(context.scene.gd, cls.ID)[0]
        return not context.scene.gd.preview_state and baker.visibility

    def __init__(self):
        self.baker = getattr(bpy.context.scene.gd, self.ID)
        if self.baker is None:
            # TODO: Handle this in the future; usually
            # only happens in manually "broken" blend files
            return
        self.baker = self.baker[0]

    def draw_header(self, _context: Context):
        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(self.baker, 'enabled', text="")
        row.operator(
            "grab_doc.preview_map",
            text=f"{self.NAME} Preview"
        ).map_name = self.ID
        row.operator(
            "grab_doc.single_render",
            text="",
            icon="RENDER_STILL"
        ).map_name = self.ID
        row.separator(factor=1.3)

    def draw(self, context: Context):
        self.baker.draw(context, self.layout)


class GRABDOC_PT_color(BakerPanel, PanelInfo, Panel):
    ID = Global.COLOR_ID
    NAME = Global.COLOR_NAME

class GRABDOC_PT_normals(BakerPanel, PanelInfo, Panel):
    ID = Global.NORMAL_ID
    NAME = Global.NORMAL_NAME

class GRABDOC_PT_roughness(BakerPanel, PanelInfo, Panel):
    ID = Global.ROUGHNESS_ID
    NAME = Global.ROUGHNESS_NAME

class GRABDOC_PT_metallic(BakerPanel, PanelInfo, Panel):
    ID = Global.METALLIC_ID
    NAME = Global.METALLIC_NAME

class GRABDOC_PT_height(BakerPanel, PanelInfo, Panel):
    ID = Global.HEIGHT_ID
    NAME = Global.HEIGHT_NAME

class GRABDOC_PT_occlusion(BakerPanel, PanelInfo, Panel):
    ID = Global.OCCLUSION_ID
    NAME = Global.OCCLUSION_NAME

class GRABDOC_PT_emissive(BakerPanel, PanelInfo, Panel):
    ID = Global.EMISSIVE_ID
    NAME = Global.EMISSIVE_NAME

class GRABDOC_PT_curvature(BakerPanel, PanelInfo, Panel):
    ID = Global.CURVATURE_ID
    NAME = Global.CURVATURE_NAME

class GRABDOC_PT_id(BakerPanel, PanelInfo, Panel):
    ID = Global.MATERIAL_ID
    NAME = Global.MATERIAL_NAME

class GRABDOC_PT_alpha(BakerPanel, PanelInfo, Panel):
    ID = Global.ALPHA_ID
    NAME = Global.ALPHA_NAME


################################################
# REGISTRATION
################################################


classes = (
    GRABDOC_PT_grabdoc,
    GRABDOC_PT_export,
    GRABDOC_PT_view_edit_maps,
    GRABDOC_PT_pack_maps,
    GRABDOC_PT_color,
    GRABDOC_PT_normals,
    GRABDOC_PT_roughness,
    GRABDOC_PT_metallic,
    GRABDOC_PT_height,
    GRABDOC_PT_occlusion,
    GRABDOC_PT_curvature,
    GRABDOC_PT_emissive,
    GRABDOC_PT_id,
    GRABDOC_PT_alpha,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
