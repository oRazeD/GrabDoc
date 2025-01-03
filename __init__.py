import importlib


module_names = (
    "operators.core",
    "operators.material",
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
