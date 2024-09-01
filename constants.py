

class Global:
    """A collection of constants used for global variable standardization"""
    PREFIX      = "GD_"
    FLAG_PREFIX = "[GrabDoc] "
    LOW_SUFFIX  = "_low_gd"
    HIGH_SUFFIX = "_high_gd"

    REFERENCE_NAME    = FLAG_PREFIX + "Reference"
    TRIM_CAMERA_NAME  = FLAG_PREFIX + "Trim Camera"
    BG_PLANE_NAME     = FLAG_PREFIX + "Background Plane"
    HEIGHT_GUIDE_NAME = FLAG_PREFIX + "Height Guide"
    ORIENT_GUIDE_NAME = FLAG_PREFIX + "Orient Guide"
    GD_MATERIAL_NAME  = FLAG_PREFIX + "Material"
    COLL_NAME         = "GrabDoc Core"
    COLL_OB_NAME      = "GrabDoc Bake Group"

    ID_PREFIX        = FLAG_PREFIX + "ID"
    RANDOM_ID_PREFIX = FLAG_PREFIX + "RANDOM_ID"

    REIMPORT_MAT_NAME = FLAG_PREFIX + "Bake Result"

    NORMAL_ID    = "normals"
    CURVATURE_ID = "curvature"
    OCCLUSION_ID = "occlusion"
    HEIGHT_ID    = "height"
    MATERIAL_ID  = "id"
    ALPHA_ID     = "alpha"
    COLOR_ID     = "color"
    EMISSIVE_ID  = "emissive"
    ROUGHNESS_ID = "roughness"
    METALLIC_ID  = "metallic"

    NORMAL_NAME    = NORMAL_ID.capitalize()
    CURVATURE_NAME = CURVATURE_ID.capitalize()
    OCCLUSION_NAME = "Ambient Occlusion"
    HEIGHT_NAME    = HEIGHT_ID.capitalize()
    MATERIAL_NAME  = "Material ID"
    ALPHA_NAME     = ALPHA_ID.capitalize()
    COLOR_NAME     = "Base Color"
    EMISSIVE_NAME  = EMISSIVE_ID.capitalize()
    ROUGHNESS_NAME = ROUGHNESS_ID.capitalize()
    METALLIC_NAME = METALLIC_ID.capitalize()

    NORMAL_NODE    = PREFIX + NORMAL_NAME
    CURVATURE_NODE = PREFIX + CURVATURE_NAME
    OCCLUSION_NODE = PREFIX + OCCLUSION_NAME
    HEIGHT_NODE    = PREFIX + HEIGHT_NAME
    ALPHA_NODE     = PREFIX + ALPHA_NAME
    COLOR_NODE     = PREFIX + COLOR_NAME
    EMISSIVE_NODE  = PREFIX + EMISSIVE_NAME
    ROUGHNESS_NODE = PREFIX + ROUGHNESS_NAME
    METALLIC_NODE = PREFIX + METALLIC_NAME

    ALL_MAP_IDS = (
        NORMAL_ID,
        CURVATURE_ID,
        OCCLUSION_ID,
        HEIGHT_ID,
        MATERIAL_ID,
        ALPHA_ID,
        COLOR_ID,
        EMISSIVE_ID,
        ROUGHNESS_ID,
        METALLIC_ID
    )

    ALL_MAP_NAMES = (
        NORMAL_NAME,
        CURVATURE_NAME,
        OCCLUSION_NAME,
        HEIGHT_NAME,
        MATERIAL_NAME,
        ALPHA_NAME,
        COLOR_NAME,
        EMISSIVE_NAME,
        ROUGHNESS_NAME,
        METALLIC_NAME
    )

    SHADER_MAP_NAMES = (
        NORMAL_NODE,
        CURVATURE_NODE,
        ALPHA_NODE,
        COLOR_NODE,
        EMISSIVE_NODE,
        ROUGHNESS_NODE,
        METALLIC_NODE,
        OCCLUSION_NODE
    )

    INVALID_BAKE_TYPES = (
        'EMPTY',
        'VOLUME',
        'ARMATURE',
        'LATTICE',
        'LIGHT',
        'LIGHT_PROBE',
        'CAMERA'
    )

    IMAGE_FORMATS = {
        'TIFF': 'tif',
        'TARGA': 'tga',
        'OPEN_EXR': 'exr',
        'PNG': 'png'
    }

    NG_NODE_WARNING = \
"""This is a passthrough node from GrabDoc, once you
Exit Map Preview every node link will be returned
to original positions. It's best not to touch the
contents of the node group (or material) but if you
do anyways it shouldn't be overwritten by GrabDoc
until the node group is removed from file, which
only happens when you use the `Remove Setup` operator."""

    # TODO: Currently unused
    PACK_MAPS_WARNING = \
"""Map Packing is a feature for optimizing textures being exported
(usually directly to engine) by cramming grayscale baked maps into
each RGBA channel of a single texture reducing the amount of texture
samples used and by extension the memory footprint. This is meant to
be a simple alternative to pit-stopping over to compositing software
to finish the job but its usability is limited.

Here's a few things to keep note of:
\u2022 Only grayscale bake maps can be packed
\u2022 Map packing isn't supported for Marmoset bakes
\u2022 The default packed channels don't represent the default bake
maps. Without intervention, the G, B, and A channels will be empty."""

    PREVIEW_WARNING = \
"""Material Preview allows you to visualize your bake maps in real-time!
\u2022 This feature is intended for previewing your materials before baking, NOT
\u2022 for working while inside a preview. Once finished, please exit previews
\u2022 to avoid scene altering changes.
\u2022 Pressing OK will dismiss this warning permanently for the project."""


class Error:
    """A collection of constants used for error code/message standardization"""

    NO_OBJECTS_SELECTED = "There are no objects selected"
    TRIM_CAM_NOT_FOUND = \
        "GrabDoc Camera not found, please run the Refresh Scene operator"
    NO_OBJECTS_BAKE_GROUPS = \
        "No objects found in bake collections"
    NO_VALID_PATH_SET = \
        "There is no export path set"
    MAT_SLOTS_WITHOUT_LINKS = \
        "Material slots were found without links, using default values"
    MARMOSET_EXPORT_COMPLETE = \
        "Export completed! Opening Marmoset Toolbag..."
    MARMOSET_REFRESH_COMPLETE = \
        "Models re-exported! Check Marmoset Toolbag"
    OFFLINE_RENDER_COMPLETE = \
        "Offline render completed!"
    EXPORT_COMPLETE = \
        "Export completed!"
