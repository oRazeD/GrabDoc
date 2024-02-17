bl_info = {
    "name": "GrabDoc",
    "author": "Ethan Simon-Law",
    "location": "3D View > Sidebar > GrabDoc",
    # NOTE: Also change:
    # - Update check in preferences.py
    # - Panel version in generic.py
    "version": (1, 4, 1),
    "blender": (4, 0, 2),
    "tracker_url": "https://discord.com/invite/wHAyVZG",
    "category": "3D View"
}


import importlib


module_names = (
    "operators.operators",
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

def unregister():
    for mod in modules:
        mod.unregister()
