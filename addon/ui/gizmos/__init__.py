import bpy
from . import gizmo_snapping

classes = [
    gizmo_snapping.RP_GGT_SnapGizmoGroup,
        ]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)