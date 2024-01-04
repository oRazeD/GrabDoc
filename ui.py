import os

import bpy
from bpy.types import (
    Context,
    Panel,
    UILayout
)

from .constants import Global
from .preferences import GRABDOC_PT_presets
from .utils.generic import (
    PanelInfo,
    proper_scene_setup,
    is_camera_in_3d_view,
    format_bl_label,
    is_pro_version
)


################################################
# UI
################################################


class GRABDOC_PT_grabdoc(Panel, PanelInfo):
    bl_label = format_bl_label()

    def draw_header_preset(self, _context: Context):
        if proper_scene_setup():
            # NOTE: This method already has
            # self but the IDE trips on it
            # pylint: disable=no-value-for-parameter
            GRABDOC_PT_presets.draw_panel_header(self.layout)

    def draw(self, context: Context):
        gd = context.scene.gd

        layout = self.layout
        col = layout.column(align=True)

        row = col.row(align=True)
        row.enabled = not gd.preview_state
        row.scale_y = 1.5
        row.operator(
            "grab_doc.setup_scene",
            text="Refresh Scene" if proper_scene_setup() else "Setup Scene",
            icon="TOOL_SETTINGS"
        )

        if not proper_scene_setup():
            return

        row.scale_x = 1.1
        row.operator("grab_doc.remove_setup", text="", icon="CANCEL")

        row = col.row(align=True)
        row.scale_y = .95

        row.prop(
            gd, "coll_selectable",
            text="Select",
            icon='RESTRICT_SELECT_OFF' if gd.coll_selectable else 'RESTRICT_SELECT_ON'
        )
        row.prop(
            gd, "coll_visible",
            text="Visible",
            icon='RESTRICT_VIEW_OFF' if gd.coll_visible else 'RESTRICT_VIEW_ON'
        )
        row.prop(
            gd, "coll_rendered",
            text="Render",
            icon='RESTRICT_RENDER_OFF' if gd.coll_rendered else 'RESTRICT_RENDER_ON'
        )

        row = col.row(align=True)
        row.scale_y = 1.25
        in_trim_cam = is_camera_in_3d_view()
        row.operator(
            "grab_doc.view_cam",
            text="Leave Camera View" if in_trim_cam else "View GrabDoc Camera",
            icon="OUTLINER_OB_CAMERA"
        )

        box = col.box()
        box.use_property_split = True
        box.use_property_decorate = False

        col = box.column()
        col.prop(gd, "scale", text='Scaling', expand=True)
        col.separator(factor=.5)
        row = col.row()
        row.prop(gd, "filter_width", text="Filtering")
        row.separator()
        row.prop(gd, "filter", text="")

        col.separator()

        row = col.row()
        row.enabled = not gd.preview_state
        row.prop(gd, "reference", text='Reference')
        row.operator("grab_doc.load_reference", text="", icon='FILE_FOLDER')
        col.separator(factor=.5)
        row = col.row()
        row.prop(gd, "grid_subdivs", text="Grid")
        row.separator()
        row.prop(gd, "use_grid", text="")


class GRABDOC_PT_export(PanelInfo, Panel):
    bl_label = 'Export Maps'
    bl_parent_id = "GRABDOC_PT_grabdoc"

    @classmethod
    def poll(cls, _context: Context) -> bool:
        return proper_scene_setup()

    def marmo_header_layout(self, layout: UILayout):
        user_prefs = bpy.context.preferences.addons[__package__].preferences
        marmo_exe = user_prefs.marmo_exe

        col = layout.column(align=True)

        row = col.row()
        if not os.path.exists(marmo_exe):
            row.alignment = 'CENTER'
            row.label(text="Marmoset Toolbag Executable Required", icon='INFO')

            row = col.row()
            row.prop(user_prefs, 'marmo_exe', text="Toolbag Executable")

            col.separator()
        else:
            row.prop(user_prefs, 'marmo_exe', text="Toolbag Executable")

            row = col.row(align=True)
            row.scale_y = 1.5
            row.operator(
                "grab_doc.bake_marmoset",
                text="Bake in Marmoset",
                icon="EXPORT"
            ).send_type = 'open'
            row.operator(
                "grab_doc.bake_marmoset",
                text="",
                icon='FILE_REFRESH'
            ).send_type = 'refresh'

    def draw(self, context: Context):
        gd = context.scene.gd
        self.export_path_exists = \
            os.path.exists(bpy.path.abspath(gd.export_path))

        layout = self.layout
        layout.activate_init = True
        layout.use_property_split = True
        layout.use_property_decorate = False

        if is_pro_version() and gd.baker_type == 'marmoset':
            self.marmo_header_layout(layout)

        col = self.layout.column(align=True)

        row = col.row(align=True)
        row.scale_y = 1.5
        row.operator("grab_doc.export_maps", icon="EXPORT")

        box = col.box()
        col2 = box.column()
        if is_pro_version():
            row = col2.row()
            row.enabled = not gd.preview_state
            row.prop(gd, 'baker_type', text="Baker")
        col2.separator(factor=.5)

        row = col2.row()
        row.alert = not self.export_path_exists
        row.prop(gd, 'export_path', text="Export Path")
        row.alert = False
        row.operator("grab_doc.open_folder", text='', icon="FOLDER_REDIRECT")

        col2.separator(factor=.5)

        col2.prop(gd, "export_name", text="Name")

        col2.separator(factor=.5)

        row = col2.row()
        row.prop(gd, "resolution_x", text='Resolution')
        row.prop(gd, "resolution_y", text='')
        row.prop(
            gd,
            'lock_res',
            icon_only=True,
            icon="LOCKED" if gd.lock_res else "UNLOCKED"
        )

        col2.separator(factor=.5)

        if gd.baker_type == "marmoset":
            row = col2.row()
            row.prop(gd, "marmo_format")
        else:
            row = col2.row()
            row.prop(gd, "format")
            row.separator(factor=.5)
            row2 = row.row()

        # TODO: This is insane lol
        if gd.format == "OPEN_EXR":
            row2.prop(gd, "exr_depth", expand=True)
        elif gd.format != "TARGA" or gd.baker_type == 'marmoset':
            row2.prop(gd, "depth", expand=True)
        else:
            row2.enabled = False
            row2.prop(gd, "tga_depth", expand=True)
        col2.separator(factor=.5)
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

        box.use_property_split = False

        col = box.column(align=True)
        col.prop(
            gd, "use_bake_collections",
            text="Use Bake Collections",
            icon='CHECKBOX_HLT' if gd.use_bake_collections else 'CHECKBOX_DEHLT'
        )
        col.prop(
            gd, "export_plane",
            text='Export Plane',
            icon='CHECKBOX_HLT' if gd.export_plane else 'CHECKBOX_DEHLT'
        )

        if gd.baker_type == "marmoset":
            col = box.column(align=True)
            col.prop(
                gd,
                'marmo_auto_bake',
                text='Bake on Import',
                icon='CHECKBOX_HLT' if gd.marmo_auto_bake else 'CHECKBOX_DEHLT'
            )

            col = col.column(align=True)
            col.enabled = gd.marmo_auto_bake
            col.prop(
                gd,
                'marmo_auto_close',
                text='Close Toolbag after Baking',
                icon='CHECKBOX_HLT' if gd.marmo_auto_close else 'CHECKBOX_DEHLT'
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

        baker = getattr(gd, gd.preview_type)[0]

        col.separator()

        row = col.row(align=True)
        row.scale_y = 1.5
        row.operator("grab_doc.leave_modal", icon="CANCEL")

        row = col.row(align=True)
        row.scale_y = 1.1
        row.operator(
            "grab_doc.export_preview",
            text=f"Export {baker.NAME}",
            icon="EXPORT"
        )
        if gd.preview_type == Global.NORMAL_ID:
            GRABDOC_PT_normals.draw(self, context)
        elif gd.preview_type == Global.CURVATURE_ID:
            GRABDOC_PT_curvature.draw(self, context)
        elif gd.preview_type == Global.OCCLUSION_ID:
            GRABDOC_PT_occlusion.draw(self, context)
        elif gd.preview_type == Global.HEIGHT_ID:
            GRABDOC_PT_height.draw(self, context)
        elif gd.preview_type == Global.MATERIAL_ID:
            GRABDOC_PT_id.draw(self, context)
        elif gd.preview_type == Global.ALPHA_ID:
            GRABDOC_PT_alpha.draw(self, context)
        elif gd.preview_type == Global.COLOR_ID:
            GRABDOC_PT_color.draw(self, context)
        elif gd.preview_type == Global.EMISSIVE_ID:
            GRABDOC_PT_emissive.draw(self, context)
        elif gd.preview_type == Global.ROUGHNESS_ID:
            GRABDOC_PT_roughness.draw(self, context)
        elif gd.preview_type == Global.METALNESS_ID:
            GRABDOC_PT_metalness.draw(self, context)


#class GRABDOC_PT_pack_maps(PanelInfo, Panel):
#    bl_label = 'Pack Maps'
#    bl_parent_id = "GRABDOC_PT_grabdoc"

#    @classmethod
#    def poll(cls, context: Context) -> bool:
#        return proper_scene_setup() and not context.scene.gd.preview_state

#    def draw_header_preset(self, _context: Context):
#        self.layout.operator(
#            "grab_doc.map_pack_info",
#            emboss=False,
#            text="",
#            icon="HELP"
#        )

#    def draw_header(self, context: Context):
#        gd = context.scene.gd
#
#        row = self.layout.row(align=True)
#        row.prop(gd, '_use_pack_maps', text='')
#        row.separator(factor=.5)

#    def draw(self, context: Context):
#        gd = context.scene.gd

#        layout = self.layout
#        layout.use_property_split = True
#        layout.use_property_decorate = False

#        col = layout.column(align=True)
#        col.prop(gd, '_channel_R')
#        col.prop(gd, '_channel_G')
#        col.prop(gd, 'channel_B')
#        col.prop(gd, 'channel_A')


################################################
# BAKER UI
################################################


def warn_ui(layout):
    box = layout.box()
    box.scale_y = .6
    box.label(text='\u2022 Requires Shader Manipulation', icon='INFO')
    if is_pro_version():
        box.label(text='\u2022 No Marmoset Support', icon='BLANK1')


class BakerPanel(PanelInfo):  # , SubPanelInfo
    ID = None

    bl_parent_id = "GRABDOC_PT_view_edit_maps"
    bl_options = {'HEADER_LAYOUT_EXPAND', 'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        gd = context.scene.gd
        try:
            baker = getattr(gd, cls.NAME)[0]
        except AttributeError:
            return False
        return not gd.preview_state and baker.visibility

    def draw_header(self, context: Context):
        gd = context.scene.gd

        try:
            baker = getattr(gd, self.ID)[0]
        except AttributeError:
            return

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(baker, 'enabled', text="")
        row.operator(
            "grab_doc.preview_map",
            text=f"{self.ID} Preview"
        ).map_name = self.ID
        row.operator(
            "grab_doc.single_render",
            text="",
            icon="RENDER_STILL"
        ).map_name = self.ID
        row.separator(factor=1.3)

    @staticmethod
    def draw_baker_warnings(layout: UILayout):
        pass

    def draw_baker_properties(self, context: Context, layout: UILayout):
        pass

    def draw(self, context: Context):
        gd = context.scene.gd
        baker = getattr(gd, self.NAME)[0]

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        self.draw_baker_warnings(layout)
        col = layout.column()
        if len(baker.SUPPORTED_ENGINES) > 1:
            col.prop(baker, 'engine', text="Engine")
        baker.draw(context, layout)
        self.draw_baker_properties(context, layout)


class GRABDOC_PT_normals(BakerPanel, Panel):
    ID = Global.NORMAL_ID
    NAME = Global.NORMAL_NAME

    def draw_baker_properties(self, context: Context, layout: UILayout):
        gd = context.scene.gd
        baker = getattr(gd, self.NAME)[0]

        col = layout.column()
        col.prop(baker, 'flip_y', text="Flip Y (-Y)")

        if gd.baker_type == 'blender':
            col.separator(factor=.5)
            col.prop(baker, 'use_texture', text="Texture Normals")


class GRABDOC_PT_curvature(BakerPanel, Panel):
    ID = Global.CURVATURE_ID
    NAME = Global.CURVATURE_NAME

    def draw_baker_properties(self, context: Context, layout: UILayout):
        gd = context.scene.gd
        baker = getattr(gd, self.NAME)[0]

        if gd.baker_type != 'blender':
            return

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()
        col.prop(baker, 'ridge', text="Ridge")
        col.separator(factor=.5)
        col.prop(baker, 'valley', text="Valley")


class GRABDOC_PT_occlusion(BakerPanel, Panel):
    ID = Global.OCCLUSION_ID
    NAME = Global.OCCLUSION_NAME

    def draw_baker_properties(self, context: Context, layout: UILayout):
        gd = context.scene.gd
        baker = getattr(gd, self.NAME)[0]

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()

        if gd.baker_type == 'marmoset':
            col.prop(gd, "marmo_occlusion_ray_count", text="Ray Count")
            return

        col.prop(baker, 'gamma', text="Intensity")
        col.separator(factor=.5)
        col.prop(baker, 'distance', text="Distance")


class GRABDOC_PT_height(BakerPanel, Panel):
    ID = Global.HEIGHT_ID
    NAME = Global.HEIGHT_NAME

    def draw_baker_properties(self, context: Context, layout: UILayout):
        gd = context.scene.gd
        baker = getattr(gd, self.NAME)[0]

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()
        if gd.baker_type == 'blender':
            col.prop(baker, 'invert', text="Invert Mask")
            col.separator(factor=.5)

        row = col.row()
        row.prop(baker, 'method', text="Height Mode", expand=True)
        if baker.method == 'MANUAL':
            col.separator(factor=.5)
            col.prop(baker, 'distance', text="0-1 Range")


class GRABDOC_PT_id(BakerPanel, Panel):
    ID = Global.MATERIAL_ID
    NAME = Global.MATERIAL_NAME

    def draw_baker_properties(self, context: Context, layout: UILayout):
        gd = context.scene.gd
        baker = getattr(gd, self.NAME)[0]

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()
        row = col.row()
        if gd.baker_type == 'marmoset':
            row.enabled = False
            row.prop(baker, 'ui_method', text="ID Method")
        else:
            row.prop(baker, 'method', text="ID Method")

        if baker.method == "MATERIAL" or gd.baker_type == 'marmoset':
            col = layout.column(align=True)
            col.separator(factor=.5)
            col.scale_y = 1.1
            col.operator("grab_doc.quick_id_setup")

            row = col.row(align=True)
            row.scale_y = .9
            row.label(text=" Remove:")
            row.operator(
                "grab_doc.remove_mats_by_name",
                text='All'
            ).mat_name = Global.MAT_ID_RAND_PREFIX

            col = layout.column(align=True)
            col.separator(factor=.5)
            col.scale_y = 1.1
            col.operator("grab_doc.quick_id_selected")

            row = col.row(align=True)
            row.scale_y = .9
            row.label(text=" Remove:")
            row.operator(
                "grab_doc.remove_mats_by_name",
                text='All'
            ).mat_name = Global.MAT_ID_PREFIX
            row.operator("grab_doc.quick_remove_selected_mats",
                         text='Selected')


class GRABDOC_PT_alpha(BakerPanel, Panel):
    ID = Global.ALPHA_ID
    NAME = Global.ALPHA_NAME

    def draw_baker_properties(self, context: Context, layout: UILayout):
        gd = context.scene.gd
        baker = getattr(gd, self.NAME)[0]

        col = layout.column()
        if gd.baker_type == 'blender':
            col.prop(baker, 'invert', text="Invert Mask")


class GRABDOC_PT_color(BakerPanel):
    ID = Global.COLOR_ID
    NAME = Global.COLOR_NAME

    def draw_baker_properties(self, context: Context, layout: UILayout):
        warn_ui(layout)


class GRABDOC_PT_emissive(BakerPanel, Panel):
    ID = Global.EMISSIVE_ID
    NAME = Global.EMISSIVE_NAME

    def draw_baker_properties(self, context: Context, layout: UILayout):
        warn_ui(layout)


class GRABDOC_PT_roughness(BakerPanel, Panel):
    ID = Global.ROUGHNESS_ID
    NAME = Global.ROUGHNESS_NAME

    def draw_baker_properties(self, context: Context, layout: UILayout):
        gd = context.scene.gd
        baker = getattr(gd, self.NAME)[0]

        warn_ui(layout)

        col = layout.column()
        col.separator(factor=.5)
        if gd.baker_type == 'blender':
            col.prop(baker, 'invert', text="Invert")


class GRABDOC_PT_metalness(BakerPanel, Panel):
    ID = Global.METALNESS_ID
    NAME = Global.METALNESS_NAME

    def draw_baker_properties(self, context: Context, layout: UILayout):
        warn_ui(layout)


################################################
# REGISTRATION
################################################


classes = (
    GRABDOC_PT_grabdoc,
    GRABDOC_PT_export,
    GRABDOC_PT_view_edit_maps,
    # GRABDOC_PT_pack_maps
    GRABDOC_PT_normals,
    GRABDOC_PT_curvature,
    GRABDOC_PT_occlusion,
    GRABDOC_PT_height,
    GRABDOC_PT_id,
    GRABDOC_PT_alpha,
    GRABDOC_PT_color,
    GRABDOC_PT_emissive,
    GRABDOC_PT_roughness,
    GRABDOC_PT_metalness
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
