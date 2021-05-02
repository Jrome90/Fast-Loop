import bpy

from . import common

def get_m_button_map(button):
        prefs = common.prefs()
        if button == 'LEFTMOUSE':
            return 'LEFTMOUSE' if not prefs.use_rcs else 'RIGHTMOUSE'

        if button == 'RIGHTMOUSE':
            return 'RIGHTMOUSE' if not prefs.use_rcs else 'LEFTMOUSE'

def fl_props():
    context = bpy.context
    if hasattr(context.scene, "fl_props"):
        return context.scene.fl_props
    return None

def set_fl_prop(property, value)-> bool:
    context = bpy.context
    if hasattr(context.scene, "fl_props"):
        if hasattr(context.scene.fl_props, property):
            setattr(context.scene.fl_props, property, value)
            return True
    return False

def options():
    context = bpy.context
    if hasattr(context.scene, "fl_options"):
        return context.scene.fl_options
    return None

def set_option(option, value)-> bool:
    context = bpy.context
    if hasattr(context.scene, "fl_options"):
        if hasattr(context.scene.fl_options, option):
            setattr(context.scene.fl_options, option, value)
            return True
    return False
