import bpy, os
from bpy.types import Panel
from .preferences import GRABDOC_PT_presets
from .generic_utils import proper_scene_setup


################################################################################################################
# UI
################################################################################################################


class PanelInfo:
    bl_category = 'GrabDoc'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'


class GRABDOC_OT_config_maps(bpy.types.Operator):
    """Configure the UI visibility of maps (also disables them from baking when hidden)"""
    bl_idname = "grab_doc.config_maps"
    bl_label = "Configure Map Visibility"
    bl_options = {'REGISTER'}
 
    def execute(self, context):
        return {'FINISHED'}
 
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width = 150)
 
    def draw(self, context):
        grabDoc = context.scene.grabDoc

        layout = self.layout
        layout.prop(grabDoc, 'uiVisibilityNormals', text = "Normals")
        layout.prop(grabDoc, 'uiVisibilityCurvature', text = "Curvature")
        layout.prop(grabDoc, 'uiVisibilityOcclusion', text = "Ambient Occlusion")
        layout.prop(grabDoc, 'uiVisibilityHeight', text = "Height")
        layout.prop(grabDoc, 'uiVisibilityMatID', text = "Material ID")
        layout.prop(grabDoc, 'uiVisibilityAlpha', text = "Alpha")


class GRABDOC_PT_grabdoc(PanelInfo, Panel):
    bl_label = 'GrabDoc Hub'

    def draw_header_preset(self, context):
        if proper_scene_setup():
            GRABDOC_PT_presets.draw_panel_header(self.layout)

    def draw(self, context):
        grabDoc = context.scene.grabDoc

        layout = self.layout

        col = layout.column(align = True)

        row = col.row(align = True)
        row.enabled = not grabDoc.modalState
        row.scale_y = 1.5
        row.operator("grab_doc.setup_scene", text = "Refresh Scene" if proper_scene_setup() else "Setup Scene", icon = "TOOL_SETTINGS")

        if proper_scene_setup():
            row.scale_x = 1.1
            row.operator("grab_doc.remove_setup", text = "", icon = "CANCEL")
            
            row = col.row(align = True)
            row.scale_y = .95

            row.prop(grabDoc, "collSelectable", text = "Select", icon = 'RESTRICT_SELECT_OFF' if grabDoc.collSelectable else 'RESTRICT_SELECT_ON')
            row.prop(grabDoc, "collVisible", text = "Visible", icon = 'HIDE_OFF' if grabDoc.collVisible else 'HIDE_ON')
            row.prop(grabDoc, "collRendered", text = "Render", icon = 'RESTRICT_RENDER_OFF' if grabDoc.collRendered else 'RESTRICT_RENDER_ON')

            box = col.box()
            box.use_property_split = True
            box.use_property_decorate = False

            row = box.row()
            row.prop(grabDoc, "scalingSet", text = 'Scaling', expand = True)

            row = box.row()
            row.enabled = not grabDoc.modalState
            row.prop(grabDoc, "refSelection", text = 'Reference')
            row.operator("grab_doc.load_ref", text = "", icon = 'FILE_FOLDER')

            row = box.row()
            row.prop(grabDoc, "gridSubdivisions", text = "Grid")
            row.separator()
            row.prop(grabDoc, "useGrid", text = "")


class GRABDOC_PT_export(PanelInfo, Panel):
    bl_label = 'Export Maps'
    bl_parent_id = "GRABDOC_PT_grabdoc"
    
    @classmethod
    def poll(cls, context):
        return proper_scene_setup()

    def draw(self, context):
        grabDoc = context.scene.grabDoc

        layout = self.layout
        layout.activate_init = True
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align=True)

        if grabDoc.bakerType == 'Blender':
            row = col.row(align=True)
            row.scale_y = 1.5
            row.operator("grab_doc.export_maps", icon = "EXPORT")
        else: # Marmoset
            row = col.row()
            if not os.path.exists(grabDoc.marmoEXE):
                row.alignment = 'CENTER'
                row.label(text="Give Marmoset Toolbag .exe Path", icon = 'INFO')

                row = col.row()
                row.prop(grabDoc, 'marmoEXE', text = 'Toolbag .exe')

                col.separator()
            else:
                row.prop(grabDoc, 'marmoEXE', text = "Toolbag .exe")

                row = col.row(align=True)
                row.scale_y = 1.5
                row.operator("grab_doc.bake_marmoset", text = "Bake in Marmoset" if grabDoc.marmoAutoBake else "Open in Marmoset", icon = "EXPORT").send_type = 'open'
                row.operator("grab_doc.bake_marmoset", text = "", icon = 'FILE_REFRESH').send_type = 'refresh'

        box = col.box()

        row = box.row()
        row.enabled = not grabDoc.modalState
        row.prop(grabDoc, 'bakerType', text = "Baker")

        row = box.row()
        row.alert = not os.path.exists(grabDoc.exportPath)
        row.prop(grabDoc, 'exportPath', text = "Export Path")
        row.alert = False
        row.operator("grab_doc.open_folder", text = '', icon = "FOLDER_REDIRECT")

        box.prop(grabDoc, "exportName", text = "Name")

        row = box.row()
        row.prop(grabDoc, "exportResX", text = 'Resolution')
        row.prop(grabDoc, "exportResY")
        row.prop(grabDoc, 'lockRes', icon_only = True, icon = "LOCKED" if grabDoc.lockRes else "UNLOCKED")

        row = box.row()
        if grabDoc.bakerType == 'Blender':
            row.prop(grabDoc, "imageType")
        else:
            row.prop(grabDoc, "imageType_marmo")

        row.separator(factor = .5)
        
        row2 = row.row()
        if grabDoc.imageType != "TARGA" or grabDoc.bakerType == 'Marmoset':
            row2.enabled = True
        else:
            row2.enabled = False
        
        row2.prop(grabDoc, "colorDepth", expand = True)

        if grabDoc.bakerType == 'Blender':
            if grabDoc.imageType != "TARGA":
                row = box.row(align = True)

                if grabDoc.imageType == "PNG":
                    row.prop(grabDoc, "imageComp", text = "Compression")
                else: # TIFF
                    row.prop(grabDoc, "imageCompTIFF", text = "Compression")
        else: # Marmoset
            row = box.row(align = True)
            row.prop(grabDoc, "marmoSamples", text = "Sampling", expand = True)

        box = col.box()
        box.use_property_split = False

        col = box.column(align = True)
        col.prop(grabDoc, "onlyRenderColl", text = "Use Bake Group", icon='CHECKBOX_HLT' if grabDoc.onlyRenderColl else 'CHECKBOX_DEHLT')
        col.prop(grabDoc, "exportPlane", text = 'Export Plane as FBX', icon='CHECKBOX_HLT' if grabDoc.exportPlane else 'CHECKBOX_DEHLT')
        col.prop(grabDoc, "openFolderOnExport", text = "Open Folder on Export", icon='CHECKBOX_HLT' if grabDoc.openFolderOnExport else 'CHECKBOX_DEHLT')

        if grabDoc.bakerType == 'Marmoset':
            col = box.column(align = True)
            col.prop(grabDoc, 'marmoAutoBake', text='Bake on Import', icon='CHECKBOX_HLT' if grabDoc.marmoAutoBake else 'CHECKBOX_DEHLT')

            col = col.column(align = True)
            col.enabled = True if grabDoc.marmoAutoBake else False
            col.prop(grabDoc, 'marmoClosePostBake', text='Close Toolbag after Baking', icon='CHECKBOX_HLT' if grabDoc.marmoClosePostBake else 'CHECKBOX_DEHLT')


class GRABDOC_PT_view_edit_maps(PanelInfo, Panel):
    bl_label = 'Preview / Edit Maps'
    bl_parent_id = "GRABDOC_PT_grabdoc"
    
    @classmethod
    def poll(cls, context):
        return proper_scene_setup()

    def draw_header_preset(self, context):
        self.layout.operator("grab_doc.config_maps", emboss = False, text = "", icon = "SETTINGS")

    def draw(self, context):
        grabDoc = context.scene.grabDoc

        layout = self.layout

        col = layout.column(align = True)

        row = col.row(align = True)
        row.scale_y = 1.25
        in_trim_cam = [area.spaces.active.region_3d.view_perspective for area in context.screen.areas if area.type == 'VIEW_3D'] == ['CAMERA']
        row.operator("grab_doc.view_cam", text = "Leave Trim Camera" if in_trim_cam else "View Trim Camera", icon = "OUTLINER_OB_CAMERA")

        col.prop(grabDoc, 'autoExitCamera', text = "Auto Switch on Exit", icon='CHECKBOX_HLT' if grabDoc.autoExitCamera else 'CHECKBOX_DEHLT')

        if grabDoc.modalState:
            col.separator()

            row = col.row(align = True)
            row.scale_y = 1.5
            row.operator("grab_doc.leave_modal", icon="CANCEL")

            # Special clause for Material ID preview
            if grabDoc.modalPreviewType != 'ID':
                mat_preview_type = grabDoc.modalPreviewType.capitalize()
            else:
                mat_preview_type = "Material ID"

            row = col.row(align = True)
            row.scale_y = 1.1
            row.operator("grab_doc.export_preview", text = f"Export {mat_preview_type}", icon = "EXPORT")

            layout = col.box()

            if grabDoc.modalPreviewType == 'normals':
                normals_ui(layout, context)

            elif grabDoc.modalPreviewType == 'curvature':
                curvature_ui(layout, context)

            elif grabDoc.modalPreviewType == 'occlusion':
                occlusion_ui(layout, context)

            elif grabDoc.modalPreviewType == 'height':
                height_ui(layout, context)

            elif grabDoc.modalPreviewType == 'alpha':
                alpha_ui(layout, context)

            elif grabDoc.modalPreviewType == 'ID':
                id_ui(layout, context)


class GRABDOC_PT_normals_settings(PanelInfo, Panel):
    bl_label = ''
    bl_parent_id = "GRABDOC_PT_view_edit_maps"
    bl_options = {'HEADER_LAYOUT_EXPAND', 'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return not context.scene.grabDoc.modalState and context.scene.grabDoc.uiVisibilityNormals

    def draw_header(self, context):
        grabDoc = context.scene.grabDoc

        row = self.layout.row(align = True)
        row.separator(factor = .5)
        row.prop(grabDoc, 'exportNormals', text = "")

        row.operator("grab_doc.preview_warning" if grabDoc.firstBakePreview else "grab_doc.preview_map", text = "Normals Preview").preview_type = 'normals'
        
        row.operator("grab_doc.offline_render", text = "", icon = "RENDER_STILL").render_type = 'normals'
        row.separator(factor = 1.3)

    def draw(self, context):
        normals_ui(self.layout, context)


def normals_ui(layout, context):
    grabDoc = context.scene.grabDoc

    layout.use_property_split = True
    layout.use_property_decorate = False

    col = layout.column()
    col.prop(grabDoc, 'flipYNormals', text = "Flip Y (-Y)")

    if grabDoc.bakerType == 'Blender':
        col.separator(factor=.5)
        col.prop(grabDoc, 'reimportAsMatNormals', text = "Import as Material")
        col.separator(factor=1.5)
        col.prop(grabDoc, "samplesNormals", text = 'Sampling')

    col.separator(factor=1.5)
    col.prop(grabDoc, 'normals_suffix', text = "Suffix")


class GRABDOC_PT_curvature_settings(PanelInfo, Panel):
    bl_label = ''
    bl_parent_id = "GRABDOC_PT_view_edit_maps"
    bl_options = {'HEADER_LAYOUT_EXPAND', 'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return not context.scene.grabDoc.modalState and context.scene.grabDoc.uiVisibilityCurvature

    def draw_header(self, context):
        grabDoc = context.scene.grabDoc

        row = self.layout.row(align = True)
        row.separator(factor = .5)
        row.prop(grabDoc, 'exportCurvature', text = "")
        
        row.operator("grab_doc.preview_warning" if grabDoc.firstBakePreview else "grab_doc.preview_map", text = "Curvature Preview").preview_type = 'curvature'

        row.operator("grab_doc.offline_render", text = "", icon = "RENDER_STILL").render_type = 'curvature'
        row.separator(factor = 1.3)

    def draw(self, context):
        curvature_ui(self.layout, context)


def curvature_ui(layout, context):
    grabDoc = context.scene.grabDoc

    layout.use_property_split = True
    layout.use_property_decorate = False

    col = layout.column()

    if grabDoc.bakerType == 'Blender':
        col.prop(grabDoc, 'ridgeCurvature', text = "Ridge")
        col.separator(factor=.5)
        col.prop(grabDoc, 'valleyCurvature', text = "Valley")
        col.separator(factor=1.5)
        col.prop(grabDoc, "samplesCurvature", text = "Sampling")
        col.separator(factor=.5)
        col.prop(grabDoc, 'contrastCurvature', text = "Contrast")
    else: # Marmoset
        pass
    
    col.separator(factor=1.5)
    col.prop(grabDoc, 'curvature_suffix', text = "Suffix")


class GRABDOC_PT_occlusion_settings(PanelInfo, Panel):
    bl_label = ''
    bl_parent_id = "GRABDOC_PT_view_edit_maps"
    bl_options = {'HEADER_LAYOUT_EXPAND', 'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return not context.scene.grabDoc.modalState and context.scene.grabDoc.uiVisibilityOcclusion

    def draw_header(self, context):
        grabDoc = context.scene.grabDoc

        row = self.layout.row(align = True)
        row.separator(factor = .5)
        row.prop(grabDoc, 'exportOcclusion', text = "")

        row.operator("grab_doc.preview_warning" if grabDoc.firstBakePreview else "grab_doc.preview_map", text = "Occlusion Preview").preview_type = 'occlusion'

        row.operator("grab_doc.offline_render", text = "", icon = "RENDER_STILL").render_type = 'occlusion'
        row.separator(factor = 1.3)

    def draw(self, context):
        occlusion_ui(self.layout, context)


def occlusion_ui(layout, context):
    grabDoc = context.scene.grabDoc

    layout.use_property_split = True
    layout.use_property_decorate = False

    col = layout.column()

    if grabDoc.bakerType == 'Marmoset':
        col.prop(grabDoc, "marmoAORayCount", text = "Ray Count")

    else: # Blender
        col.prop(grabDoc, 'reimportAsMatOcclusion', text = "Import as Material")

        col.separator(factor=.5)
        col.prop(grabDoc, 'gammaOcclusion', text = "Intensity")
        col.separator(factor=.5)
        col.prop(grabDoc, 'distanceOcclusion', text = "Distance")
        col.separator(factor=1.5)
        col.prop(grabDoc, "samplesOcclusion", text = "Samples")
        col.separator(factor=.5)
        col.prop(grabDoc, 'contrastOcclusion', text = "Contrast")

    col.separator(factor=1.5)
    col.prop(grabDoc, 'occlusion_suffix', text = "Suffix")


class GRABDOC_PT_height_settings(PanelInfo, Panel):
    bl_label = ''
    bl_parent_id = "GRABDOC_PT_view_edit_maps"
    bl_options = {'HEADER_LAYOUT_EXPAND', 'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return not context.scene.grabDoc.modalState and context.scene.grabDoc.uiVisibilityHeight

    def draw_header(self, context):
        grabDoc = context.scene.grabDoc

        row = self.layout.row(align = True)
        row.separator(factor = .5)
        row.prop(grabDoc, 'exportHeight', text = "")

        row.operator("grab_doc.preview_warning" if grabDoc.firstBakePreview else "grab_doc.preview_map", text = "Height Preview").preview_type = 'height'

        row.operator("grab_doc.offline_render", text = "", icon = "RENDER_STILL").render_type = 'height'
        row.separator(factor = 1.3)

    def draw(self, context):
        height_ui(self.layout, context)


def height_ui(layout, context):
    grabDoc = context.scene.grabDoc

    layout.use_property_split = True
    layout.use_property_decorate = False

    col = layout.column()
    
    if grabDoc.bakerType == 'Blender':
        col.prop(grabDoc, 'invertMaskHeight', text = "Invert Mask")
        col.separator(factor=.5)

    row = col.row()
    row.prop(grabDoc, "rangeTypeHeight", text = 'Height Mode', expand = True)

    if grabDoc.rangeTypeHeight == 'MANUAL':
        col.separator(factor=.5)
        col.prop(grabDoc, 'guideHeight', text = "0-1 Range")

    if grabDoc.bakerType == 'Blender':
        col.separator(factor=1.5)
        col.prop(grabDoc, "samplesHeight", text = "Samples")
        col.separator(factor=.5)
        col.prop(grabDoc, 'contrastHeight', text = "Contrast")
    
    col.separator(factor=1.5)
    col.prop(grabDoc, 'height_suffix', text = "Suffix")


class GRABDOC_PT_id_settings(PanelInfo, Panel):
    bl_label = ''
    bl_parent_id = "GRABDOC_PT_view_edit_maps"
    bl_options = {'HEADER_LAYOUT_EXPAND', 'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return not context.scene.grabDoc.modalState and context.scene.grabDoc.uiVisibilityMatID

    def draw_header(self, context):
        grabDoc = context.scene.grabDoc

        row = self.layout.row(align = True)
        row.separator(factor = .5)
        row.prop(grabDoc, 'exportMatID', text = "")
        
        row.operator("grab_doc.preview_warning" if grabDoc.firstBakePreview else "grab_doc.preview_map", text = "Mat ID Preview").preview_type = 'ID'

        row.operator("grab_doc.offline_render", text = "", icon = "RENDER_STILL").render_type = 'ID'
        row.separator(factor = 1.3)

    def draw(self, context):
        id_ui(self.layout, context)


def id_ui(layout, context):    
    grabDoc = context.scene.grabDoc

    layout.use_property_split = True
    layout.use_property_decorate = False

    col = layout.column()

    row = col.row()
    if grabDoc.bakerType == 'Marmoset':
        row.enabled = False
        row.prop(grabDoc, "fakeMethodMatID", text = "ID Method", expand = True)
    else:
        row.prop(grabDoc, "methodMatID", text = "ID Method", expand = True)

    if grabDoc.methodMatID == "MATERIAL" or grabDoc.bakerType == 'Marmoset':
        col = layout.column()
        col.separator(factor=.5)
        col.scale_y = 1.1
        col.operator("grab_doc.quick_id_setup")

        row = col.row(align = True)
        row.scale_y = .9
        row.label(text = " Remove:")
        row.operator("grab_doc.quick_remove_random_mats")

        col = layout.column()
        col.separator(factor=.5)
        col.scale_y = 1.1
        col.operator("grab_doc.quick_id_selected")

        row = col.row(align = True)
        row.scale_y = .9
        row.label(text = " Remove:")
        row.operator("grab_doc.quick_remove_manual_mats")
        row.operator("grab_doc.quick_remove_selected_mats")

    if grabDoc.bakerType == 'Blender':
        col.separator(factor=1.5)
        col.prop(grabDoc, "samplesMatID", text = "Samples")

    col.separator(factor=1.5)
    col.prop(grabDoc, 'id_suffix', text = "Suffix")


class GRABDOC_PT_alpha_settings(PanelInfo, Panel):
    bl_label = ''
    bl_parent_id = "GRABDOC_PT_view_edit_maps"
    bl_options = {'HEADER_LAYOUT_EXPAND', 'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return not context.scene.grabDoc.modalState and context.scene.grabDoc.uiVisibilityAlpha

    def draw_header(self, context):
        grabDoc = context.scene.grabDoc

        row = self.layout.row(align = True)
        row.separator(factor = .5)
        row.prop(grabDoc, 'exportAlpha', text = "")

        row.operator("grab_doc.preview_warning" if grabDoc.firstBakePreview else "grab_doc.preview_map", text = "Alpha Preview").preview_type = 'alpha'

        row.operator("grab_doc.offline_render", text = "", icon = "RENDER_STILL").render_type = 'alpha'
        row.separator(factor = 1.3)

    def draw(self, context):
        alpha_ui(self.layout, context)


def alpha_ui(layout, context):
    grabDoc = context.scene.grabDoc

    layout.use_property_split = True
    layout.use_property_decorate = False

    col = layout.column()
    
    if grabDoc.bakerType == 'Blender':
        col.prop(grabDoc, 'invertMaskAlpha', text = "Invert Mask")
        col.separator(factor=1.5)
        col.prop(grabDoc, 'samplesAlpha', text = "Samples")
    else: # Marmoset
        pass
    
    col.separator(factor=1.5)
    col.prop(grabDoc, 'alpha_suffix', text = "Suffix")


################################################################################################################
# REGISTRATION
################################################################################################################


classes = (
    GRABDOC_PT_grabdoc,
    GRABDOC_OT_config_maps,
    GRABDOC_PT_export,
    GRABDOC_PT_view_edit_maps,
    GRABDOC_PT_normals_settings,
    GRABDOC_PT_curvature_settings,
    GRABDOC_PT_occlusion_settings,
    GRABDOC_PT_height_settings,
    GRABDOC_PT_id_settings,
    GRABDOC_PT_alpha_settings
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
