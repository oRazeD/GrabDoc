import importlib

import bpy
from bpy.app.handlers import persistent

from .ui import register_baker_panels
from .preferences import generate_channel_pack_enums


#########################
# BOOTSTRAPPER
#########################


def refresh_baker_dependencies():
    """Refresh all dynamic GrabDoc classes or properties."""
    register_baker_panels()
    generate_channel_pack_enums()


#########################
# HANDLERS
#########################


@persistent
def load_post_handler(_dummy) -> None:
    if not bpy.data.filepath:
        return
    refresh_baker_dependencies()


@persistent
def save_pre_handler(_dummy) -> None:
    if not bpy.context.scene.gd.preview_state:
        return
    bpy.ops.grabdoc.baker_preview_exit()


#########################
# REGISTRATION
#########################


module_names = (
    "operators.core",
    "operators.material",
    "operators.marmoset",
    "preferences",
    "ui"
)

modules = []
for module_name in module_names:
    if module_name in locals():
        modules.append(importlib.reload(locals()[module_name]))
    else:
        modules.append(importlib.import_module(f".{module_name}", __package__))

def register():
    for mod in modules:
        mod.register()

    bpy.app.handlers.load_post.append(load_post_handler)
    bpy.app.handlers.save_pre.append(save_pre_handler)

def unregister():
    for mod in modules:
        mod.unregister()
