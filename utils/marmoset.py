import os
import json

import mset

from ..constants import Global


temp_path = os.path.join(os.path.dirname(mset.getPluginPath()), "_temp")

def refresh_scene() -> None:
    if os.path.exists(os.path.join(temp_path, "marmo_vars.json")):
        mset.newScene()

        with open(
            os.path.join(temp_path, "marmo_vars.json"), 'r', encoding='utf-8'
        ) as openfile:
            marmo_json = json.load(openfile)

        ## BAKER SETUP

        baker = mset.BakerObject()

        baker.outputPath = marmo_json["file_path"]
        baker.outputBits = marmo_json["bits_per_channel"]

        baker.edgePadding = "None"
        baker.outputSoften = 0.5
        baker.useHiddenMeshes = True
        baker.ignoreTransforms = False
        baker.smoothCage = True
        baker.ignoreBackfaces = True
        baker.multipleTextureSets = False
        baker.outputWidth = marmo_json["resolution_x"]
        baker.outputHeight = marmo_json["resolution_y"]

        if mset.getToolbagVersion() < 4000 and marmo_json["samples"] == 64:
            baker.outputSamples = 16
        else:
            baker.outputSamples = marmo_json["samples"]

        # Import the models
        baker.importModel(
            os.path.normpath(os.path.join(temp_path, "GD_temp_model.fbx"))
        )

        # Set cage offset
        mset.findObject('Low').maxOffset = marmo_json["cage_height"] + .01

        # Change skybox to Evening Clouds
        if mset.getToolbagVersion() < 4000:
            mset.findObject('Sky').loadSky(marmo_json["marmo_sky_path"])

        # Rotate all models 90 degrees
        bakeGroup = mset.findObject('GD')
        bakeGroup.rotation = [90, 0, 0]

        # Make a folder for Mat ID materials
        for mat in mset.getAllMaterials():
            if mat.name.startswith(Global.GD_PREFIX):
                mat.setGroup('Mat ID')

        ## BAKE MAPS SETUP

        for maps in baker.getAllMaps():
            maps.enabled = False

        # Extra bake pass for alpha map
        if marmo_json["export_alpha"]:
            alphaMap = baker.getMap("Height")
            alphaMap.enabled = marmo_json["export_alpha"]
            alphaMap.suffix = marmo_json['suffix_alpha']
            alphaMap.innerDistance = 0
            alphaMap.outerDistance = .01

            if marmo_json["auto_bake"]:
                baker.bake()

                alphaMap.enabled = False

        normalMap = baker.getMap("Normals")
        normalMap.enabled = marmo_json["export_normal"]
        normalMap.suffix = marmo_json['suffix_normal']
        normalMap.flipY = marmo_json["flipy_normal"]
        normalMap.flipX = False
        normalMap.dither = False

        curvatureMap = baker.getMap("Curvature")
        curvatureMap.enabled = marmo_json["export_curvature"]
        curvatureMap.suffix = marmo_json['suffix_curvature']

        occlusionMap = baker.getMap("Ambient Occlusion")
        occlusionMap.enabled = marmo_json["export_occlusion"]
        occlusionMap.suffix = marmo_json['suffix_occlusion']
        occlusionMap.rayCount = marmo_json["ray_count_occlusion"]

        heightMap = baker.getMap("Height")
        heightMap.enabled = marmo_json["export_height"]
        heightMap.suffix = marmo_json['suffix_height']
        heightMap.innerDistance = 0
        heightMap.outerDistance = marmo_json["cage_height"] / 2 - .02

        matIDMap = baker.getMap("Material ID")
        matIDMap.enabled = marmo_json["export_matid"]
        matIDMap.suffix = marmo_json['suffix_id']

        ## BAKE & FINALIZE

        if marmo_json["auto_bake"]:
            baker.bake()

            # Open folder on export
            if marmo_json["open_folder"]:
                os.startfile(marmo_json["file_path_no_ext"])

            # Close marmo if the option is selected
            if marmo_json["close_after_bake"]:
                mset.quit()
            else:
                # Hide the _High group
                mset.findObject('High').visible = False

                # Scale up the high poly plane
                mset.findObject(
                    f'{Global.GD_HIGH_PREFIX} {Global.BG_PLANE_NAME}'
                ).scale = [300, 300, 300]

                findDefault = mset.findMaterial("Default")

                # Material preview
                if marmo_json["export_normal"]:
                    findDefault.getSubroutine('surface').setField(
                        'Normal Map', marmo_json["file_path"][:-4] + '_' + marmo_json['suffix_normal'] + '.' + marmo_json['file_ext']
                    )

                if marmo_json["export_occlusion"]:
                    findDefault.setSubroutine('occlusion', 'Occlusion')
                    findDefault.getSubroutine('occlusion').setField(
                        'Occlusion Map', marmo_json["file_path"][:-4] + '_' + marmo_json['suffix_occlusion'] + '.' + marmo_json['file_ext']
                    )

                # Rename bake material
                findDefault.name = 'Bake Material'

        # Remove the json file to signal the no rebakes
        # need to take place until a new one is made
        os.remove(os.path.join(temp_path, "marmo_vars.json"))


mset.callbacks.onRegainFocus = refresh_scene

refresh_scene()



