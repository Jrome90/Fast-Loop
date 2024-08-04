from ... import __package__ as base_package

import bpy


def prefs():
    return bpy.context.preferences.addons[base_package].preferences

def set_addon_preference(option, value)-> bool:
    if hasattr(prefs(), option):
        setattr(prefs(), option, value)
        return True
    return False

def get_blender_version()-> tuple:
    return bpy.app.version

def min_ver_4_2()-> bool:
    version = get_blender_version()
    major = version[0]
    minor = version[1]
    return (major == 4 and minor >= 2) or (major > 4)

def is_modal_running(operator: str):
    op = bpy.context.window.modal_operators.get(operator, None)
    return op is not None
       