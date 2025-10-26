import importlib

import bpy
from bpy.app.handlers import persistent

from .ui import GRABDOC_PT_Baker
from .preferences import generate_pack_enums
from .utils.baker import get_baker_collections


#########################
# BOOTSTRAPPER
#########################


def init_baker_dependencies():
    """Refresh all dynamic GrabDoc classes or
    properties dependent on the `UIList` structure."""
    register_bakers()
    generate_pack_enums()


def register_bakers():
    """Unregister and re-register all bakers and their respective panels."""
    for cls in GRABDOC_PT_Baker.__subclasses__():
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            continue
    for cls in subclass_baker_panels():
        bpy.utils.register_class(cls)


def subclass_baker_panels():
    """Creates panels for every item in the baker
    `CollectionProperty`s via dynamic subclassing."""
    baker_classes = []
    for baker_prop in get_baker_collections():
        for baker in baker_prop:
            baker.initialize()
            class_name = f"GRABDOC_PT_{baker.ID}_{baker.index}"
            panel_cls = type(class_name, (GRABDOC_PT_Baker,), {})
            panel_cls.baker = baker
            baker_classes.append(panel_cls)
    return baker_classes


#########################
# HANDLERS
#########################


@persistent
def load_post_handler(_dummy) -> None:
    if not bpy.data.filepath:
        return
    init_baker_dependencies()


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
