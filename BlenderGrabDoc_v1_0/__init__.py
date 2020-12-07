bl_info = {
    "name":"Blender GrabDoc",
    "author":"Ethan Simon-Law",
    "location": "View3D > Sidebar > GrabDoc Tab",
    "version":(1, 0, 0),
    "blender":(2, 83, 0),
    "category":"3D View"}


import bpy
import importlib


module_names = ("ui",
                "operators",
                "prefs")
modules = []

for module_name in module_names:
    if module_name in locals():
        modules.append(importlib.reload(locals()[module_name]))
    else:
        modules.append(importlib.import_module("." + module_name, package=__package__))

def register():
    for mod in modules:
        mod.register()

def unregister():
    for mod in modules:
        mod.unregister()


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