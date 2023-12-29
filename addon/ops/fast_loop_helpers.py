import bpy

from .. utils import  ops
from enum import Enum


class Mode(Enum):
    NONE = 0
    SINGLE = 4
    MULTI_LOOP = 8
    REMOVE_LOOP = 16
    SELECT_LOOP = 32
    EDGE_SLIDE = 64
  
enum_to_str = {Mode.SINGLE: 'SINGLE', Mode.MULTI_LOOP: 'MULTI_LOOP', Mode.REMOVE_LOOP: 'REMOVE_LOOP',  Mode.SELECT_LOOP: 'SELECT_LOOP', Mode.EDGE_SLIDE: 'EDGE_SLIDE', Mode.NONE: 'NONE'}
str_to_enum = {v: k for k, v in enum_to_str.items()}
def enum_to_mode_str(mode):
    return enum_to_str[mode]

def str_to_mode_enum(mode_str):
    return str_to_enum[mode_str]

def get_active_mode():
    return str_to_enum[ops.options().mode]

def mode_enabled(mode) -> bool:
    active_mode = get_active_mode()
    if mode in enum_to_str:
        return active_mode == mode
    return False

def get_options():
    context = bpy.context
    if hasattr(context.window_manager, "fl_options"):
        return context.window_manager.fl_options
    return None

def set_mode(mode):
    ops.set_option('mode', enum_to_str[mode])

# def get_options():
#     return options()
    
def set_option(option, value):
    return ops.set_option(option, value)

def get_props():
    return ops.fl_props()

def set_prop(prop, value):
    return ops.set_fl_prop(prop, value)