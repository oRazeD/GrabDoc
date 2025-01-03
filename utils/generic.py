import os
import re
import tomllib
from pathlib import Path

import bpy
from bpy.types import Context

from ..constants import Error


class UseSelectedOnly():
    @classmethod
    def poll(cls, context: Context) -> bool:
        return True if len(context.selected_objects) \
          else cls.poll_message_set(Error.NO_OBJECTS_SELECTED)


def get_version(version: tuple[int, int, int] | None = None) -> str | None:
    if version is None:
        addon_path = Path(os.path.abspath(__file__)).parents[1]
        toml_path = addon_path / "blender_manifest.toml"
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
            return data.get("version", None)
    # NOTE: Since 4.2 this pattern is deprecated
    version_pattern = r'\((\d+), (\d+), (\d+)\)'
    match = re.match(version_pattern, str(version))
    return '.'.join(match.groups()) if match else None


def get_user_preferences():
    package = __package__.rsplit(".", maxsplit=1)[0]
    return bpy.context.preferences.addons[package].preferences


def enum_members_from_type(rna_type, prop_str):
    prop = rna_type.bl_rna.properties[prop_str]
    return [e.identifier for e in prop.enum_items]


def enum_members_from_instance(rna_item, prop_str):
    return enum_members_from_type(type(rna_item), prop_str)
