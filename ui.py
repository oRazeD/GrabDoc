import os

import bpy
from bpy.types import (
    Context,
    Operator,
    Panel,
    UILayout,
    Event
)

from .preferences import GRABDOC_PT_presets
from .constants import GlobalVariableConstants as Global
from .utils.generic import (
    PanelInfo,
    SubPanelInfo,
    proper_scene_setup,
    is_camera_in_3d_view,
    format_bl_label,
    is_pro_version
)


################################################
# UI
################################################


def warn_ui(layout):
    box = layout.box()
    box.scale_y = .6
    box.label(text='\u2022 Requires Shader Manipulation', icon='INFO')

    if is_pro_version():
        box.label(text='\u2022 No Marmoset Support', icon='BLANK1')


class GRABDOC_PT_grabdoc(Panel, PanelInfo):
    bl_label = format_bl_label()

    def draw_header_preset(self, _context: Context):
        if proper_scene_setup():
            # NOTE: This method already has
            # self but the IDE trips on it
            GRABDOC_PT_presets.draw_panel_header(self.layout)

    def draw(self, context: Context):
        gd = context.scene.grabDoc

        layout = self.layout
        col = layout.column(align=True)

        row = col.row(align=True)
        row.enabled = not gd.modalState
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
            gd, "collSelectable",
            text="Select",
            icon='RESTRICT_SELECT_OFF' if gd.collSelectable else 'RESTRICT_SELECT_ON'
        )
        row.prop(
            gd, "collVisible",
            text="Visible",
            icon='RESTRICT_VIEW_OFF' if gd.collVisible else 'RESTRICT_VIEW_ON'
        )
        row.prop(
            gd, "collRendered",
            text="Render",
            icon='RESTRICT_RENDER_OFF' if gd.collRendered else 'RESTRICT_RENDER_ON'
        )

        box = col.box()
        box.use_property_split = True
        box.use_property_decorate = False

        col = box.column()
        col.prop(gd, "scalingSet", text='Scaling', expand=True)
        col.separator(factor=.5)
        row = col.row()
        row.prop(gd, "widthFiltering", text="Filtering")
        row.separator()
        row.prop(gd, "useFiltering", text="")

        col.separator()

        row = col.row()
        row.enabled = not gd.modalState
        row.prop(gd, "refSelection", text='Reference')
        row.operator("grab_doc.load_ref", text="", icon='FILE_FOLDER')
        col.separator(factor=.5)
        row = col.row()
        row.prop(gd, "gridSubdivisions", text="Grid")
        row.separator()
        row.prop(gd, "useGrid", text="")


class GRABDOC_PT_export(PanelInfo, Panel):
    bl_label = 'Export Maps'
    bl_parent_id = "GRABDOC_PT_grabdoc"

    @classmethod
    def poll(cls, _context: Context) -> bool:
        return proper_scene_setup()

    def marmoset_export_header_ui(self, layout: UILayout):
        user_prefs = bpy.context.preferences.addons[__package__].preferences
        marmo_exe = user_prefs.marmoEXE

        col = layout.column(align=True)

        row = col.row()
        if not os.path.exists(marmo_exe):
            row.alignment = 'CENTER'
            row.label(text="Give Marmoset Toolbag .exe Path", icon='INFO')

            row = col.row()
            row.prop(user_prefs, 'marmoEXE', text='Toolbag .exe')

            col.separator()
        else:
            row.prop(user_prefs, 'marmoEXE', text="Toolbag .exe")

            row = col.row(align=True)
            row.scale_y = 1.5
            row.operator(
                "grab_doc.bake_marmoset",
                text="Bake in Marmoset" if bpy.context.scene.grabDoc.marmoAutoBake else "Open in Marmoset",
                icon="EXPORT"
            ).send_type = 'open'
            row.operator(
                "grab_doc.bake_marmoset",
                text="",
                icon='FILE_REFRESH'
            ).send_type = 'refresh'

    def marmoset_ui(self, gd, layout: UILayout):
        col = layout.column(align=True)

        box = col.box()
        col2 = box.column()

        row = col2.row()
        row.enabled = not gd.modalState
        row.prop(gd, 'bakerType', text="Baker")

        col2.separator(factor=.5)

        row = col2.row()
        row.alert = not self.export_path_exists
        row.prop(gd, 'exportPath', text="Export Path")
        row.alert = False
        row.operator("grab_doc.open_folder", text='', icon="FOLDER_REDIRECT")

        col2.separator(factor=.5)

        col2.prop(gd, "exportName", text="Name")

        col2.separator(factor=.5)

        row = col2.row()
        row.prop(gd, "exportResX", text='Resolution')
        row.prop(gd, "exportResY", text='')
        row.prop(gd, 'lockRes', icon_only=True, icon="LOCKED" if gd.lockRes else "UNLOCKED")

        col2.separator(factor=.5)

        row = col2.row()
        row.prop(gd, "imageType_marmo")

        row.separator(factor=.5)

        row2 = row.row()
        if gd.imageType == "OPEN_EXR":
            row2.prop(gd, "colorDepthEXR", expand=True)
        elif gd.imageType != "TARGA" or gd.bakerType == 'Marmoset':
            row2.prop(gd, "colorDepth", expand=True)
        else:
            row2.enabled = False
            row2.prop(gd, "colorDepthTGA", expand=True)

        col2.separator(factor=.5)

        row = col2.row(align=True)
        row.prop(gd, "marmoSamples", text="Samples", expand=True)

        box.use_property_split = False

        col = box.column(align=True)
        col.prop(
            gd, "useBakeCollection",
            text="Use Bake Group",
            icon='CHECKBOX_HLT' if gd.useBakeCollection else 'CHECKBOX_DEHLT'
        )
        col.prop(
            gd, "exportPlane",
            text='Export Plane as FBX',
            icon='CHECKBOX_HLT' if gd.exportPlane else 'CHECKBOX_DEHLT'
        )
        col.prop(
            gd, "openFolderOnExport",
            text="Open Folder on Export",
            icon='CHECKBOX_HLT' if gd.openFolderOnExport else 'CHECKBOX_DEHLT'
        )

        col = box.column(align=True)
        col.prop(gd, 'marmoAutoBake', text='Bake on Import', icon='CHECKBOX_HLT' if gd.marmoAutoBake else 'CHECKBOX_DEHLT')

        col = col.column(align=True)
        col.enabled = True if gd.marmoAutoBake else False
        col.prop(
            gd,
            'marmoClosePostBake',
            text='Close Toolbag after Baking',
            icon='CHECKBOX_HLT' if gd.marmoClosePostBake else 'CHECKBOX_DEHLT'
        )

    def blender_ui(self, gd, layout: UILayout):
        col = layout.column(align=True)

        row = col.row(align=True)
        row.scale_y = 1.5
        row.operator("grab_doc.export_maps", icon="EXPORT")

        box = col.box()
        col2 = box.column()

        if is_pro_version():
            row = col2.row()
            row.enabled = not gd.modalState
            row.prop(gd, 'bakerType', text="Baker")

        col2.separator(factor=.5)

        row = col2.row()
        row.alert = not self.export_path_exists
        row.prop(gd, 'exportPath', text="Export Path")
        row.alert = False
        row.operator("grab_doc.open_folder", text='', icon="FOLDER_REDIRECT")

        col2.separator(factor=.5)

        col2.prop(gd, "exportName", text="Name")

        col2.separator(factor=.5)

        row = col2.row()
        row.prop(gd, "exportResX", text='Resolution')
        row.prop(gd, "exportResY", text='')
        row.prop(gd, 'lockRes', icon_only=True, icon="LOCKED" if gd.lockRes else "UNLOCKED")

        col2.separator(factor=.5)

        row = col2.row()
        row.prop(gd, "imageType")

        row.separator(factor=.5)

        row2 = row.row()
        if gd.imageType == "OPEN_EXR":
            row2.prop(gd, "colorDepthEXR", expand=True)
        elif gd.imageType != "TARGA" or gd.bakerType == 'Marmoset':
            row2.prop(gd, "colorDepth", expand=True)
        else:
            row2.enabled = False
            row2.prop(gd, "colorDepthTGA", expand=True)

        col2.separator(factor=.5)

        if gd.imageType != "TARGA":
            image_settings = bpy.context.scene.render.image_settings

            row = col2.row(align=True)

            if gd.imageType == "PNG":
                row.prop(gd, "imageCompPNG", text="Compression")
            elif gd.imageType == "OPEN_EXR":
                row.prop(image_settings, "exr_codec", text="Codec")
            else: # TIFF
                row.prop(image_settings, "tiff_codec", text="Codec")

        box.use_property_split = False

        col = box.column(align=True)
        col.prop(
            gd, "useBakeCollection",
            text="Use Bake Group",
            icon='CHECKBOX_HLT' if gd.useBakeCollection else 'CHECKBOX_DEHLT'
        )
        col.prop(
            gd, "openFolderOnExport",
            text="Open Folder on Export",
            icon='CHECKBOX_HLT' if gd.openFolderOnExport else 'CHECKBOX_DEHLT'
        )
        col.prop(
            gd, "exportPlane",
            text='Export Plane as FBX',
            icon='CHECKBOX_HLT' if gd.exportPlane else 'CHECKBOX_DEHLT'
        )

    def draw(self, context: Context):
        gd = context.scene.grabDoc
        self.export_path_exists = os.path.exists(bpy.path.abspath(gd.exportPath))

        layout = self.layout
        layout.activate_init = True
        layout.use_property_split = True
        layout.use_property_decorate = False

        if gd.bakerType == 'Blender':
            self.blender_ui(gd, layout)
        elif is_pro_version(): # Marmoset
            self.marmoset_export_header_ui(layout)
            self.marmoset_ui(gd, layout)


class GRABDOC_OT_config_maps(Operator):
    """Configure the UI visibility of maps, also disabling them from baking when hidden"""
    bl_idname = "grab_doc.config_maps"
    bl_label = "Configure Map Visibility"
    bl_options = {'REGISTER'}

    def execute(self, _context):
        return {'FINISHED'} # NOTE: Funky and neat

    def invoke(self, context: Context, _event: Event):
        return context.window_manager.invoke_props_dialog(self, width = 200)

    def draw(self, context: Context):
        gd = context.scene.grabDoc

        layout = self.layout
        layout.prop(gd, 'uiVisibilityNormals', text="Normals")
        layout.prop(gd, 'uiVisibilityCurvature', text="Curvature")
        layout.prop(gd, 'uiVisibilityOcclusion', text="Ambient Occlusion")
        layout.prop(gd, 'uiVisibilityHeight', text="Height")
        layout.prop(gd, 'uiVisibilityMatID', text="Material ID")
        layout.prop(gd, 'uiVisibilityAlpha', text="Alpha")
        layout.prop(gd, 'uiVisibilityAlbedo', text="Albedo (Blender Only)")
        layout.prop(gd, 'uiVisibilityRoughness', text="Roughness (Blender Only)")
        layout.prop(gd, 'uiVisibilityMetalness', text="Metalness (Blender Only)")


class GRABDOC_PT_view_edit_maps(PanelInfo, Panel):
    bl_label = 'Edit Maps'
    bl_parent_id = "GRABDOC_PT_grabdoc"

    @classmethod
    def poll(cls, _context: Context) -> bool:
        return proper_scene_setup()

    def draw_header_preset(self, _context: Context):
        self.layout.operator("grab_doc.config_maps", emboss=False, text="", icon="SETTINGS")

    def draw(self, context: Context):
        gd = context.scene.grabDoc

        layout = self.layout
        col = layout.column(align=True)

        row = col.row(align=True)
        row.scale_y = 1.25
        in_trim_cam = is_camera_in_3d_view()
        row.operator(
            "grab_doc.view_cam",
            text="Leave Camera View" if in_trim_cam else "View GrabDoc Camera",
            icon="OUTLINER_OB_CAMERA"
        )

        col.prop(
            gd,
            'autoExitCamera',
            text="Leave Cam on Preview Exit",
            icon='CHECKBOX_HLT' if gd.autoExitCamera else 'CHECKBOX_DEHLT'
        )

        if not gd.modalState:
            return

        col.separator()

        row = col.row(align=True)
        row.scale_y = 1.5
        row.operator("grab_doc.leave_modal", icon="CANCEL")

        row = col.row(align=True)
        row.scale_y = 1.1
        mat_preview_type = "Material ID" if gd.modalPreviewType == 'ID' else gd.modalPreviewType.capitalize()
        row.operator("grab_doc.export_preview", text = f"Export {mat_preview_type}", icon="EXPORT")

        if gd.modalPreviewType == 'normals':
            GRABDOC_PT_normals_settings.draw(self, context)
        elif gd.modalPreviewType == 'curvature':
            GRABDOC_PT_curvature_settings.draw(self, context)
        elif gd.modalPreviewType == 'occlusion':
            GRABDOC_PT_occlusion_settings.draw(self, context)
        elif gd.modalPreviewType == 'height':
            GRABDOC_PT_height_settings.draw(self, context)
        elif gd.modalPreviewType == 'ID':
            GRABDOC_PT_id_settings.draw(self, context)
        elif gd.modalPreviewType == 'alpha':
            GRABDOC_PT_alpha_settings.draw(self, context)
        elif gd.modalPreviewType == 'albedo':
            GRABDOC_PT_albedo_settings.draw(self, context)
        elif gd.modalPreviewType == 'roughness':
            GRABDOC_PT_roughness_settings.draw(self, context)
        elif gd.modalPreviewType == 'metalness':
            GRABDOC_PT_metalness_settings.draw(self, context)


#class GRABDOC_PT_pack_maps(PanelInfo, Panel):
#    bl_label = 'Pack Maps'
#    bl_parent_id = "GRABDOC_PT_grabdoc"

#    @classmethod
#    def poll(cls, context: Context) -> bool:
#        return proper_scene_setup() and not context.scene.grabDoc.modalState

#    def draw_header_preset(self, _context: Context):
#        self.layout.operator(
#            "grab_doc.map_pack_info",
#            emboss=False,
#            text="",
#            icon="HELP"
#        )

#    def draw_header(self, context: Context):
#        gd = context.scene.grabDoc
#
#        row = self.layout.row(align=True)
#        row.prop(gd, 'packMaps', text='')
#        row.separator(factor=.5)

#    def draw(self, context: Context):
#        gd = context.scene.grabDoc

#        layout = self.layout
#        layout.use_property_split = True
#        layout.use_property_decorate = False

#        col = layout.column(align=True)
#        col.prop(gd, 'channel_R')
#        col.prop(gd, 'channel_G')
#        col.prop(gd, 'channel_B')
#        col.prop(gd, 'channel_A')


class GRABDOC_PT_normals_settings(PanelInfo, SubPanelInfo, Panel):
    @classmethod
    def poll(cls, context: Context) -> bool:
        gd = context.scene.grabDoc
        return not gd.modalState and gd.uiVisibilityNormals

    def draw_header(self, context: Context):
        gd = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(gd, 'exportNormals', text="")

        row.operator(
            "grab_doc.preview_warning" if gd.firstBakePreview else "grab_doc.preview_map",
            text="Normals Preview"
        ).map_types = 'normals'

        row.operator(
            "grab_doc.offline_render",
            text="",
            icon="RENDER_STILL"
        ).map_types = 'normals'
        row.separator(factor=1.3)

    def draw(self, context: Context):
        gd = context.scene.grabDoc

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()
        col.prop(gd, "engineNormals", text="Engine")

        col = layout.column()
        col.prop(gd, 'flipYNormals', text="Flip Y (-Y)")

        if gd.bakerType == 'Blender':
            col.separator(factor=.5)
            col.prop(gd, 'useTextureNormals', text="Texture Normals")
            col.separator(factor=.5)
            col.prop(gd, 'reimportAsMatNormals', text="Import as Material")

            col.separator(factor=1.5)
            col.prop(
                gd,
                "samplesNormals" if gd.engineNormals == 'blender_eevee' else "samplesCyclesNormals",
                text='Samples'
            )

        col.separator(factor=.5)
        col.prop(gd, 'suffixNormals', text="Suffix")


class GRABDOC_PT_curvature_settings(PanelInfo, SubPanelInfo, Panel):
    @classmethod
    def poll(cls, context: Context) -> bool:
        gd = context.scene.grabDoc
        return not gd.modalState and gd.uiVisibilityCurvature

    def draw_header(self, context: Context):
        gd = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(gd, 'exportCurvature', text="")

        row.operator(
            "grab_doc.preview_warning" if gd.firstBakePreview else "grab_doc.preview_map",
            text="Curvature Preview"
        ).map_types = 'curvature'

        row.operator(
            "grab_doc.offline_render",
            text="",
            icon="RENDER_STILL"
        ).map_types = 'curvature'
        row.separator(factor=1.3)

    def draw(self, context: Context):
        gd = context.scene.grabDoc

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()

        if gd.bakerType == 'Blender':
            col.prop(gd, 'ridgeCurvature', text="Ridge")
            col.separator(factor=.5)
            col.prop(gd, 'valleyCurvature', text="Valley")
            col.separator(factor=1.5)
            col.prop(gd, "samplesCurvature", text="Samples")
            col.separator(factor=.5)
            col.prop(gd, 'contrastCurvature', text="Contrast")

        col.separator(factor=.5)
        col.prop(gd, 'suffixCurvature', text="Suffix")


class GRABDOC_PT_occlusion_settings(PanelInfo, SubPanelInfo, Panel):
    @classmethod
    def poll(cls, context: Context) -> bool:
        gd = context.scene.grabDoc
        return not gd.modalState and gd.uiVisibilityOcclusion

    def draw_header(self, context: Context):
        gd = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(gd, 'exportOcclusion', text="")

        row.operator(
            "grab_doc.preview_warning" if gd.firstBakePreview else "grab_doc.preview_map",
            text="Occlusion Preview"
        ).map_types = 'occlusion'

        row.operator(
            "grab_doc.offline_render",
            text="",
            icon="RENDER_STILL"
        ).map_types = 'occlusion'
        row.separator(factor=1.3)

    def draw(self, context: Context):
        gd = context.scene.grabDoc

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()

        if gd.bakerType == 'Marmoset':
            col.prop(gd, "marmoAORayCount", text="Ray Count")

        else: # Blender
            col.prop(gd, 'reimportAsMatOcclusion', text="Import as Material")

            col.separator(factor=.5)
            col.prop(gd, 'gammaOcclusion', text="Intensity")
            col.separator(factor=.5)
            col.prop(gd, 'distanceOcclusion', text="Distance")
            col.separator(factor=1.5)
            col.prop(gd, "samplesOcclusion", text="Samples")
            col.separator(factor=.5)
            col.prop(gd, 'contrastOcclusion', text="Contrast")

        col.separator(factor=.5)
        col.prop(gd, 'suffixOcclusion', text="Suffix")


class GRABDOC_PT_height_settings(PanelInfo, SubPanelInfo, Panel):
    @classmethod
    def poll(cls, context: Context) -> bool:
        gd = context.scene.grabDoc
        return not gd.modalState and gd.uiVisibilityHeight

    def draw_header(self, context: Context):
        gd = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(gd, 'exportHeight', text="")

        row.operator(
            "grab_doc.preview_warning" if gd.firstBakePreview else "grab_doc.preview_map",
            text="Height Preview"
        ).map_types = 'height'

        row.operator(
            "grab_doc.offline_render",
            text="",
            icon="RENDER_STILL"
        ).map_types = 'height'
        row.separator(factor=1.3)

    def draw(self, context: Context):
        gd = context.scene.grabDoc

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()

        if gd.bakerType == 'Blender':
            col.prop(gd, 'invertMaskHeight', text="Invert Mask")
            col.separator(factor=.5)

        row = col.row()
        row.prop(gd, "rangeTypeHeight", text='Height Mode', expand=True)

        if gd.rangeTypeHeight == 'MANUAL':
            col.separator(factor=.5)
            col.prop(gd, 'guideHeight', text="0-1 Range")

        if gd.bakerType == 'Blender':
            col.separator(factor=1.5)
            col.prop(gd, "samplesHeight", text="Samples")
            col.separator(factor=.5)
            col.prop(gd, 'contrastHeight', text="Contrast")

        col.separator(factor=.5)
        col.prop(gd, 'suffixHeight', text="Suffix")


class GRABDOC_PT_id_settings(PanelInfo, SubPanelInfo, Panel):
    @classmethod
    def poll(cls, context: Context) -> bool:
        gd = context.scene.grabDoc
        return not gd.modalState and gd.uiVisibilityMatID

    def draw_header(self, context: Context):
        gd = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(gd, 'exportMatID', text="")

        row.operator(
            "grab_doc.preview_warning" if gd.firstBakePreview else "grab_doc.preview_map",
            text="Mat ID Preview"
        ).map_types = 'ID'

        row.operator(
            "grab_doc.offline_render",
            text="",
            icon="RENDER_STILL"
        ).map_types = 'ID'
        row.separator(factor=1.3)

    def draw(self, context: Context):
        gd = context.scene.grabDoc

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()

        row = col.row()
        if gd.bakerType == 'Marmoset':
            row.enabled = False
            row.prop(gd, "fakeMethodMatID", text="ID Method")
        else:
            row.prop(gd, "methodMatID", text="ID Method")

        if gd.methodMatID == "MATERIAL" or gd.bakerType == 'Marmoset':
            col = layout.column(align=True)
            col.separator(factor=.5)
            col.scale_y = 1.1
            col.operator("grab_doc.quick_id_setup")

            row = col.row(align=True)
            row.scale_y = .9
            row.label(text=" Remove:")
            row.operator("grab_doc.remove_mats_by_name", text='All').mat_name = Global.MAT_ID_RAND_PREFIX

            col = layout.column(align=True)
            col.separator(factor=.5)
            col.scale_y = 1.1
            col.operator("grab_doc.quick_id_selected")

            row = col.row(align=True)
            row.scale_y = .9
            row.label(text=" Remove:")
            row.operator("grab_doc.remove_mats_by_name", text='All').mat_name = Global.MAT_ID_PREFIX
            row.operator("grab_doc.quick_remove_selected_mats", text='Selected')

        if gd.bakerType == 'Blender':
            col.separator(factor=1.5)
            col.prop(gd, "samplesMatID", text="Samples")

        col.separator(factor=.5)
        col.prop(gd, 'suffixID', text="Suffix")


class GRABDOC_PT_alpha_settings(PanelInfo, SubPanelInfo, Panel):
    @classmethod
    def poll(cls, context: Context) -> bool:
        gd = context.scene.grabDoc
        return not gd.modalState and gd.uiVisibilityAlpha

    def draw_header(self, context: Context):
        gd = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(gd, 'exportAlpha', text="")

        row.operator(
            "grab_doc.preview_warning" if gd.firstBakePreview else "grab_doc.preview_map",
            text="Alpha Preview"
        ).map_types = 'alpha'

        row.operator(
            "grab_doc.offline_render",
            text="",
            icon="RENDER_STILL"
        ).map_types = 'alpha'
        row.separator(factor=1.3)

    def draw(self, context: Context):
        gd = context.scene.grabDoc

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()

        if gd.bakerType == 'Blender':
            col.prop(gd, 'invertMaskAlpha', text="Invert Mask")
            col.separator(factor=1.5)
            col.prop(gd, 'samplesAlpha', text="Samples")

        col.separator(factor=.5)
        col.prop(gd, 'suffixAlpha', text="Suffix")


class GRABDOC_PT_albedo_settings(PanelInfo, SubPanelInfo, Panel):
    @classmethod
    def poll(cls, context: Context) -> bool:
        gd = context.scene.grabDoc
        return not gd.modalState and gd.uiVisibilityAlbedo and gd.bakerType == 'Blender'

    def draw_header(self, context: Context):
        gd = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(gd, 'exportAlbedo', text="")

        row.operator(
            "grab_doc.preview_warning" if gd.firstBakePreview else "grab_doc.preview_map",
            text="Albedo Preview"
        ).map_types = 'albedo'

        row.operator(
            "grab_doc.offline_render",
            text="",
            icon="RENDER_STILL"
        ).map_types = 'albedo'
        row.separator(factor=1.3)

    def draw(self, context: Context):
        gd = context.scene.grabDoc

        layout = self.layout

        warn_ui(layout)

        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()
        col.prop(gd, "engineAlbedo", text="Engine")

        col.separator(factor=1.5)
        col.prop(
            gd,
            "samplesAlbedo" if gd.engineAlbedo == 'blender_eevee' else "samplesCyclesAlbedo",
            text='Samples'
        )

        col.separator(factor=.5)
        col.prop(gd, 'suffixAlbedo', text="Suffix")


class GRABDOC_PT_roughness_settings(PanelInfo, SubPanelInfo, Panel):
    @classmethod
    def poll(cls, context: Context) -> bool:
        gd = context.scene.grabDoc
        return not gd.modalState and gd.uiVisibilityRoughness and gd.bakerType == 'Blender'

    def draw_header(self, context: Context):
        gd = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(gd, 'exportRoughness', text="")

        row.operator(
            "grab_doc.preview_warning" if gd.firstBakePreview else "grab_doc.preview_map",
            text="Roughness Preview"
        ).map_types = 'roughness'

        row.operator(
            "grab_doc.offline_render",
            text="",
            icon="RENDER_STILL"
        ).map_types = 'roughness'
        row.separator(factor=1.3)

    def draw(self, context: Context):
        gd = context.scene.grabDoc

        layout = self.layout

        warn_ui(layout)

        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()
        col.prop(gd, "engineRoughness", text="Engine")

        col.separator(factor=.5)
        if gd.bakerType == 'Blender':
            col.prop(gd, 'invertMaskRoughness', text="Invert")
            col.separator(factor=.5)

        col.separator(factor=1.5)
        col.prop(
            gd,
            "samplesRoughness" if gd.engineRoughness == 'blender_eevee' else "samplesCyclesRoughness",
            text='Samples'
        )

        col.separator(factor=.5)
        col.prop(gd, 'suffixRoughness', text="Suffix")


class GRABDOC_PT_metalness_settings(PanelInfo, SubPanelInfo, Panel):
    @classmethod
    def poll(cls, context: Context) -> bool:
        gd = context.scene.grabDoc
        return not gd.modalState and gd.uiVisibilityMetalness and gd.bakerType == 'Blender'

    def draw_header(self, context: Context):
        gd = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(gd, 'exportMetalness', text="")

        row.operator(
            "grab_doc.preview_warning" if gd.firstBakePreview else "grab_doc.preview_map",
            text="Metalness Preview"
        ).map_types = 'metalness'

        row.operator(
            "grab_doc.offline_render",
            text="",
            icon="RENDER_STILL"
        ).map_types = 'metalness'
        row.separator(factor=1.3)

    def draw(self, context: Context):
        gd = context.scene.grabDoc

        layout = self.layout

        warn_ui(layout)

        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()
        col.prop(gd, "engineMetalness", text="Engine")

        col.separator(factor=1.5)
        col.prop(
            gd,
            "samplesMetalness" if gd.engineMetalness == 'blender_eevee' else "samplesCyclesMetalness",
            text='Samples'
        )

        col.separator(factor=.5)
        col.prop(gd, 'suffixMetalness', text="Suffix")


################################################
# REGISTRATION
################################################


classes = (
    GRABDOC_PT_grabdoc,
    GRABDOC_OT_config_maps,
    GRABDOC_PT_export,
    GRABDOC_PT_view_edit_maps,
    #GRABDOC_PT_pack_maps,
    GRABDOC_PT_normals_settings,
    GRABDOC_PT_curvature_settings,
    GRABDOC_PT_occlusion_settings,
    GRABDOC_PT_height_settings,
    GRABDOC_PT_id_settings,
    GRABDOC_PT_alpha_settings,
    GRABDOC_PT_albedo_settings,
    GRABDOC_PT_roughness_settings,
    GRABDOC_PT_metalness_settings
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
