import bpy, os
from bpy.types import Panel
from .preferences import GRABDOC_PT_presets
from .operators import proper_scene_setup


################################################################################################################
# UI
################################################################################################################


class PanelInfo:
    bl_category = 'GrabDoc'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'


class GRABDOC_PT_grabdoc(PanelInfo, Panel):
    bl_label = 'GrabDoc'

    def draw_header_preset(self, context):
        is_setup = proper_scene_setup()

        if is_setup:
            GRABDOC_PT_presets.draw_panel_header(self.layout)

    def draw(self, context):
        grabDoc = context.scene.grabDoc

        is_setup = proper_scene_setup()

        layout = self.layout

        col = layout.column(align = True)

        row = col.row(align = True)
        row.enabled = not grabDoc.modalState
        row.scale_y = 1.5
        row.operator("grab_doc.setup_scene", text = "Refresh Scene" if is_setup else "Setup Scene", icon = "TOOL_SETTINGS")

        if is_setup:
            row.operator("grab_doc.remove_setup", text = "", icon = "REMOVE")
            
            row = col.row(align = True)
            row.scale_y = .95

            row.prop(grabDoc, "collSelectable", text = "Selectable", icon = 'RESTRICT_SELECT_OFF' if grabDoc.collSelectable else 'RESTRICT_SELECT_ON')
            row.prop(grabDoc, "collVisible", text = "Visible", icon = 'HIDE_OFF' if grabDoc.collVisible else 'HIDE_ON')

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
        is_setup = proper_scene_setup()
        return is_setup

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
            row.operator("grab_doc.export_maps", text = 'Export Maps', icon = "EXPORT").offlineRenderType = 'online'
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
        row.prop(grabDoc, 'exportPath', text = "Export Path")
        row.operator("grab_doc.open_folder", text = '', icon = "FOLDER_REDIRECT")

        box.prop(grabDoc, "exportName", text = "Name")

        row = box.row()
        row.prop(grabDoc, "exportResX", text = 'Resolution')
        row.prop(grabDoc, "exportResY")
        row.prop(grabDoc, 'lockRes', icon_only = True, icon = "LOCKED" if grabDoc.lockRes else "UNLOCKED")

        row = box.row()
        row.prop(grabDoc, "imageType")

        row.separator(factor = .5)
        
        row2 = row.row()
        if grabDoc.imageType == "TARGA":
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
        col.prop(grabDoc, "onlyRenderColl", text = "Use Bake Collection", icon='CHECKBOX_HLT' if grabDoc.onlyRenderColl else 'CHECKBOX_DEHLT')
        col.prop(grabDoc, "exportPlane", text = 'Export Plane as FBX', icon='CHECKBOX_HLT' if grabDoc.exportPlane else 'CHECKBOX_DEHLT')
        col.prop(grabDoc, "openFolderOnExport", text = "Open Folder on Export", icon='CHECKBOX_HLT' if grabDoc.openFolderOnExport else 'CHECKBOX_DEHLT')

        if grabDoc.bakerType == 'Marmoset':
            col = box.column(align = True)
            col.prop(grabDoc, 'marmoAutoBake', text='Bake on Import', icon='CHECKBOX_HLT' if grabDoc.marmoAutoBake else 'CHECKBOX_DEHLT')
            col2 = col.column(align = True)
            if not grabDoc.marmoAutoBake:
                col2.active = False
            col2.prop(grabDoc, 'marmoClosePostBake', text='Close Toolbag after Baking', icon='CHECKBOX_HLT' if grabDoc.marmoClosePostBake else 'CHECKBOX_DEHLT')


class GRABDOC_OT_config_maps(bpy.types.Operator):
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


class GRABDOC_PT_view_edit_maps(PanelInfo, Panel):
    bl_label = 'Preview / Edit Maps'
    bl_parent_id = "GRABDOC_PT_grabdoc"
    
    @classmethod
    def poll(cls, context):
        is_setup = proper_scene_setup()
        return is_setup

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

            row = col.row(align = True)
            row.scale_y = 1.1
            row.operator("grab_doc.export_preview", text = f"Export {grabDoc.modalPreviewType.capitalize()}", icon = "EXPORT")

            layout = col.box()

            if grabDoc.modalPreviewType == 'normals':
                normals_ui(layout, self, context)

            elif grabDoc.modalPreviewType == 'curvature':
                curvature_ui(layout, self, context)

            elif grabDoc.modalPreviewType == 'occlusion':
                occlusion_ui(layout, self, context)

            elif grabDoc.modalPreviewType == 'height':
                height_ui(layout, self, context)

            elif grabDoc.modalPreviewType == 'ID':
                id_ui(layout, self, context)


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

        if grabDoc.firstBakePreview:
            row.operator("grab_doc.preview_warning", text = "Normals Preview").preview_type = 'normals'
        else:
            row.operator("grab_doc.preview_map", text = "Normals Preview").preview_type = 'normals'
        
        row.operator("grab_doc.export_maps", text = "", icon = "RENDER_STILL").offlineRenderType = 'normals'
        row.separator(factor = 1.3)

    def draw(self, context):
        normals_ui(self.layout, self, context)

def normals_ui(layout, self, context):
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
        
        if grabDoc.firstBakePreview:
            row.operator("grab_doc.preview_warning", text = "Curvature Preview").preview_type = 'curvature'
        else:
            row.operator("grab_doc.preview_map", text = "Curvature Preview").preview_type = 'curvature'

        row.operator("grab_doc.export_maps", text = "", icon = "RENDER_STILL").offlineRenderType = 'curvature'
        row.separator(factor = 1.3)

    def draw(self, context):
        curvature_ui(self.layout, self, context)

def curvature_ui(layout, self, context):
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
        col.separator()


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

        if grabDoc.firstBakePreview:
            row.operator("grab_doc.preview_warning", text = "Occlusion Preview").preview_type = 'occlusion'
        else:
            row.operator("grab_doc.preview_map", text = "Occlusion Preview").preview_type = 'occlusion'

        row.operator("grab_doc.export_maps", text = "", icon = "RENDER_STILL").offlineRenderType = 'occlusion'
        row.separator(factor = 1.3)

    def draw(self, context):
        occlusion_ui(self.layout, self, context)

def occlusion_ui(layout, self, context):
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

        if grabDoc.firstBakePreview:
            row.operator("grab_doc.preview_warning", text = "Height Preview").preview_type = 'height'
        else:
            row.operator("grab_doc.preview_map", text = "Height Preview").preview_type = 'height'

        row.operator("grab_doc.export_maps", text = "", icon = "RENDER_STILL").offlineRenderType = 'height'
        row.separator(factor = 1.3)

    def draw(self, context):
        height_ui(self.layout, self, context)

def height_ui(layout, self, context):
    grabDoc = context.scene.grabDoc

    layout.use_property_split = True
    layout.use_property_decorate = False

    col = layout.column()
    col.prop(grabDoc, 'flatMaskHeight', text = "Alpha Mask")
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
        col.prop(grabDoc, 'contrastOcclusion', text = "Contrast")


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
        
        if grabDoc.firstBakePreview:
            row.operator("grab_doc.preview_warning", text = "ID Preview").preview_type = 'ID'
        else:
            row.operator("grab_doc.preview_map", text = "ID Preview").preview_type = 'ID'

        row.operator("grab_doc.export_maps", text = "", icon = "RENDER_STILL").offlineRenderType = 'ID'
        row.separator(factor = 1.3)

    def draw(self, context):
        id_ui(self.layout, self, context)

def id_ui(layout, self, context):    
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
    GRABDOC_PT_id_settings
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
