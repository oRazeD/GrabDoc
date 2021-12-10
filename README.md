![GrabDoc Image](https://user-images.githubusercontent.com/31065180/122285547-e10f9380-cebc-11eb-9726-2322cb8ae907.png)

# GrabDoc Introduction

GrabDoc is a Blender add-on made to create a simple and streamlined workflow for exporting baked maps for trim sheets, tileables, alphas or even stamps. When installed all you need to do is run the one-click scene setup, and then start modeling! Whether you've modeled out your shapes or are still modeling them you can preview what the baked maps will look like in the viewport live! Once satisfied you can bake all maps using in-house options or even utilizing Marmoset Toolbag 3&4's baker for the best possible results!

Video Examples: https://www.artstation.com/artwork/WKmwzG

Product page: https://gumroad.com/l/grabdoc

# Feature Set

This list is oversimplified... I will eventually do a pass to be more verbose about the specific things you can do in GrabDoc <3

- Preview all of your to-be baked objects realtime in Map Preview Mode
- Export bake maps such as Normals, Curvature, Occlusion, Height, Material ID, Alpha, Albedo, Roughness and Metalness quickly and with optimized file-sizes
- Create Alpha & Normal stamps with transparency
- Baking Bridge between Blender and Marmoset Toolbag3&4
- ...and more!

# Installation Guide

1. Click the **Code** button in the top right of the repo & click **Download ZIP** in the dropdown (Do not unpack the ZIP file)
2. Follow this video for the rest of the simple instructions

https://user-images.githubusercontent.com/31065180/137642217-d51470d3-a243-438f-8c49-1e367a8972ab.mp4


# TODO / Future Update Paths

- [ ] Painter Bridge Support (Baking and or just setting up a project file)
- [ ] Extending Albedo/Roughness/Metallic/Mixed Normals bake functionality to the bridge exporter
- [ ] Rewrite of "Re-import as Material" feature as a whole with bridge exporter support
- [ ] A general feature parity pass between the different baking engines
- [ ] Improved multiple viewport support
- [ ] A more dynamic method of generating a bake setup, for things like exporting multiple bake maps of the same type (very cool, but very unlikely)
- [ ] Improved offline render (internal rendering) support:
    - [ ] Allow compositing from this render type (for overlaying things like Ambient Occlusion)
    - [ ] Support "Re-import as Material" feature
    - [ ] Support correct default color spaces

# Known Issues / Limitations

- If you create a new object or unhide objects not originally visible while in a Map Preview mode, the object will be black.
  - SOLUTION: GrabDoc is material based and does not update materials constantly, so just leaving Map Preview mode and re entering it will refresh the scene materials.
