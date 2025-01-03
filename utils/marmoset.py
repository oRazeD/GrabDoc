"""Startup script to run alongside Marmoset Toolbag.
"""


import os
import json
from pathlib import Path

import mset


def run_auto_baker(baker, properties: dict) -> None:
    baker.bake()
    os.startfile(properties['filepath'])

    # TODO: Implement alpha mask
    # NOTE: There is no alpha support in Marmoset so we use
    # height with a modified range and run another bake pass
    #if properties['export_alpha'] and properties['auto_bake']:
    #    enabled_maps = \
    #        [bake_map for bake_map in baker.getAllMaps() is bake_map.enabled]
    #    for bake_map in baker.getAllMaps():
    #        bake_map.enabled = False
    #    alpha = baker.getMap("Height")
    #    alpha.enabled = True
    #    alpha.suffix = properties['suffix_alpha']
    #    alpha.innerDistance = 0
    #    alpha.outerDistance = .01
    #    baker.bake()
    #
    #    # NOTE: Refresh original bake
    #    baker_setup()
    #    alpha.enabled = False

    # Close marmo if the option is selected
    if properties['close_after_bake']:
        mset.quit()
        return

    mset.findObject('High').visible = False


def create_baker(properties: dict):
    mset.newScene()
    baker = mset.BakerObject()
    baker.outputPath = properties['file_path']
    baker.outputBits = properties['bits_per_channel']
    baker.edgePadding = "None"
    baker.outputSoften = 0.5
    baker.useHiddenMeshes = True
    baker.ignoreTransforms = False
    baker.smoothCage = True
    baker.ignoreBackfaces = True
    baker.multipleTextureSets = False
    baker.outputWidth = properties['resolution_x']
    baker.outputHeight = properties['resolution_y']
    # NOTE: Output samples is broken in older APIs
    if mset.getToolbagVersion() < 4000 and properties['samples'] == 64:
        baker.outputSamples = 16
    else:
        baker.outputSamples = properties['samples']
    return baker


def baker_setup(baker, properties: dict) -> None:
    for bake_map in baker.getAllMaps():
        bake_map.enabled = False

    normals = baker.getMap("Normals")
    normals.enabled = properties['export_normal']
    normals.suffix = properties['suffix_normal']
    normals.flipY = properties['flipy_normal']
    normals.flipX = False
    normals.dither = False

    curvature = baker.getMap("Curvature")
    curvature.enabled = properties['export_curvature']
    curvature.suffix = properties['suffix_curvature']

    occlusion = baker.getMap("Ambient Occlusion")
    occlusion.enabled = properties['export_occlusion']
    occlusion.suffix = properties['suffix_occlusion']
    occlusion.rayCount = properties['ray_count_occlusion']

    height = baker.getMap("Height")
    height.enabled = properties['export_height']
    height.suffix = properties['suffix_height']
    height.innerDistance = 0
    height.outerDistance = properties['cage_height'] / 2 - .02

    material = baker.getMap("Material ID")
    material.enabled = properties['export_matid']
    material.suffix = properties['suffix_id']

def shader_setup(properties: dict) -> None:
    findDefault = mset.findMaterial("Default")
    findDefault.name = "GrabDoc Bake Result"
    if properties["export_normal"]:
        findDefault.getSubroutine('surface').setField(
            'Normal Map',
            properties['file_path'][:-4] + '_' +
            properties['suffix_normal'] + '.' + properties['format']
        )
    if properties["export_occlusion"]:
        findDefault.setSubroutine('occlusion', 'Occlusion')
        findDefault.getSubroutine('occlusion').setField(
            'Occlusion Map',
            properties['file_path'][:-4] + '_' +
            properties['suffix_occlusion'] + '.' + properties['format']
        )


def main():
    plugin_path = Path(mset.getPluginPath()).parents[1]
    temp_path = os.path.join(plugin_path, "temp")
    properties_path = os.path.join(temp_path, "mt_vars.json")

    # Check if file location has been repopulated
    if not os.path.exists(properties_path):
        return

    with open(properties_path, 'r', encoding='utf-8') as file:
        properties = json.load(file)
    # NOTE: Remove the file so when the file is
    # recreated we know to update scene properties
    os.remove(properties_path)

    # Baker setup
    baker = create_baker(properties)
    model_path = os.path.join(temp_path, "mesh_export.fbx")
    baker.importModel(model_path)

    # Set cage distance
    mset.findObject('Low').maxOffset = properties['cage_height'] + .001

    # Scale up the high poly plane
    mset.findObject(
        "[GrabDoc] Background Plane_high_gd"
    ).scale = [300, 300, 300]

    # Rotate imported group to align with camera
    bake_group = mset.findObject("[GrabDoc] Background Plane")
    bake_group.rotation = [90, 0, 0]
    # Create groups for material id
    for mat in mset.getAllMaterials():
        if mat.name.startswith("GD_"):
            mat.setGroup('[GrabDoc] Materials')

    baker_setup(baker, properties)
    if properties['auto_bake']:
        run_auto_baker(baker, properties)
    # NOTE: Delete FBX file to avoid temp folder bloat
    #os.remove(model_path)
    shader_setup(properties)


if __name__ == "__main__":
    mset.callbacks.onRegainFocus = main
    main()
