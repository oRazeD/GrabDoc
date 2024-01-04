
class Global:
    """A collection of constants used for global variable standardization"""
    GD_PREFIX      = "GD_"
    GD_FLAG_PREFIX = "[GrabDoc] "
    GD_LOW_PREFIX  = GD_PREFIX + "low"
    GD_HIGH_PREFIX = GD_PREFIX + "high"

    REFERENCE_NAME    = GD_PREFIX + "Reference"
    TRIM_CAMERA_NAME  = GD_PREFIX + "Trim Camera"
    BG_PLANE_NAME     = GD_PREFIX + "Background Plane"
    HEIGHT_GUIDE_NAME = GD_PREFIX + "Height Guide"
    ORIENT_GUIDE_NAME = GD_PREFIX + "Orient Guide"
    GD_MATERIAL_NAME  = GD_PREFIX + "Material (do not touch contents)"
    COLL_NAME         = "GrabDoc (do not touch contents)"
    COLL_OB_NAME      = "GrabDoc Objects (put objects here)"

    MAT_ID_PREFIX      = GD_PREFIX + "ID"
    MAT_ID_RAND_PREFIX = GD_PREFIX + "RANDOM_ID"

    REIMPORT_MAT_NAME = GD_FLAG_PREFIX + "Render Result"

    NORMAL_ID    = "normals"
    CURVATURE_ID = "curvature"
    OCCLUSION_ID = "occlusion"
    HEIGHT_ID    = "height"
    MATERIAL_ID  = "id"
    ALPHA_ID     = "alpha"
    COLOR_ID     = "color"
    EMISSIVE_ID  = "emissive"
    ROUGHNESS_ID = "roughness"
    METALNESS_ID = "metalness"

    NORMAL_NAME    = NORMAL_ID.capitalize()
    CURVATURE_NAME = CURVATURE_ID.capitalize()
    OCCLUSION_NAME = "Ambient Occlusion"
    HEIGHT_NAME    = HEIGHT_ID.capitalize()
    MATERIAL_NAME  = "Material ID"
    ALPHA_NAME     = ALPHA_ID.capitalize()
    COLOR_NAME     = "Base Color"
    EMISSIVE_NAME  = EMISSIVE_ID.capitalize()
    ROUGHNESS_NAME = ROUGHNESS_ID.capitalize()
    METALNESS_NAME = METALNESS_ID.capitalize()

    NORMAL_NODE    = GD_PREFIX + NORMAL_NAME
    OCCLUSION_NODE = GD_PREFIX + OCCLUSION_NAME
    HEIGHT_NODE    = GD_PREFIX + HEIGHT_NAME
    ALPHA_NODE     = GD_PREFIX + ALPHA_NAME
    COLOR_NODE     = GD_PREFIX + COLOR_NAME
    EMISSIVE_NODE  = GD_PREFIX + EMISSIVE_NAME
    ROUGHNESS_NODE = GD_PREFIX + ROUGHNESS_NAME
    METALNESS_NODE = GD_PREFIX + METALNESS_NAME

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
        METALNESS_ID
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
        METALNESS_NAME
    )

    SHADER_MAP_NAMES = (
        NORMAL_NODE,
        COLOR_NODE,
        EMISSIVE_NODE,
        ROUGHNESS_NODE,
        METALNESS_NODE
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

    PACK_MAPS_WARNING = \
"""Map Packing is a new feature in GrabDoc for optimizing textures being
exported (usually directly to engine) by cramming grayscale baked maps into
each RGBA channel of a single texture reducing the amount of texture samples
used and by extension the memory footprint. This is meant to be a simple
alternative to pit-stopping over to compositing software to finish the job
but its usability is limited.

Map Packing in GrabDoc is new, so here's a few things to keep note of:
\u2022 Only grayscale maps can currently be packed
\u2022 Map packing isn't supported for Marmoset bakes
\u2022 Any successfully packed maps will not also be exported as their
own maps and will also ignore `Import as Material` option
\u2022 The default selected packed channels don't represent the default enabled
bake maps, meaning without intervention G, B, and A channels will be empty."""

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
    MARMOSET_RE_EXPORT_COMPLETE = \
        "Models re-exported! Check Marmoset Toolbag"
    OFFLINE_RENDER_COMPLETE = \
        "Offline render completed!"
    EXPORT_COMPLETE = \
        "Export completed!"
