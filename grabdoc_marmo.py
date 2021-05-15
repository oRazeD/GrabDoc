import mset, os, json


temps_path = os.path.join(os.path.dirname(mset.getPluginPath()), "Temp")

def refresh_scene():
    if os.path.exists(os.path.join(temps_path, "marmo_vars.json")):
        mset.newScene()

        with open(os.path.join(temps_path, "marmo_vars.json"), 'r') as openfile:
            marmo_json = json.load(openfile)

        # Create baker object
        baker = mset.BakerObject()

        # Setting up the baker
        baker.outputPath = marmo_json["file_path"]
        baker.outputBits = marmo_json["bits_per_channel"]
        baker.outputSamples = marmo_json["samples"]
        baker.edgePadding = "None"
        baker.outputSoften = 0.5
        baker.useHiddenMeshes = True
        baker.ignoreTransforms = False
        baker.smoothCage = True
        baker.ignoreBackfaces = True
        baker.multipleTextureSets = False
        baker.outputWidth = marmo_json["resolution_x"]
        baker.outputHeight = marmo_json["resolution_y"]

        # Disable all maps
        for maps in baker.getAllMaps():
            maps.enabled = False

        # Configure maps
        normalMap = baker.getMap("Normals")
        normalMap.enabled = marmo_json["export_normals"]
        normalMap.suffix = 'normal'
        normalMap.flipY = marmo_json["flipy_normals"]
        normalMap.flipX = False
        normalMap.dither = False

        curvatureMap = baker.getMap("Curvature")
        curvatureMap.enabled = marmo_json["export_curvature"]

        occlusionMap = baker.getMap("Ambient Occlusion")
        occlusionMap.rayCount = marmo_json["ray_count_occlusion"]
        occlusionMap.enabled = marmo_json["export_occlusion"]

        heightMap = baker.getMap("Height")
        heightMap.innerDistance = 0
        heightMap.enabled = marmo_json["export_height"]
        if marmo_json["flat_height"]:
            heightMap.outerDistance = .01
        else:
            heightMap.outerDistance = marmo_json["cage_height"] / 2 - .02

        matIDMap = baker.getMap("Material ID")
        matIDMap.enabled = marmo_json["export_matid"]

        # Import the models
        baker.importModel(os.path.join(temps_path, "grabdoc_temp_model.fbx"))

        # Set cage offset
        mset.findObject('Low').maxOffset = marmo_json["cage_height"] + .01

        tb_version = mset.getToolbagVersion()

        # Change skybox to Evening Clouds
        if tb_version < 4000:
            mset.findObject('Sky').loadSky(marmo_json["marmo_sky_path"])

        # Rotate all models 90 degrees
        bakeGroup = mset.findObject('GrabDoc')
        bakeGroup.rotation = [90, 0, 0]

        # Make a folder for Mat ID materials
        for mat in mset.getAllMaterials():
            if mat.name.startswith("GD_"):
                mat.setGroup('Mat ID')

        # Baker
        if marmo_json["auto_bake"]:
            baker.bake()

            # Open folder on export
            if marmo_json["open_folder"]:
                os.startfile(marmo_json["file_path_no_ext"])

            # Close marmo if the option is selected
            if marmo_json["close_after_bake"]:
                mset.quit()
            
            # Hide the _High group
            mset.findObject('High').visible = False
            
            # Scale up the high poly plane
            mset.findObject('GrabDoc_high GD_Background Plane').scale = [300, 300, 300]

            findDefault = mset.findMaterial("Default")

            # Material preview
            if marmo_json["export_normals"]:
                findDefault.getSubroutine('surface').setField('Normal Map', marmo_json["file_path"][:-4] + '_normal' + '.png')

            if marmo_json["export_occlusion"]:
                findDefault.setSubroutine('occlusion', 'Occlusion')
                findDefault.getSubroutine('occlusion').setField('Occlusion Map', marmo_json["file_path"][:-4] + '_ao' + '.png')

            # Rename bake material
            findDefault.name = 'Bake Material'

        os.remove(os.path.join(temps_path, "marmo_vars.json"))


mset.callbacks.onRegainFocus = refresh_scene

refresh_scene()


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
