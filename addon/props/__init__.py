import bpy
from . import addon
from . import prefs

from .. keymaps.modal_keymapping import save_keymap

classes = (
    addon.AddonProps,
    addon.ModalKeymapDisplay,
    prefs.AddonPrefs,
    addon.Loop_Cut,
    addon.Loop_Cut_Slot_Prop,
    addon.Loop_Cut_Slots_Prop,
    addon.FL_Props,
    addon.FL_Options,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.WindowManager.example = bpy.props.PointerProperty(type=addon.AddonProps)
    bpy.types.WindowManager.keymap_strings = bpy.props.PointerProperty(type=addon.ModalKeymapDisplay)

    bpy.types.Scene.fl_options = bpy.props.PointerProperty(type=addon.FL_Options)
    bpy.types.Scene.fl_props = bpy.props.PointerProperty(type=addon.FL_Props)
    
    bpy.types.Scene.Loop_Cut_Slots = bpy.props.PointerProperty(type=addon.Loop_Cut_Slots_Prop)
    bpy.types.Scene.Loop_Cut_Slots_Index = bpy.props.IntProperty(name='Loop Index', default=0)
    bpy.types.Scene.Loop_Cut_Lookup_Index = bpy.props.IntProperty(name='Loop Cut Slots Lookup Index', default=0)

def unregister():
    del bpy.types.WindowManager.example
    del bpy.types.WindowManager.keymap_strings
    del bpy.types.Scene.fl_options
    del bpy.types.Scene.fl_props
    del bpy.types.Scene.Loop_Cut_Slots
    del bpy.types.Scene.Loop_Cut_Slots_Index
    del bpy.types.Scene.Loop_Cut_Lookup_Index

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
