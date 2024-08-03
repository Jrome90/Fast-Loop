from ... import __package__ as base_package

import bpy

def prefs():
    return bpy.context.preferences.addons[base_package].preferences

def set_addon_preference(option, value)-> bool:
    if hasattr(prefs(), option):
        setattr(prefs(), option, value)
        return True
    return False