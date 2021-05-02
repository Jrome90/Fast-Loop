import bpy
from . import addon
from . import prefs


classes = (
    addon.AddonProps,
    prefs.AddonPrefs,
    addon.FL_Props,
    addon.FL_Options,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.WindowManager.example = bpy.props.PointerProperty(type=addon.AddonProps)
    bpy.types.Scene.fl_options = bpy.props.PointerProperty(type=addon.FL_Options)
    bpy.types.Scene.fl_props = bpy.props.PointerProperty(type=addon.FL_Props)


def unregister():
    del bpy.types.WindowManager.example
    del bpy.types.Scene.fl_options
    del bpy.types.Scene.fl_props

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
