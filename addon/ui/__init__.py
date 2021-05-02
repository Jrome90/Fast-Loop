import bpy
from . import panels
from . import pies

classes = (
    panels.VIEW3D_PT_FastLoopSetFlowOptions,
    pies.FastLoopPie,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
