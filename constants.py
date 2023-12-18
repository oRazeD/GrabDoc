# NOTE: This is a basic grouping of constants for specific object
# names that are frequently reused. An improved approach would
# be to make a system that doesn't rely on naming conventions and
# instead reads GD-specific attributes, or whatever alternative relies
# on just using less constants. This is more a temp cope for old code.

# from .constants import GlobalVariableConstants as Global


NAME = "GrabDoc Pro"
VERSION = (1, 4, 0)
BLENDER_VERSION = (4, 0, 1)


class GlobalVariableConstants:
    """A collection of constants used for global variable standardization"""
    ID_PREFIX = "grab_doc" # TODO: wrong prefix?

    REFERENCE_NAME    = "GD_Reference"
    TRIM_CAMERA_NAME  = "GD_Trim Camera"
    BG_PLANE_NAME     = "GD_Background Plane"
    COLL_NAME         = "GrabDoc (do not touch contents)"
    COLL_OB_NAME      = "GrabDoc Objects (put objects here)"
    HEIGHT_GUIDE_NAME = "GD_Height Guide"
    ORIENT_GUIDE_NAME = "GD_Orient Guide"
    GD_MATERIAL_NAME  = "GD_Material (do not touch contents)"

    GD_PREFIX      = "GD_"
    GD_LOW_PREFIX  = "GD_low"
    GD_HIGH_PREFIX = "GD_high"

    MAT_ID_PREFIX      = "GD_ID"
    MAT_ID_RAND_PREFIX = "GD_RANDOM_ID"

    NG_NORMAL_NAME    = "GD_Normal"
    NG_AO_NAME        = "GD_Ambient Occlusion"
    NG_HEIGHT_NAME    = "GD_Height"
    NG_ALPHA_NAME     = "GD_Alpha"
    NG_ALBEDO_NAME    = "GD_Albedo"
    NG_ROUGHNESS_NAME = "GD_Roughness"
    NG_METALNESS_NAME = "GD_Metalness"

    INVALID_RENDER_TYPES = (
        'EMPTY',
        'VOLUME',
        'ARMATURE',
        'LATTICE',
        'LIGHT',
        'LIGHT_PROBE',
        'CAMERA'
    )

    FORMAT_MATCHED_EXTENSIONS = {
        'TIFF': 'tif',
        'TARGA': 'tga',
        'OPEN_EXR': 'exr',
        'PNG': 'png'
    }

    NG_NODE_WARNING = \
"""This is a passthrough node from GrabDoc, once you Exit Map Preview every node link will be returned
to original positions. It's best not to touch the contents of the node group (or material) but if you
do anyways it shouldn't be overwritten by GrabDoc until the node group is removed from file, which
only happens when you use the `Remove Setup` operator."""

    PACK_MAPS_WARNING = \
"""Map Packing is a new feature in GrabDoc for optimizing textures being exported (usually
directly to engine) by cramming grayscale baked maps into each RGBA channel of a single
texture reducing the amount of texture samples used and by extension the memory footprint.
This is meant to be a simple alternative to pit-stopping over to compositing software to
finish the job, but its usability is limited.

Map Packing in GrabDoc is new, so here's a few things to keep note of:
\u2022 Only grayscale maps can currently be packed
\u2022 Map packing isn't supported for Marmoset bakes
\u2022 Any successfully packed maps will not also be exported as their
own maps and will also ignore `Import as Material` option
\u2022 The default selected packed channels don't represent the default enabled
bake maps, meaning without intervention G, B, and A channels will be empty."""

    PREVIEW_WARNING = \
"""Live Material Preview allows you to visualize your bake maps in real-time!

This feature is intended for previewing your materials, NOT for working while inside
the preview. Once finished please exit previews to avoid scene altering changes.

Pressing `OK` will dismiss this warning permanently for the current project file."""


class ErrorCodeConstants:
    """A collection of constants used for error code/message standardization"""

    NO_OBJECTS_SELECTED = "There are no objects selected"

    TRIM_CAM_NOT_FOUND = \
        "Trim Camera not found, refresh the scene to set everything up properly"
    NO_OBJECTS_BAKE_GROUPS = \
        "You have 'Use Bake Group' turned on, but no objects are inside the corresponding collection"
    NO_VALID_PATH_SET = \
        "There is no export path set"

    MAT_SLOTS_WITHOUT_LINKS = \
        "Material slots found without links & will be rendered using the sockets default value"

    MARMOSET_EXPORT_COMPLETE = \
        "Export completed! Opening Marmoset Toolbag..."
    MARMOSET_RE_EXPORT_COMPLETE = \
        "Models re-exported! Check Marmoset Toolbag"

    OFFLINE_RENDER_COMPLETE = \
        "Offline render completed!"
    EXPORT_COMPLETE = \
        "Export completed!"



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
