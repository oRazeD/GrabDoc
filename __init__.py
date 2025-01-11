import importlib

import bpy
from bpy.app.handlers import persistent

from .ui import register_baker_panels


#########################
# HANDLERS
#########################


@persistent
def load_post_handler(_dummy):
    register_baker_panels()


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

def unregister():
    for mod in modules:
        mod.unregister()
