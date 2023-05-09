import bpy, os, bpy.types as types

from .__init__ import bl_info
from .preferences import GRABDOC_PT_presets
from .generic_utils import (
    PanelInfo,
    SubPanelInfo,
    proper_scene_setup,
    is_camera_in_3d_view,
    format_bl_version,
    is_pro_version
)

from .constants import GlobalVariableConstants as GlobalVarConst


################################################################################################################
# UI
################################################################################################################


def warn_ui(layout):
    box = layout.box()
    box.scale_y = .6
    box.label(text='\u2022 Requires Shader Manipulation', icon='INFO')

    if is_pro_version():
        box.label(text='\u2022 No Marmoset Support', icon='BLANK1')


class GRABDOC_PT_grabdoc(PanelInfo, types.Panel):
    bl_label = f'{bl_info["name"]} {format_bl_version()}'

    def draw_header_preset(self, _context: types.Context):
        if proper_scene_setup():
            GRABDOC_PT_presets.draw_panel_header(self.layout)

    def draw(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        layout = self.layout
        col = layout.column(align=True)

        row = col.row(align=True)
        row.enabled = not grabDoc.modalState
        row.scale_y = 1.5
        row.operator("grab_doc.setup_scene", text="Refresh Scene" if proper_scene_setup() else "Setup Scene", icon="TOOL_SETTINGS")

        if not proper_scene_setup():
            return

        row.scale_x = 1.1
        row.operator("grab_doc.remove_setup", text="", icon="CANCEL")

        row = col.row(align=True)
        row.scale_y = .95

        row.prop(
            grabDoc, "collSelectable",
            text="Select",
            icon='RESTRICT_SELECT_OFF' if grabDoc.collSelectable else 'RESTRICT_SELECT_ON'
        )
        row.prop(
            grabDoc, "collVisible",
            text="Visible",
            icon='RESTRICT_VIEW_OFF' if grabDoc.collVisible else 'RESTRICT_VIEW_ON'
        )
        row.prop(
            grabDoc, "collRendered",
            text="Render",
            icon='RESTRICT_RENDER_OFF' if grabDoc.collRendered else 'RESTRICT_RENDER_ON'
        )

        box = col.box()
        box.use_property_split = True
        box.use_property_decorate = False

        col = box.column()
        col.prop(grabDoc, "scalingSet", text='Scaling', expand=True)
        col.separator(factor=.5)
        row = col.row()
        row.prop(grabDoc, "widthFiltering", text="Filtering")
        row.separator()
        row.prop(grabDoc, "useFiltering", text="")

        col.separator()

        row = col.row()
        row.enabled = not grabDoc.modalState
        row.prop(grabDoc, "refSelection", text='Reference')
        row.operator("grab_doc.load_ref", text="", icon='FILE_FOLDER')
        col.separator(factor=.5)
        row = col.row()
        row.prop(grabDoc, "gridSubdivisions", text="Grid")
        row.separator()
        row.prop(grabDoc, "useGrid", text="")


class GRABDOC_PT_export(PanelInfo, types.Panel):
    bl_label = 'Export Maps'
    bl_parent_id = "GRABDOC_PT_grabdoc"

    @classmethod
    def poll(cls, _context: types.Context) -> bool:
        return proper_scene_setup()

    def marmoset_export_header_ui(self, layout: types.UILayout):
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
            row.operator("grab_doc.bake_marmoset", text="", icon='FILE_REFRESH').send_type = 'refresh'

    def marmoset_ui(self, grabDoc, layout: types.UILayout):
        col = layout.column(align=True)

        box = col.box()
        col2 = box.column()

        row = col2.row()
        row.enabled = not grabDoc.modalState
        row.prop(grabDoc, 'bakerType', text="Baker")

        col2.separator(factor=.5)

        row = col2.row()
        row.alert = not self.export_path_exists
        row.prop(grabDoc, 'exportPath', text="Export Path")
        row.alert = False
        row.operator("grab_doc.open_folder", text='', icon="FOLDER_REDIRECT")

        col2.separator(factor=.5)

        col2.prop(grabDoc, "exportName", text="Name")

        col2.separator(factor=.5)

        row = col2.row()
        row.prop(grabDoc, "exportResX", text='Resolution')
        row.prop(grabDoc, "exportResY", text='')
        row.prop(grabDoc, 'lockRes', icon_only=True, icon="LOCKED" if grabDoc.lockRes else "UNLOCKED")

        col2.separator(factor=.5)

        row = col2.row()
        row.prop(grabDoc, "imageType_marmo")

        row.separator(factor=.5)

        row2 = row.row()
        if grabDoc.imageType == "OPEN_EXR":
            row2.prop(grabDoc, "colorDepthEXR", expand=True)
        elif grabDoc.imageType != "TARGA" or grabDoc.bakerType == 'Marmoset':
            row2.prop(grabDoc, "colorDepth", expand=True)
        else:
            row2.enabled = False
            row2.prop(grabDoc, "colorDepthTGA", expand=True)

        col2.separator(factor=.5)

        row = col2.row(align=True)
        row.prop(grabDoc, "marmoSamples", text="Samples", expand=True)

        box.use_property_split = False

        col = box.column(align=True)
        col.prop(
            grabDoc, "onlyRenderColl",
            text="Use Bake Group",
            icon='CHECKBOX_HLT' if grabDoc.onlyRenderColl else 'CHECKBOX_DEHLT'
        )
        col.prop(
            grabDoc, "exportPlane",
            text='Export Plane as FBX',
            icon='CHECKBOX_HLT' if grabDoc.exportPlane else 'CHECKBOX_DEHLT'
        )
        col.prop(
            grabDoc, "openFolderOnExport",
            text="Open Folder on Export",
            icon='CHECKBOX_HLT' if grabDoc.openFolderOnExport else 'CHECKBOX_DEHLT'
        )

        col = box.column(align=True)
        col.prop(grabDoc, 'marmoAutoBake', text='Bake on Import', icon='CHECKBOX_HLT' if grabDoc.marmoAutoBake else 'CHECKBOX_DEHLT')

        col = col.column(align=True)
        col.enabled = True if grabDoc.marmoAutoBake else False
        col.prop(
            grabDoc,
            'marmoClosePostBake',
            text='Close Toolbag after Baking',
            icon='CHECKBOX_HLT' if grabDoc.marmoClosePostBake else 'CHECKBOX_DEHLT'
        )

    def blender_ui(self, grabDoc, layout: types.UILayout):
        col = layout.column(align=True)

        row = col.row(align=True)
        row.scale_y = 1.5
        row.operator("grab_doc.export_maps", icon="EXPORT")

        box = col.box()
        col2 = box.column()

        if is_pro_version():
            row = col2.row()
            row.enabled = not grabDoc.modalState
            row.prop(grabDoc, 'bakerType', text="Baker")

        col2.separator(factor=.5)

        row = col2.row()
        row.alert = not self.export_path_exists
        row.prop(grabDoc, 'exportPath', text="Export Path")
        row.alert = False
        row.operator("grab_doc.open_folder", text='', icon="FOLDER_REDIRECT")

        col2.separator(factor=.5)

        col2.prop(grabDoc, "exportName", text="Name")

        col2.separator(factor=.5)

        row = col2.row()
        row.prop(grabDoc, "exportResX", text='Resolution')
        row.prop(grabDoc, "exportResY", text='')
        row.prop(grabDoc, 'lockRes', icon_only=True, icon="LOCKED" if grabDoc.lockRes else "UNLOCKED")

        col2.separator(factor=.5)

        row = col2.row()
        row.prop(grabDoc, "imageType")

        row.separator(factor=.5)

        row2 = row.row()
        if grabDoc.imageType == "OPEN_EXR":
            row2.prop(grabDoc, "colorDepthEXR", expand=True)
        elif grabDoc.imageType != "TARGA" or grabDoc.bakerType == 'Marmoset':
            row2.prop(grabDoc, "colorDepth", expand=True)
        else:
            row2.enabled = False
            row2.prop(grabDoc, "colorDepthTGA", expand=True)

        col2.separator(factor=.5)

        if grabDoc.imageType != "TARGA":
            image_settings = bpy.context.scene.render.image_settings

            row = col2.row(align=True)

            if grabDoc.imageType == "PNG":
                row.prop(grabDoc, "imageCompPNG", text="Compression")
            elif grabDoc.imageType == "OPEN_EXR":
                row.prop(image_settings, "exr_codec", text="Codec")
            else: # TIFF
                row.prop(image_settings, "tiff_codec", text="Codec")

        box.use_property_split = False

        col = box.column(align=True)
        col.prop(
            grabDoc, "onlyRenderColl",
            text="Use Bake Group",
            icon='CHECKBOX_HLT' if grabDoc.onlyRenderColl else 'CHECKBOX_DEHLT'
        )
        col.prop(
            grabDoc, "openFolderOnExport",
            text="Open Folder on Export",
            icon='CHECKBOX_HLT' if grabDoc.openFolderOnExport else 'CHECKBOX_DEHLT'
        )
        col.prop(
            grabDoc, "exportPlane",
            text='Export Plane as FBX',
            icon='CHECKBOX_HLT' if grabDoc.exportPlane else 'CHECKBOX_DEHLT'
        )

    def draw(self, context: types.Context):
        grabDoc = context.scene.grabDoc
        self.export_path_exists = os.path.exists(bpy.path.abspath(grabDoc.exportPath))

        layout = self.layout
        layout.activate_init = True
        layout.use_property_split = True
        layout.use_property_decorate = False

        if grabDoc.bakerType == 'Blender':
            self.blender_ui(grabDoc, layout)
        elif is_pro_version(): # Marmoset
            self.marmoset_export_header_ui(layout)
            self.marmoset_ui(grabDoc, layout)


class GRABDOC_OT_config_maps(types.Operator):
    """Configure the UI visibility of maps, also disabling them from baking when hidden"""
    bl_idname = "grab_doc.config_maps"
    bl_label = "Configure Map Visibility"
    bl_options = {'REGISTER'}

    def execute(self, _context):
        return {'FINISHED'} # NOTE Funky and neat

    def invoke(self, context: types.Context, _event: types.Event):
        return context.window_manager.invoke_props_dialog(self, width = 200)

    def draw(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        layout = self.layout
        layout.prop(grabDoc, 'uiVisibilityNormals', text="Normals")
        layout.prop(grabDoc, 'uiVisibilityCurvature', text="Curvature")
        layout.prop(grabDoc, 'uiVisibilityOcclusion', text="Ambient Occlusion")
        layout.prop(grabDoc, 'uiVisibilityHeight', text="Height")
        layout.prop(grabDoc, 'uiVisibilityMatID', text="Material ID")
        layout.prop(grabDoc, 'uiVisibilityAlpha', text="Alpha")
        layout.prop(grabDoc, 'uiVisibilityAlbedo', text="Albedo (Blender Only)")
        layout.prop(grabDoc, 'uiVisibilityRoughness', text="Roughness (Blender Only)")
        layout.prop(grabDoc, 'uiVisibilityMetalness', text="Metalness (Blender Only)")


class GRABDOC_PT_view_edit_maps(PanelInfo, types.Panel):
    bl_label = 'Edit Maps'
    bl_parent_id = "GRABDOC_PT_grabdoc"

    @classmethod
    def poll(cls, _context: types.Context) -> bool:
        return proper_scene_setup()

    def draw_header_preset(self, _context: types.Context):
        self.layout.operator("grab_doc.config_maps", emboss=False, text="", icon="SETTINGS")

    def draw(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        layout = self.layout
        col = layout.column(align=True)

        row = col.row(align=True)
        row.scale_y = 1.25
        in_trim_cam = is_camera_in_3d_view()
        row.operator("grab_doc.view_cam", text="Leave Camera View" if in_trim_cam else "View GrabDoc Camera", icon="OUTLINER_OB_CAMERA")

        col.prop(grabDoc, 'autoExitCamera', text="Leave Cam on Preview Exit", icon='CHECKBOX_HLT' if grabDoc.autoExitCamera else 'CHECKBOX_DEHLT')

        if not grabDoc.modalState:
            return

        col.separator()

        row = col.row(align=True)
        row.scale_y = 1.5
        row.operator("grab_doc.leave_modal", icon="CANCEL")

        row = col.row(align=True)
        row.scale_y = 1.1
        mat_preview_type = "Material ID" if grabDoc.modalPreviewType == 'ID' else grabDoc.modalPreviewType.capitalize()
        row.operator("grab_doc.export_preview", text = f"Export {mat_preview_type}", icon="EXPORT")

        if grabDoc.modalPreviewType == 'normals':
            GRABDOC_PT_normals_settings.draw(self, context)
        elif grabDoc.modalPreviewType == 'curvature':
            GRABDOC_PT_curvature_settings.draw(self, context)
        elif grabDoc.modalPreviewType == 'occlusion':
            GRABDOC_PT_occlusion_settings.draw(self, context)
        elif grabDoc.modalPreviewType == 'height':
            GRABDOC_PT_height_settings.draw(self, context)
        elif grabDoc.modalPreviewType == 'ID':
            GRABDOC_PT_id_settings.draw(self, context)
        elif grabDoc.modalPreviewType == 'alpha':
            GRABDOC_PT_alpha_settings.draw(self, context)
        elif grabDoc.modalPreviewType == 'albedo':
            GRABDOC_PT_albedo_settings.draw(self, context)
        elif grabDoc.modalPreviewType == 'roughness':
            GRABDOC_PT_roughness_settings.draw(self, context)
        elif grabDoc.modalPreviewType == 'metalness':
            GRABDOC_PT_metalness_settings.draw(self, context)


class GRABDOC_PT_pack_maps(PanelInfo, types.Panel):
    bl_label = 'Pack Maps'
    bl_parent_id = "GRABDOC_PT_grabdoc"

    @classmethod
    def poll(cls, context: types.Context) -> bool:
        return proper_scene_setup() and not context.scene.grabDoc.modalState

    def draw_header_preset(self, _context: types.Context):
        self.layout.operator("grab_doc.map_pack_info", emboss=False, text="", icon="HELP")

    def draw_header(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.prop(grabDoc, 'packMaps', text='')
        row.separator(factor=.5)

    def draw(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align=True)
        col.prop(grabDoc, 'mapType_R')
        col.prop(grabDoc, 'mapType_G')
        col.prop(grabDoc, 'mapType_B')
        col.prop(grabDoc, 'mapType_A')


class GRABDOC_PT_normals_settings(PanelInfo, SubPanelInfo, types.Panel):
    @classmethod
    def poll(cls, context: types.Context) -> bool:
        grabDoc = context.scene.grabDoc
        return not grabDoc.modalState and grabDoc.uiVisibilityNormals

    def draw_header(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(grabDoc, 'exportNormals', text="")

        row.operator(
            "grab_doc.preview_warning" if grabDoc.firstBakePreview else "grab_doc.preview_map",
            text="Normals Preview"
        ).map_types = 'normals'

        row.operator("grab_doc.offline_render", text="", icon="RENDER_STILL").map_types = 'normals'
        row.separator(factor=1.3)

    def draw(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()
        col.prop(grabDoc, "engineNormals", text="Engine")

        col = layout.column()
        col.prop(grabDoc, 'flipYNormals', text="Flip Y (-Y)")

        if grabDoc.bakerType == 'Blender':
            col.separator(factor=.5)
            col.prop(grabDoc, 'useTextureNormals', text="Texture Normals")
            col.separator(factor=.5)
            col.prop(grabDoc, 'reimportAsMatNormals', text="Import as Material")

            col.separator(factor=1.5)
            col.prop(
                grabDoc,
                "samplesNormals" if grabDoc.engineNormals == 'blender_eevee' else "samplesCyclesNormals",
                text='Samples'
            )

        col.separator(factor=.5)
        col.prop(grabDoc, 'suffixNormals', text="Suffix")


class GRABDOC_PT_curvature_settings(PanelInfo, SubPanelInfo, types.Panel):
    @classmethod
    def poll(cls, context: types.Context) -> bool:
        grabDoc = context.scene.grabDoc
        return not grabDoc.modalState and grabDoc.uiVisibilityCurvature

    def draw_header(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(grabDoc, 'exportCurvature', text="")

        row.operator(
            "grab_doc.preview_warning" if grabDoc.firstBakePreview else "grab_doc.preview_map",
            text="Curvature Preview"
        ).map_types = 'curvature'

        row.operator("grab_doc.offline_render", text="", icon="RENDER_STILL").map_types = 'curvature'
        row.separator(factor=1.3)

    def draw(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()

        if grabDoc.bakerType == 'Blender':
            col.prop(grabDoc, 'ridgeCurvature', text="Ridge")
            col.separator(factor=.5)
            col.prop(grabDoc, 'valleyCurvature', text="Valley")
            col.separator(factor=1.5)
            col.prop(grabDoc, "samplesCurvature", text="Samples")
            col.separator(factor=.5)
            col.prop(grabDoc, 'contrastCurvature', text="Contrast")

        col.separator(factor=.5)
        col.prop(grabDoc, 'suffixCurvature', text="Suffix")


class GRABDOC_PT_occlusion_settings(PanelInfo, SubPanelInfo, types.Panel):
    @classmethod
    def poll(cls, context: types.Context) -> bool:
        grabDoc = context.scene.grabDoc
        return not grabDoc.modalState and grabDoc.uiVisibilityOcclusion

    def draw_header(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(grabDoc, 'exportOcclusion', text="")

        row.operator(
            "grab_doc.preview_warning" if grabDoc.firstBakePreview else "grab_doc.preview_map",
            text="Occlusion Preview"
        ).map_types = 'occlusion'

        row.operator("grab_doc.offline_render", text="", icon="RENDER_STILL").map_types = 'occlusion'
        row.separator(factor=1.3)

    def draw(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()

        if grabDoc.bakerType == 'Marmoset':
            col.prop(grabDoc, "marmoAORayCount", text="Ray Count")

        else: # Blender
            col.prop(grabDoc, 'reimportAsMatOcclusion', text="Import as Material")

            col.separator(factor=.5)
            col.prop(grabDoc, 'gammaOcclusion', text="Intensity")
            col.separator(factor=.5)
            col.prop(grabDoc, 'distanceOcclusion', text="Distance")
            col.separator(factor=1.5)
            col.prop(grabDoc, "samplesOcclusion", text="Samples")
            col.separator(factor=.5)
            col.prop(grabDoc, 'contrastOcclusion', text="Contrast")

        col.separator(factor=.5)
        col.prop(grabDoc, 'suffixOcclusion', text="Suffix")


class GRABDOC_PT_height_settings(PanelInfo, SubPanelInfo, types.Panel):
    @classmethod
    def poll(cls, context: types.Context) -> bool:
        grabDoc = context.scene.grabDoc
        return not grabDoc.modalState and grabDoc.uiVisibilityHeight

    def draw_header(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(grabDoc, 'exportHeight', text="")

        row.operator(
            "grab_doc.preview_warning" if grabDoc.firstBakePreview else "grab_doc.preview_map",
            text="Height Preview"
        ).map_types = 'height'

        row.operator("grab_doc.offline_render", text="", icon="RENDER_STILL").map_types = 'height'
        row.separator(factor=1.3)

    def draw(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()

        if grabDoc.bakerType == 'Blender':
            col.prop(grabDoc, 'invertMaskHeight', text="Invert Mask")
            col.separator(factor=.5)

        row = col.row()
        row.prop(grabDoc, "rangeTypeHeight", text='Height Mode', expand=True)

        if grabDoc.rangeTypeHeight == 'MANUAL':
            col.separator(factor=.5)
            col.prop(grabDoc, 'guideHeight', text="0-1 Range")

        if grabDoc.bakerType == 'Blender':
            col.separator(factor=1.5)
            col.prop(grabDoc, "samplesHeight", text="Samples")
            col.separator(factor=.5)
            col.prop(grabDoc, 'contrastHeight', text="Contrast")

        col.separator(factor=.5)
        col.prop(grabDoc, 'suffixHeight', text="Suffix")


class GRABDOC_PT_id_settings(PanelInfo, SubPanelInfo, types.Panel):
    @classmethod
    def poll(cls, context: types.Context) -> bool:
        grabDoc = context.scene.grabDoc
        return not grabDoc.modalState and grabDoc.uiVisibilityMatID

    def draw_header(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(grabDoc, 'exportMatID', text="")

        row.operator(
            "grab_doc.preview_warning" if grabDoc.firstBakePreview else "grab_doc.preview_map",
            text="Mat ID Preview"
        ).map_types = 'ID'

        row.operator("grab_doc.offline_render", text="", icon="RENDER_STILL").map_types = 'ID'
        row.separator(factor=1.3)

    def draw(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()

        row = col.row()
        if grabDoc.bakerType == 'Marmoset':
            row.enabled = False
            row.prop(grabDoc, "fakeMethodMatID", text="ID Method")
        else:
            row.prop(grabDoc, "methodMatID", text="ID Method")

        if grabDoc.methodMatID == "MATERIAL" or grabDoc.bakerType == 'Marmoset':
            col = layout.column(align=True)
            col.separator(factor=.5)
            col.scale_y = 1.1
            col.operator("grab_doc.quick_id_setup")

            row = col.row(align=True)
            row.scale_y = .9
            row.label(text=" Remove:")
            row.operator("grab_doc.remove_mats_by_name", text='All').mat_name = GlobalVarConst.MAT_ID_RAND_PREFIX

            col = layout.column(align=True)
            col.separator(factor=.5)
            col.scale_y = 1.1
            col.operator("grab_doc.quick_id_selected")

            row = col.row(align=True)
            row.scale_y = .9
            row.label(text=" Remove:")
            row.operator("grab_doc.remove_mats_by_name", text='All').mat_name = GlobalVarConst.MAT_ID_PREFIX
            row.operator("grab_doc.quick_remove_selected_mats", text='Selected')

        if grabDoc.bakerType == 'Blender':
            col.separator(factor=1.5)
            col.prop(grabDoc, "samplesMatID", text="Samples")

        col.separator(factor=.5)
        col.prop(grabDoc, 'suffixID', text="Suffix")


class GRABDOC_PT_alpha_settings(PanelInfo, SubPanelInfo, types.Panel):
    @classmethod
    def poll(cls, context: types.Context) -> bool:
        grabDoc = context.scene.grabDoc
        return not grabDoc.modalState and grabDoc.uiVisibilityAlpha

    def draw_header(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(grabDoc, 'exportAlpha', text="")

        row.operator(
            "grab_doc.preview_warning" if grabDoc.firstBakePreview else "grab_doc.preview_map",
            text="Alpha Preview"
        ).map_types = 'alpha'

        row.operator("grab_doc.offline_render", text="", icon="RENDER_STILL").map_types = 'alpha'
        row.separator(factor=1.3)

    def draw(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()

        if grabDoc.bakerType == 'Blender':
            col.prop(grabDoc, 'invertMaskAlpha', text="Invert Mask")
            col.separator(factor=1.5)
            col.prop(grabDoc, 'samplesAlpha', text="Samples")

        col.separator(factor=.5)
        col.prop(grabDoc, 'suffixAlpha', text="Suffix")


class GRABDOC_PT_albedo_settings(PanelInfo, SubPanelInfo, types.Panel):
    @classmethod
    def poll(cls, context: types.Context) -> bool:
        grabDoc = context.scene.grabDoc
        return not grabDoc.modalState and grabDoc.uiVisibilityAlbedo and grabDoc.bakerType == 'Blender'

    def draw_header(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(grabDoc, 'exportAlbedo', text="")

        row.operator(
            "grab_doc.preview_warning" if grabDoc.firstBakePreview else "grab_doc.preview_map",
            text="Albedo Preview"
        ).map_types = 'albedo'

        row.operator("grab_doc.offline_render", text="", icon="RENDER_STILL").map_types = 'albedo'
        row.separator(factor=1.3)

    def draw(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        layout = self.layout

        warn_ui(layout)

        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()
        col.prop(grabDoc, "engineAlbedo", text="Engine")

        col.separator(factor=1.5)
        col.prop(
            grabDoc,
            "samplesAlbedo" if grabDoc.engineAlbedo == 'blender_eevee' else "samplesCyclesAlbedo",
            text='Samples'
        )

        col.separator(factor=.5)
        col.prop(grabDoc, 'suffixAlbedo', text="Suffix")


class GRABDOC_PT_roughness_settings(PanelInfo, SubPanelInfo, types.Panel):
    @classmethod
    def poll(cls, context: types.Context) -> bool:
        grabDoc = context.scene.grabDoc
        return not grabDoc.modalState and grabDoc.uiVisibilityRoughness and grabDoc.bakerType == 'Blender'

    def draw_header(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(grabDoc, 'exportRoughness', text="")

        row.operator(
            "grab_doc.preview_warning" if grabDoc.firstBakePreview else "grab_doc.preview_map",
            text="Roughness Preview"
        ).map_types = 'roughness'

        row.operator("grab_doc.offline_render", text="", icon="RENDER_STILL").map_types = 'roughness'
        row.separator(factor=1.3)

    def draw(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        layout = self.layout

        warn_ui(layout)

        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()
        col.prop(grabDoc, "engineRoughness", text="Engine")

        col.separator(factor=.5)
        if grabDoc.bakerType == 'Blender':
            col.prop(grabDoc, 'invertMaskRoughness', text="Invert")
            col.separator(factor=.5)

        col.separator(factor=1.5)
        col.prop(
            grabDoc,
            "samplesRoughness" if grabDoc.engineRoughness == 'blender_eevee' else "samplesCyclesRoughness",
            text='Samples'
        )

        col.separator(factor=.5)
        col.prop(grabDoc, 'suffixRoughness', text="Suffix")


class GRABDOC_PT_metalness_settings(PanelInfo, SubPanelInfo, types.Panel):
    @classmethod
    def poll(cls, context: types.Context) -> bool:
        grabDoc = context.scene.grabDoc
        return not grabDoc.modalState and grabDoc.uiVisibilityMetalness and grabDoc.bakerType == 'Blender'

    def draw_header(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        row = self.layout.row(align=True)
        row.separator(factor=.5)
        row.prop(grabDoc, 'exportMetalness', text="")

        row.operator(
            "grab_doc.preview_warning" if grabDoc.firstBakePreview else "grab_doc.preview_map",
            text="Metalness Preview"
        ).map_types = 'metalness'

        row.operator("grab_doc.offline_render", text="", icon="RENDER_STILL").map_types = 'metalness'
        row.separator(factor=1.3)

    def draw(self, context: types.Context):
        grabDoc = context.scene.grabDoc

        layout = self.layout

        warn_ui(layout)

        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()
        col.prop(grabDoc, "engineMetalness", text="Engine")

        col.separator(factor=1.5)
        col.prop(
            grabDoc,
            "samplesMetalness" if grabDoc.engineMetalness == 'blender_eevee' else "samplesCyclesMetalness",
            text='Samples'
        )

        col.separator(factor=.5)
        col.prop(grabDoc, 'suffixMetalness', text="Suffix")


################################################################################################################
# REGISTRATION
################################################################################################################


classes = (
    GRABDOC_PT_grabdoc,
    GRABDOC_OT_config_maps,
    GRABDOC_PT_export,
    GRABDOC_PT_view_edit_maps,
    GRABDOC_PT_pack_maps,
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
