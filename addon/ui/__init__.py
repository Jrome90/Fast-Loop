import bpy
from . import panels
from . import ui

classes = (
    panels.VIEW3D_PT_FastLoopSetFlowOptions,
    panels.VIEW3D_PT_HUDSettings,
    ui.FL_UL_Percentages,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    
def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
