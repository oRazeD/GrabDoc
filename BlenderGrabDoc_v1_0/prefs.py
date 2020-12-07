import bpy
from bpy.props import BoolProperty, EnumProperty
from bpy.types import AddonPreferences, PropertyGroup
import os
import bpy.utils.previews
from .operators import scene_refresh, get_rendered_objects, find_tallest_object
from bpy.props import BoolProperty, PointerProperty, StringProperty, EnumProperty, IntProperty, FloatProperty, FloatVectorProperty


############################################################
# USER PREFERENCES
############################################################


class PIESPLUS_MT_addon_prefs(AddonPreferences):
    bl_idname = __package__

    Tabs: EnumProperty(items=(('info', "Information", "Information about the addon"),
                              ('settings', "Settings", "Settings")))

    showSceneUI_Pref : BoolProperty(description = "Show Scene Setup UI", default = True)
    showViewEditUI_Pref : BoolProperty(description = "Show View / Edit Maps UI", default = True)
    showExternalBakeUI_Pref : BoolProperty(description = "Show External Baking UI", default = True)

    drawMatPreviewUI_Pref: BoolProperty(description = "Draw UI in the viewport (useful to turn off if you are previewing materials in a small viewport, otherwise it is not recommended)", default = True)

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.prop(self, "Tabs", expand=True)

        # Information
        if self.Tabs == 'info':
            global custom_icons

            row = layout.row()
            row.separator()

            row = layout.row()
            row.operator("wm.url_open", text="Discord Support Server", icon_value=custom_icons["custom_icon"].icon_id).url = "https://discord.com/invite/wHAyVZG"
            row.operator("wm.url_open", text="Basic User Guide").url = "https://docs.google.com/document/d/1hJGfFiGBL-2nriT0ofdyqxj3Pn5dED2AEhzVbixvfpM/edit?usp=sharing"

            flow = layout.grid_flow()
            box = flow.box()

            box.label(text="Blender GrabDoc is an add-on structured around creating a simple and streamlined")
            box.label(text="method of grabbing baked maps for trim sheets, tileables or even alphas.")

            row = layout.row()
            row.label(text="        Support Us:")

            flow = layout.grid_flow()
            box = flow.box()

            box.label(text="If you like Blender GrabDoc, consider leaving a positive rating on the view content page")
            box.label(text="of the product in your Gumroad library. If you would like to support me further you can")
            box.label(text="either contact me with development ideas or send a few bucks via purchasing the product.")

        # Settings
        if self.Tabs == 'settings':
            row = layout.row()
            row.separator()

            row = layout.row()
            row.label(text="        UI Visibility:")
            box = layout.box()
            row = box.row()
            row.prop(self, "showSceneUI_Pref", text = "Show Scene Setup UI")
            row.prop(self, "showViewEditUI_Pref", text = "Show View/Edit UI")
            row.prop(self, "showExternalBakeUI_Pref", text = "Show External Bake UI")

            row = layout.row()
            row.label(text="        Other:")
            box = layout.box()
            row = box.row()
            row.prop(self, "drawMatPreviewUI_Pref", text = "Draw viewport UI in Map Preview mode")    


############################################################
# PROPERTY GROUP
############################################################


class GRABDOC_property_group(PropertyGroup):
    # Update Definitions
    def update_coll_settings(self, context):
        bpy.data.collections["GrabDoc (do not touch)"].hide_select = not self.collSelectable
        bpy.data.collections["GrabDoc (do not touch)"].hide_viewport = self.collHidden

    def update_height_guide(self, context):
        grabDocPrefs = context.scene.grabDocPrefs

        scene_refresh(self, context)

        if grabDocPrefs.modalState:
            # Update here so that it refreshes live in the VP
            mat = bpy.data.materials['GrabDoc_Temp_Height']

            map_range_node = mat.node_tree.nodes.get('Map Range')  

            if grabDocPrefs.onlyFlatValues:
                map_range_node.inputs[1].default_value = grabDocPrefs.camHeight - .001
            else:
                map_range_node.inputs[1].default_value = grabDocPrefs.heightGuide * -1 + grabDocPrefs.camHeight

            map_range_node.inputs[2].default_value = grabDocPrefs.camHeight

    def update_grid_subdivs(self, context):
        if not context.scene.grabDocPrefs.creatingGrid:
            context.scene.grabDocPrefs.creatingGrid = True

        scene_refresh(self, context)

    def update_resolution(self, context):
        render = context.scene.render
    
        if self.lockRes:
            if self.exportResY != self.exportResX:
                self.exportResY = self.exportResX
                render.resolution_y = self.exportResY
                render.resolution_x = self.exportResY
        else:
            render.resolution_x = self.exportResX
            render.resolution_y = self.exportResY

        scene_refresh(self, context)

    def update_export_name(self, context):
        if not context.scene.grabDocPrefs.exportName:
            context.scene.grabDocPrefs.exportName = "untitled"

    def update_bit_depth(self, context):
        context.scene.render.image_settings.color_depth = self.bitDepth

    def update_cavity(self, context):
        grabDocPrefs = context.scene.grabDocPrefs

        if grabDocPrefs.modalState:
            sceneShading = bpy.data.scenes[str(context.scene.name)].display.shading

            sceneShading.cavity_ridge_factor = grabDocPrefs.WSRidge
            sceneShading.curvature_ridge_factor = grabDocPrefs.SSRidge
            sceneShading.curvature_valley_factor = grabDocPrefs.SSValley

    def update_single_color(self, context):
        if context.scene.grabDocPrefs.modalState:
            sceneShading = bpy.data.scenes[str(context.scene.name)].display.shading
            sceneShading.single_color = context.scene.grabDocPrefs.colorCurvature

    def update_occlusion_gamma(self, context):
        if context.scene.grabDocPrefs.modalState:
            # Update here so that it refreshes live in the VP
            mat = bpy.data.materials['GrabDoc_Temp_AO']

            gamma_node = mat.node_tree.nodes.get('Gamma')
            gamma_node.inputs[1].default_value = context.scene.grabDocPrefs.gammaOcclusion

    def update_occlusion_distance(self, context):
        if context.scene.grabDocPrefs.modalState:
            # Update here so that it refreshes live in the VP
            context.scene.eevee.gtao_distance = context.scene.grabDocPrefs.distanceOcclusion

    def update_manual_height_range(self, context):
        if context.scene.grabDocPrefs.modalState and context.scene.grabDocPrefs.manualHeightRange == 'AUTO':
            get_rendered_objects(self, context)

            find_tallest_object(self, context)

        scene_refresh(self, context)

    # Properties
        # Setup
    collSelectable: BoolProperty(default = True, update = update_coll_settings)
    collHidden: BoolProperty(update = update_coll_settings)

    camHeight: FloatProperty(name = "", default = 5, min = .01, max = 10, step = .03, subtype = 'DISTANCE', update = update_height_guide)

    scalingType: EnumProperty(items = (('scaling_set', "Set", ""),
                                       ('scaling_matchRes', "Match Res", "Match the resolution of the image to the objects scale (Scale is based on the X axis of resolution)")),
                                       update = scene_refresh)
    scalingSet: FloatProperty(name = "", default = 2, min = .1, soft_max = 10, subtype = 'DISTANCE', update = scene_refresh)

    creatingGrid: BoolProperty(update = scene_refresh)
    creatingGridSubdivs: FloatProperty(name = "", default = 1, min = 1, max = 64, step = 100, precision = 0, update = update_grid_subdivs)

    onlyRenderColl: BoolProperty(update = scene_refresh, description = "Choose this option if your objects aren't visible in the renders. This will add a collection to the scene, and the add-on will ONLY render what is inside that collection. Read the documentation on why this can happen")

        # Baker
    exportResX: IntProperty(name = "X", default = 2048, min = 1, max = 8192, update = update_resolution)
    exportResY: IntProperty(name = "Y", default = 2048, min = 1, max = 8192, update = update_resolution)
    lockRes: BoolProperty(default = True, update = update_resolution)
    exportName: StringProperty(name = "",
                               description = "Changes the name of the exported file",
                               default = "untitled",
                               update = update_export_name)
    image_type: EnumProperty(items=(('PNG', "PNG", ""),
                                    ('TIFF', "TIFF", ""),
                                    ('TARGA', "TGA", "")), name = "Format")
    bitDepth: EnumProperty(items = (('16', "16", ""),
                                    ('8', "8", "")),
                                    update = update_bit_depth)                         
    openFolderOnExport: BoolProperty(description = "This option will open up the folder path whenever you export maps")

    exportNormals: BoolProperty(default = True)
    dropdownNormals: BoolProperty(name = "")
    reimportAsMat: BoolProperty(description = "This will reimport the Normals map as a material for use in Blender")
    normalsFlipY: BoolProperty(name = "Flip Y (-Y)")
    samplesNormals: IntProperty(name = "", default = 128, min = 1, max = 500)

    exportCurvature: BoolProperty(default = True)
    dropdownCurvature: BoolProperty(name = "")
    WSRidge: FloatProperty(name = "", default = 2.5, min = 0, max = 2.5, precision = 3, step = .1, update = update_cavity, subtype = 'FACTOR')
    SSRidge: FloatProperty(name = "", default = 2, min = 0, max = 2, precision = 3, step = .1, update = update_cavity, subtype = 'FACTOR')
    SSValley: FloatProperty(name = "", default = 0, min = 0, max = 2, precision = 3, step = .1, update = update_cavity, subtype = 'FACTOR')
    colorCurvature: FloatVectorProperty(subtype='COLOR', default=(.214041, .214041, .214041), update = update_single_color)
    contrastCurvature: EnumProperty(items = (('None', "None (Medium)", ""),
                                             ('Very_High_Contrast', "Very High", ""),
                                             ('High_Contrast', "High", ""),
                                             ('Medium_High_Contrast', "Medium High", ""),
                                             ('Medium_High_Contrast', "Medium Low", ""),
                                             ('Low_Contrast', "Low", ""),
                                             ('Very_Low_Contrast', "Very Low", "")),
                                             name = "Curvature Contrast")
    samplesCurvature: EnumProperty(items=(('OFF', "No Anti-Aliasing", ""),
                                          ('FXAA', "Single Pass Anti-Aliasing", ""),
                                          ('5', "5 Samples", ""),
                                          ('8', "8 Samples", ""),
                                          ('11', "11 Samples", ""),
                                          ('16', "16 Samples", ""),
                                          ('32', "32 Samples", "")),
                                          default = "32", name = "Curvature Samples")

    exportOcclusion: BoolProperty(default = True)
    dropdownOcclusion: BoolProperty(name = "")
    gammaOcclusion: FloatProperty(default = 1, min = .001, max = 10, step = .17, name = "", description = "Intensity of AO (calculated with gamma)", update = update_occlusion_gamma)
    distanceOcclusion: FloatProperty(default = 1, min = 0, max = 100, step = .03, subtype = 'DISTANCE', name = "", description = "The distance AO rays travel", update = update_occlusion_distance)
    samplesOcclusion: IntProperty(name = "", default = 128, min = 1, max = 500)
    contrastOcclusion: EnumProperty(items = (('None', "None (Medium)", ""),
                                             ('Very_High_Contrast', "Very High", ""),
                                             ('High_Contrast', "High", ""),
                                             ('Medium_High_Contrast', "Medium High", ""),
                                             ('Medium_High_Contrast', "Medium Low", ""),
                                             ('Low_Contrast', "Low", ""),
                                             ('Very_Low_Contrast', "Very Low", "")),
                                             name = "Occlusion Contrast")                      

    exportHeight: BoolProperty(default = True, update = scene_refresh)
    dropdownHeight: BoolProperty(name = "")
    onlyFlatValues: BoolProperty(description = "The height map will be exported with only fully white & black values for use as an alpha", update = update_height_guide)
    heightGuide: FloatProperty(name = "", default = 1, min = .001, max = 5, step = .03, subtype = 'DISTANCE', update = update_height_guide)
    samplesHeight: IntProperty(name = "", default = 128, min = 1, max = 500)
    manualHeightRange: EnumProperty(items = (('AUTO', "Auto", ""),
                                             ('MANUAL', "Manual", "")),
                                             update = update_manual_height_range,
                                             description = "Automatic or manual height range. Use manual if automatic is giving you incorrect results or if baking is really slow")

    exportMatID: BoolProperty(default = True)
    dropdownMatID: BoolProperty(name = "")
    matID_method: EnumProperty(items = (('RANDOM', "Random", ""),
                                        ('MATERIAL', "Material", "")))
    samplesMatID: EnumProperty(items=(('OFF', "No Anti-Aliasing", ""),
                                      ('FXAA', "Single Pass Anti-Aliasing", ""),
                                      ('5', "5 Samples", ""),
                                      ('8', "8 Samples", ""),
                                      ('11', "11 Samples", ""),
                                      ('16', "16 Samples", ""),
                                      ('32', "32 Samples", "")),
                                      default = "32", name = "Mat ID Samples")

    modalState: BoolProperty()
    preview_type: EnumProperty(items=(('None', "None", ""),
                                      ('Normals', "Normals", ""),
                                      ('Curvature', "Curvature", ""),
                                      ('Occlusion', "Ambient Occlusion", ""),
                                      ('Height', "Height", ""),
                                      ('ID', "Material ID", "")))                        
    wirePreview: BoolProperty(name = "Grid preview", description = "Visible grid when in Map Preview mode (NOTE: wireframe does not appear in or affect the export)")

        # Marmoset Baking
    dropdownMarmoset: BoolProperty(name = "")
    autoBake: BoolProperty(name = "Auto bake", default = True)
    closeAfterBake: BoolProperty(name = "Close after baking")
    samplesMarmoset: EnumProperty(items=(('1', "1x", ""),
                                         ('4', "4x", ""),
                                         ('16', "16x", "")),
                                         default = "16", name = "Marmoset Samples")
    aoRayCount: IntProperty(default = 512, min = 32, max = 4096)


##################################
# REGISTRATION
##################################


# Global var to store icons
custom_icons = None

def register():
    global custom_icons
    custom_icons = bpy.utils.previews.new()
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    custom_icons.load("custom_icon", os.path.join(icons_dir, "discord_icon.png"), 'IMAGE')

    bpy.utils.register_class(PIESPLUS_MT_addon_prefs)
    bpy.utils.register_class(GRABDOC_property_group)

    bpy.types.Scene.grabDocPrefs = PointerProperty(type = GRABDOC_property_group)

    bpy.types.Scene.directory = StringProperty(subtype = 'FILE_PATH')
    bpy.types.Scene.marmoset_exe_filepath = bpy.props.StringProperty \
        (name = "",
         default = " ",
         description = "Define the export path",
         subtype = 'FILE_PATH')

def unregister():
    global custom_icons
    bpy.utils.previews.remove(custom_icons)

    bpy.utils.unregister_class(PIESPLUS_MT_addon_prefs)
    bpy.utils.unregister_class(GRABDOC_property_group)


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