import bpy
from bpy.types import Panel, Menu
from bl_operators.presets import AddPresetBase
import os


class GRABDOC_MT_display_presets(Menu):
    bl_label = "Presets"
    preset_subdir = "grabdoc"
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


class GRABDOC_OT_add_preset(AddPresetBase, bpy.types.Operator):
    bl_idname = "grab_doc.preset_add"
    bl_label = "Add a new preset"
    preset_menu = "GRABDOC_MT_display_presets"

    # Variable used for all preset values
    preset_defines = ["scene = bpy.context.scene",
                      "grabDocPrefs = scene.grabDocPrefs"]

    # Properties to store in the preset
    preset_values = [
        "grabDocPrefs.collSelectable",
        "grabDocPrefs.collHidden",
        "grabDocPrefs.creatingGrid",
        "grabDocPrefs.creatingGridSubdivs",

        "grabDocPrefs.camHeight",
        "grabDocPrefs.scalingType",
        "grabDocPrefs.scalingSet",
        "grabDocPrefs.onlyRenderColl",

        "scene.grab_doc_filepath",
        "grabDocPrefs.exportName",
        "grabDocPrefs.exportResX",
        "grabDocPrefs.exportResY",
        "grabDocPrefs.lockRes",
        "grabDocPrefs.image_type",
        "grabDocPrefs.bitDepth",
        "scene.render.image_settings.compression",
        "scene.render.image_settings.tiff_codec",

        "grabDocPrefs.exportNormals",
        "grabDocPrefs.reimportAsMat",
        "grabDocPrefs.normalsFlipY",
        "grabDocPrefs.samplesNormals",

        "grabDocPrefs.exportCurvature",
        "grabDocPrefs.WSRidge",
        "grabDocPrefs.SSRidge",
        "grabDocPrefs.SSValley",
        "grabDocPrefs.colorCurvature",
        "grabDocPrefs.samplesCurvature",
        "grabDocPrefs.contrastCurvature",

        "grabDocPrefs.exportOcclusion",
        "grabDocPrefs.gammaOcclusion",
        "grabDocPrefs.distanceOcclusion",
        "grabDocPrefs.samplesOcclusion",
        "grabDocPrefs.contrastOcclusion",

        "grabDocPrefs.exportHeight",
        "grabDocPrefs.manualHeightRange",
        "grabDocPrefs.heightGuide",
        "grabDocPrefs.onlyFlatValues",
        "grabDocPrefs.samplesHeight",

        "grabDocPrefs.exportMatID",
        "grabDocPrefs.matID_method",
        "grabDocPrefs.samplesMatID",

        "grabDocPrefs.openFolderOnExport",
        
        "scene.marmoset_exe_filepath",
        "grabDocPrefs.autoBake",
        "grabDocPrefs.closeAfterBake",
        "grabDocPrefs.samplesMarmoset",
        "grabDocPrefs.aoRayCount"]

    # Where to store the preset
    preset_subdir = "grabdoc"


class PanelInfo:
    bl_category = 'GrabDoc'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'


class GRABDOC_PT_setup_ui(PanelInfo, Panel):
    bl_label = 'Scene Setup'

    @classmethod
    def poll(cls, context):
        addon_prefs = context.preferences.addons[__package__].preferences

        return(addon_prefs.showSceneUI_Pref)

    def draw(self, context):
        grabDocPrefs = context.scene.grabDocPrefs

        layout = self.layout

        for block in bpy.data.collections:
            if block.name == "GrabDoc (do not touch)":
                row = layout.row(align=True)
                row.menu(GRABDOC_MT_display_presets.__name__, text = GRABDOC_MT_display_presets.bl_label)
                row.scale_x = 1.25
                row.operator("grab_doc.preset_add", text="", icon='ADD')
                row.operator("grab_doc.preset_add", text="", icon='REMOVE').remove_active = True

                row = layout.row()
                box = layout.box()

                row = box.row()
                row.scale_y = 1.5
                row.operator("grab_doc.setup_scene", text = "Refresh Scene", icon = "TOOL_SETTINGS")

                col = row.column()
                col.scale_y = .55
                col.scale_x = .88
                col.prop(grabDocPrefs, "collSelectable", text = "", icon = 'RESTRICT_SELECT_OFF' if grabDocPrefs.collSelectable else 'RESTRICT_SELECT_ON', icon_only = True, emboss = False)
                col.prop(grabDocPrefs, "collHidden", text = "", icon = 'HIDE_ON' if grabDocPrefs.collHidden else 'HIDE_OFF', icon_only = True, emboss = False)

                split = box.split(factor=.275)
                col_left = split.column()
                col_right = split.column()
                col_left.label(text= "Ceiling:")
                rowCol = col_right.row()
                rowCol.prop(grabDocPrefs, "camHeight")

                split = box.split(factor=.275)
                col_left = split.column()
                col_right = split.column()
                col_left.label(text= "Scaling:")
                rowCol = col_right.row()
                rowCol.prop(grabDocPrefs, "scalingType", expand = True)
                if grabDocPrefs.scalingType == "scaling_set":
                    col_left.label(text = "")
                    col_right.prop(grabDocPrefs, "scalingSet", expand = True)

                split = box.split(factor=.275)
                col_left = split.column()
                col_right = split.column()
                col_left.prop(grabDocPrefs, "creatingGrid", text = "Grid:")
                rowCol = col_right.row()
                rowCol.active = grabDocPrefs.creatingGrid
                rowCol.prop(grabDocPrefs, "creatingGridSubdivs", text = "Subdivisions")

                row = box.row()
                row.prop(grabDocPrefs, "onlyRenderColl", text = "Manually pick rendered")
                break
        else:
            box = layout.box()
            row = box.row()
            row.scale_y = 1.5
            row.operator("grab_doc.setup_scene", text = "Setup Scene",icon = "TOOL_SETTINGS")


class GRABDOC_MT_setup_ui_info(Menu):
    bl_label = 'Info Tab'

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.label(text = "-- WARNINGS & INFO --")
        row = layout.row()
        row.separator()

        row = layout.row()

        row = layout.row()
        row.label(text = "    Map Preview mode is meant to give you an idea of what your exported maps should look")
        row = layout.row()
        row.label(text = "like. In most cases the preview will not be 100 percent accurate to the final exported result")
        row = layout.row()
        row.label(text = "and while there are info tags to let you know what to look out for, you should still use it as")
        row = layout.row()
        row.label(text = "more of a rough guideline. This is partly due to post-processing and some of the maps being")
        row = layout.row()
        row.label(text = "linked to screenspace.")

        row = layout.row()
        row.label(text = "")
        
        row = layout.row()
        row.label(text = "    This functionality is currently experimental, please avoid doing any actual work when")
        row = layout.row()
        row.label(text = "inside the mode as to prevent bugs. While there are many safeguards in place to resolve")
        row = layout.row()
        row.label(text = "possible issues, bugs can still happen. Any bugs should be fixable with a session restart,")
        row = layout.row()
        row.label(text = "if experienced please contact us so that we can get it patched in the next release.")


class GRABDOC_PT_ui(PanelInfo, Panel):
    bl_label = 'Baker'
    
    @classmethod
    def poll(cls, context):
        collectionExists = any(block.name == "GrabDoc (do not touch)" for block in bpy.data.collections)
        return(collectionExists)

    def draw(self, context):
        grabDocPrefs = context.scene.grabDocPrefs

        layout = self.layout   
        box = layout.box()

        row = box.row()
        row.scale_y = 1.5
        if not grabDocPrefs.modalState:
            row.operator("grab_doc.export_maps", icon = "EXPORT")
        else:
            row.operator("grab_doc.export_preview", text = f"Export {grabDocPrefs.preview_type}", icon = "EXPORT").preview_export_type = grabDocPrefs.preview_type

        split = box.split(factor=.275)
        col_left = split.column()
        col_right = split.column()
 
        col_left.label(text='Path:')

        row = col_right.row(align=True)
        row.prop(context.scene, 'grab_doc_filepath')
        row.operator("grab_doc.open_folder", text = "", icon = "FILE_PARENT")
        col_right.separator()

        col_left.separator()
        col_left.label(text='Name:')

        row2 = col_right.row(align=True)
        row2.prop(grabDocPrefs, "exportName")
        col_right.separator()

        col_left.separator()
        col_left.label(text='Res:')

        row3 = col_right.row(align=True)
        row3.prop(grabDocPrefs, "exportResX")
        row3.prop(grabDocPrefs, "exportResY")
        row3.separator(factor = .2)
        row3.prop(grabDocPrefs, 'lockRes', icon_only = True, emboss = False, icon = "LOCKED" if grabDocPrefs.lockRes else "UNLOCKED")
        col_right.separator()

        col_left.separator()
        col_left.label(text='Type:')

        row4 = col_right.row(align=True)
        row4.scale_x = .65
        row4.prop(grabDocPrefs, "image_type", text = "")
        row5 = row4.row()

        row5.scale_x = .7
        if grabDocPrefs.image_type == "TARGA":
            row5.enabled = False
        row5.prop(grabDocPrefs, "bitDepth", expand = True)

        if grabDocPrefs.image_type != "TARGA":
            col_right.separator()

            col_left.separator()
            col_left.label(text='Comp:')

            row2 = col_right.row(align=True)

            if grabDocPrefs.image_type == "PNG":
                row2.prop(context.scene.render.image_settings, "compression", text = "")
            else: # TIFF
                row2.prop(context.scene.render.image_settings, "tiff_codec", text = "")

        row5 = row4.row()
        row5 = box.row()
        row5.scale_x = 2
        row5.prop(grabDocPrefs, "openFolderOnExport", text = "Open folder on export")


class GRABDOC_PT_view_maps(PanelInfo, Panel):
    bl_label = 'View / Edit Maps'
    
    @classmethod
    def poll(cls, context):
        addon_prefs = context.preferences.addons[__package__].preferences

        collectionExists = any(block.name == "GrabDoc (do not touch)" for block in bpy.data.collections)
        return(addon_prefs.showViewEditUI_Pref and collectionExists)

    def draw(self, context):
        grabDocPrefs = context.scene.grabDocPrefs

        layout = self.layout

        box = layout.box()
        row3 = box.row()
        row3.scale_x = 2
        if [area.spaces.active.region_3d.view_perspective for area in context.screen.areas if area.type == 'VIEW_3D'] != ['CAMERA']:
            row3.operator("grab_doc.view_cam", icon = "OUTLINER_OB_CAMERA")
        else:
            row3.operator("grab_doc.view_cam", text = "Leave Trim Camera", icon = "OUTLINER_OB_CAMERA")

        row3.scale_x = .4
        row3.menu("GRABDOC_MT_setup_ui_info", text=" ", icon="INFO")

        box2 = layout.box()

        if grabDocPrefs.modalState:
            row = box2.row()
            row.scale_y = 1.5
            row.operator("grab_doc.leave_modal", icon = "CANCEL")

        else:
            row8 = box2.row(align = True)
            row8.prop(grabDocPrefs, 'dropdownNormals', icon_only = True, emboss = False, icon = "DOWNARROW_HLT" if grabDocPrefs.dropdownNormals else "RIGHTARROW")

        if grabDocPrefs.dropdownNormals and not grabDocPrefs.modalState or grabDocPrefs.preview_type == 'Normals':
            box2_in = box2.box()

            row = box2_in.row()
            row.alignment = 'RIGHT'
            row.prop(grabDocPrefs, 'reimportAsMat', text = "Import as mat")

            row = box2_in.row()
            row.alignment = 'RIGHT'
            row.prop(grabDocPrefs, 'normalsFlipY', text = "Flip Y (-Y)")

            box2_in = box2.box()

            row = box2_in.row()
            split = row.split(factor=.275)
            
            col_left = split.column()
            col_left.label(text="Sampling:")

            col_right = split.column()
            col_right_row = col_right.row()
            col_right_row.prop(grabDocPrefs, "samplesNormals", text = "")

        if not grabDocPrefs.modalState:
            row8.prop(grabDocPrefs, 'exportNormals', text = "")
            row8.operator("grab_doc.preview_map", text = "Normals").preview_type = 'Normals'
            row8.operator("grab_doc.export_maps", text = "", icon = "RENDER_STILL").renderer_type = 'Normals'

            row9 = box2.row(align = True)
            row9.prop(grabDocPrefs, 'dropdownCurvature', icon_only = True, emboss = False, icon = "DOWNARROW_HLT" if grabDocPrefs.dropdownCurvature else "RIGHTARROW")
        if grabDocPrefs.dropdownCurvature and not grabDocPrefs.modalState or grabDocPrefs.preview_type == 'Curvature':
            box2_in = box2.box()

            split = box2_in.split(factor=.275)

            col_left = split.column()
            col_left.label(text="WS Ridge:")

            col_right = split.column()
            col_right_row = col_right.row()
            col_right_row.prop(grabDocPrefs, 'WSRidge')

            split = box2_in.split(factor=.275)

            col_left = split.column()
            col_left.label(text="SS Ridge:")

            col_right = split.column()
            col_right_row = col_right.row()
            col_right_row.prop(grabDocPrefs, 'SSRidge')

            split = box2_in.split(factor=.275)

            col_left = split.column()
            col_left.label(text="SS Valley:")

            col_right = split.column()
            col_right_row = col_right.row()
            col_right_row.prop(grabDocPrefs, 'SSValley')

            split = box2_in.split(factor=.275)

            col_left = split.column()
            col_left.label(text="Color:")

            col_right = split.column()
            col_right_row = col_right.row()
            col_right_row.prop(grabDocPrefs, 'colorCurvature', text = "")

            box2_in = box2.box()

            split = box2_in.split(factor=.275)
            
            col_left = split.column()
            col_left.label(text="Sampling:")

            col_right = split.column()
            col_right_row = col_right.row()
            col_right_row.prop(grabDocPrefs, "samplesCurvature", text = "")

            split = box2_in.split(factor=.275)
            
            col_left = split.column()
            col_left.label(text="Contrast:")

            col_right = split.column()
            col_right_row = col_right.row()
            col_right_row.prop(grabDocPrefs, 'contrastCurvature', text = "")

            if grabDocPrefs.modalState:
                box3 = box2_in.box()
                row = box3.row()
                row.alignment = 'CENTER'
                row.label(text="White borders not visible in render", icon = 'INFO')

        if not grabDocPrefs.modalState:
            row9.prop(grabDocPrefs, 'exportCurvature', text = "")
            row9.operator("grab_doc.preview_map", text = "Curvature").preview_type = 'Curvature'
            row9.operator("grab_doc.export_maps", text = "", icon = "RENDER_STILL").renderer_type = 'Curvature'

            row10 = box2.row(align=True)
            row10.prop(grabDocPrefs, 'dropdownOcclusion', icon_only = True, emboss = False, icon = "DOWNARROW_HLT" if grabDocPrefs.dropdownOcclusion else "RIGHTARROW")
        if grabDocPrefs.dropdownOcclusion and not grabDocPrefs.modalState or grabDocPrefs.preview_type == 'Occlusion':
            box2_in = box2.box()

            split = box2_in.split(factor=.275)
            
            col_left = split.column()
            col_left.label(text="Intensity:")

            col_right = split.column()
            col_right.prop(grabDocPrefs, 'gammaOcclusion', text = "")

            split = box2_in.split(factor=.275)
            
            col_left = split.column()
            col_left.label(text="Distance:")

            col_right = split.column()
            col_right.prop(grabDocPrefs, 'distanceOcclusion', text = "")

            box2_in = box2.box()

            split = box2_in.split(factor=.275)
            
            col_left = split.column()
            col_left.label(text="Sampling:")

            col_right = split.column()
            col_right_row = col_right.row()
            col_right_row.prop(grabDocPrefs, "samplesOcclusion", text = "")

            split = box2_in.split(factor=.275)
            
            col_left = split.column()
            col_left.label(text="Contrast:")

            col_right = split.column()
            col_right_row = col_right.row()
            col_right_row.prop(grabDocPrefs, 'contrastOcclusion', text = "")

        if not grabDocPrefs.modalState:
            row10.prop(grabDocPrefs, 'exportOcclusion', text = "")
            row10.operator("grab_doc.preview_map", text = "Ambient Occlusion").preview_type = 'Occlusion'
            row10.operator("grab_doc.export_maps", text = "", icon = "RENDER_STILL").renderer_type = 'Occlusion'

            row11 = box2.row(align=True)
            row11.prop(grabDocPrefs, 'dropdownHeight', icon_only = True, emboss = False, icon = "DOWNARROW_HLT" if grabDocPrefs.dropdownHeight else "RIGHTARROW")
        if grabDocPrefs.dropdownHeight and not grabDocPrefs.modalState or grabDocPrefs.preview_type == 'Height':
            box2_in = box2.box()

            split = box2_in.split(factor=.275)
            
            col_left = split.column()
            col_left.label(text="0-1 Range:")

            col_right = split.column()
            col_right_row = col_right.row()
            col_right_row.prop(grabDocPrefs, "manualHeightRange", expand = True)
            if grabDocPrefs.manualHeightRange == 'MANUAL':
                col_right.prop(grabDocPrefs, 'heightGuide')

            row = box2_in.row()
            row.alignment = 'RIGHT'
            row.prop(grabDocPrefs, 'onlyFlatValues', text = "Flat mask")

            box2_in = box2.box()

            split = box2_in.split(factor=.275)
            
            col_left = split.column()
            col_left.label(text="Sampling:")

            col_right = split.column()
            col_right.prop(grabDocPrefs, "samplesHeight", text = "")

        if not grabDocPrefs.modalState:
            row11.prop(grabDocPrefs, 'exportHeight', text = "")
            row11.operator("grab_doc.preview_map", text = "Height").preview_type = 'Height'
            row11.operator("grab_doc.export_maps", text = "", icon = "RENDER_STILL").renderer_type = 'Height'
        
            row12 = box2.row(align=True)
            row12.prop(grabDocPrefs, 'dropdownMatID', icon_only = True, emboss = False, icon = "DOWNARROW_HLT" if grabDocPrefs.dropdownMatID else "RIGHTARROW")
        if grabDocPrefs.dropdownMatID and not grabDocPrefs.modalState or grabDocPrefs.preview_type == 'ID':
            box2_in = box2.box()

            split = box2_in.split(factor=.275)

            col_left = split.column()
            col_left.label(text="Method:")

            col_right = split.column()
            col_right_row = col_right.row()
            col_right_row.prop(grabDocPrefs, "matID_method", expand = True)
            if grabDocPrefs.matID_method == "MATERIAL":
                col_right_row = col_right.row(align = True)
                col_right_row.operator("grab_doc.quick_mat_setup")
                col_right_row.operator("grab_doc.quick_remove_mats", text = "", icon = 'CANCEL')

            box2_in = box2.box()

            split = box2_in.split(factor=.275)
            
            col_left = split.column()
            col_left.label(text="Sampling:")

            col_right = split.column()
            col_right_row = col_right.row()
            col_right_row.prop(grabDocPrefs, "samplesMatID", text = "")
        if not grabDocPrefs.modalState:
            row12.prop(grabDocPrefs, 'exportMatID', text = "")
            row12.operator("grab_doc.preview_map", text = "Material ID").preview_type = 'ID'
            row12.operator("grab_doc.export_maps", text = "", icon = "RENDER_STILL").renderer_type = 'ID'
        else:
            if grabDocPrefs.creatingGrid:
                row = box2_in.row()
                row.alignment = 'RIGHT'
                row.prop(grabDocPrefs, 'wirePreview')


class GRABDOC_PT_external_baking(PanelInfo, Panel):
    bl_label = 'Marmoset Baking'

    @classmethod
    def poll(cls, context):
        collectionExists = any(block.name == "GrabDoc (do not touch)" for block in bpy.data.collections)
        return(collectionExists and context.preferences.addons[__package__].preferences.showExternalBakeUI_Pref and not context.scene.grabDocPrefs.modalState)

    def draw(self, context):
        grabDocPrefs = context.scene.grabDocPrefs

        layout = self.layout
        box_marmo = layout.box()

        if not os.path.exists(context.scene.marmoset_exe_filepath):
            row_marmo = box_marmo.row()
            row_marmo.alignment = 'CENTER'
            row_marmo.label(text="Give path to the Marmoset .exe", icon = 'INFO')

            split_marmo = box_marmo.split(factor=.275)
            
            col_left = split_marmo.column()
            col_left.label(text=".exe path:")

            col_right = split_marmo.column()
            col_right_row = col_right.row()
            col_right_row.prop(context.scene, 'marmoset_exe_filepath')
        else:
            row_marmo = box_marmo.row(align = True)
            row_marmo.prop(grabDocPrefs, 'dropdownMarmoset', icon_only = True, emboss = False, icon = "DOWNARROW_HLT" if grabDocPrefs.dropdownMarmoset else "RIGHTARROW")
            row_marmo.separator(factor =.25)
            if grabDocPrefs.dropdownMarmoset:
                box_marmo_ins = box_marmo.box()

                row = box_marmo_ins.row()
                row.alignment = 'RIGHT'
                row.prop(grabDocPrefs, 'autoBake')

                row2 = row.row()
                row2.enabled = grabDocPrefs.autoBake
                row2.scale_x = .762
                row2.prop(grabDocPrefs, 'closeAfterBake')

                split_marmo = box_marmo_ins.split(factor=.275)

                col_left = split_marmo.column()
                col_left.label(text="Sampling:")

                col_right = split_marmo.column()
                col_right_row = col_right.row()
                col_right_row.prop(grabDocPrefs, "samplesMarmoset", text = "")

                split_marmo_2 = box_marmo_ins.split(factor=.275)

                col_left = split_marmo_2.column()
                col_left.label(text="AO Rays:")

                col_right = split_marmo_2.column()
                col_right_row = col_right.row()
                col_right_row.prop(grabDocPrefs, "aoRayCount", text = "")

                box_marmo_ins_2 = box_marmo.box()

                split_marmo_3 = box_marmo_ins_2.split(factor=.275)
                
                col_left = split_marmo_3.column()
                col_left.label(text=".exe path:")

                col_right = split_marmo_3.column()
                col_right_row = col_right.row()
                col_right_row.prop(context.scene, 'marmoset_exe_filepath')
            row_marmo.operator("grab_doc.bake_marmoset", text = "Bake in Marmoset" if grabDocPrefs.autoBake else "Open in Marmoset").send_type = 'open'
            row_marmo.operator("grab_doc.bake_marmoset", text = "", icon = 'FILE_REFRESH').send_type = 'refresh'


##############################
# REGISTRATION
##############################


classes = (GRABDOC_MT_display_presets,
           GRABDOC_OT_add_preset,
           GRABDOC_PT_setup_ui,
           GRABDOC_MT_setup_ui_info,
           GRABDOC_PT_ui,
           GRABDOC_PT_view_maps,
           GRABDOC_PT_external_baking)

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