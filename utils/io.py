import bpy

from ..constants import Global


def get_temp_path() -> str:
    """Gets or creates a temporary directory based on the extensions system."""
    return bpy.utils.extension_path_user(
        __package__.rsplit(".", maxsplit=1)[0], path="temp", create=True
    )


def get_format() -> str:
    """Get the correct file extension based on `format` attribute"""
    return f".{Global.IMAGE_FORMATS[bpy.context.scene.gd.format]}"


def get_filepath() -> str:
    """Get the absolute export filepath from the user preferences"""
    gd = bpy.context.scene.gd
    if not gd.filepath:
        return "//"
    return gd.filepath
