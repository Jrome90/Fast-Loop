import bpy
from . import addon
from . import prefs

classes = (
    addon.AddonProps,
    addon.ModalKeymapDisplay,
    prefs.AddonPrefs,
    addon.Loop_Cut,
    addon.Loop_Cut_Slot_Prop,
    addon.Loop_Cut_Slots_Prop,
    addon.FL_Props,
    addon.FL_Options,
    addon.SharedSnapData,

    # addon.LoopSlice_Options,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.WindowManager.example = bpy.props.PointerProperty(type=addon.AddonProps)
    bpy.types.WindowManager.keymap_strings = bpy.props.PointerProperty(type=addon.ModalKeymapDisplay)

    bpy.types.WindowManager.fl_options = bpy.props.PointerProperty(type=addon.FL_Options)
    bpy.types.WindowManager.fl_props = bpy.props.PointerProperty(type=addon.FL_Props)
    
    bpy.types.WindowManager.Loop_Cut_Slots = bpy.props.PointerProperty(type=addon.Loop_Cut_Slots_Prop)
    bpy.types.WindowManager.Loop_Cut_Slots_Index = bpy.props.IntProperty(name='Loop Index', default=0)
    bpy.types.WindowManager.Loop_Cut_Lookup_Index = bpy.props.IntProperty(name='Loop Cut Slots Lookup Index', default=0)

    bpy.types.WindowManager.Shared_Snap_Data = bpy.props.PointerProperty(type=addon.SharedSnapData)

    # bpy.types.WindowManager.ls_options = bpy.props.PointerProperty(type=addon.LoopSlice_Options)

def unregister():
    del bpy.types.WindowManager.example
    del bpy.types.WindowManager.keymap_strings
    del bpy.types.WindowManager.fl_options
    del bpy.types.WindowManager.fl_props
    del bpy.types.WindowManager.Loop_Cut_Slots
    del bpy.types.WindowManager.Loop_Cut_Slots_Index
    del bpy.types.WindowManager.Loop_Cut_Lookup_Index
    del bpy.types.WindowManager.Shared_Snap_Data
    # del bpy.types.WindowManager.ls_options

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
