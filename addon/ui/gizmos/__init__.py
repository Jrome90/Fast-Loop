import bpy
from . import gizmo_preview

classes = [
    gizmo_preview.FL_GGT_GizmoGroupBase,
    gizmo_preview.FL_GGT_FastLoop,
    gizmo_preview.FL_GGT_FastLoopClassic,
    #gizmo_preview.PreviewWidget,
            #gizmo_preview.PreviewWidgetGroup,
        ]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)