
class Global:
    """A collection of constants used for global variable standardization"""
    FLAG_PREFIX          = "[GrabDoc] "
    LOW_SUFFIX           = "_low_gd"
    HIGH_SUFFIX          = "_high_gd"
    NODE_GROUP_WARN_NAME = "_grabdoc_ng_warning"

    REFERENCE_NAME    = FLAG_PREFIX + "Reference"
    TRIM_CAMERA_NAME  = FLAG_PREFIX + "Trim Camera"
    BG_PLANE_NAME     = FLAG_PREFIX + "Background Plane"
    HEIGHT_GUIDE_NAME = FLAG_PREFIX + "Height Guide"
    ORIENT_GUIDE_NAME = FLAG_PREFIX + "Orient Guide"
    GD_MATERIAL_NAME  = FLAG_PREFIX + "Material"
    ID_PREFIX         = FLAG_PREFIX + "ID"
    RANDOM_ID_PREFIX  = FLAG_PREFIX + "RANDOM_ID"
    REIMPORT_MAT_NAME = FLAG_PREFIX + "Bake Result"
    COLL_CORE_NAME    = FLAG_PREFIX + "Core"
    COLL_GROUP_NAME   = FLAG_PREFIX + "Bake Group"

    CAMERA_DISTANCE = 15

    INVALID_BAKE_TYPES = ('EMPTY',
                          'VOLUME',
                          'ARMATURE',
                          'LATTICE',
                          'LIGHT',
                          'LIGHT_PROBE',
                          'CAMERA')

    IMAGE_FORMATS = {'TIFF':     'tif',
                     'TARGA':    'tga',
                     'OPEN_EXR': 'exr',
                     'PNG':      'png'}

    NODE_GROUP_WARN = """
This node is generated by GrabDoc! Once exiting Map Preview,
every node link will be returned to their original sockets.

Avoid editing the contents of this node group. If you do make
changes, using the Remove Setup operator will overwrite any changes!"""


class Error:
    """A collection of constants used for error code/message standardization"""
    NO_OBJECTS_SELECTED       = "There are no objects selected"
    BAKE_GROUPS_EMPTY         = "No objects found in bake collections"
    NO_VALID_PATH_SET         = "There is no export path set"
    ALL_MAPS_DISABLED         = "No bake maps are enabled"
    MARMOSET_EXPORT_COMPLETE  = "Export completed! Opening Marmoset Toolbag..."
    MARMOSET_REFRESH_COMPLETE = "Models re-exported! Switch to Marmoset Toolbag"
    EXPORT_COMPLETE           = "Export completed!"
    CAMERA_NOT_FOUND          = \
        "GrabDoc camera not found, please run the Refresh Scene operator"
    MISSING_SLOT_LINKS        = \
        "socket(s) found without links, bake results may appear incorrect"
