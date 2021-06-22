import bpy
from . import internal
from . import fast_loop
from . import fast_loop_classic
from . import edge_slide


classes = (
    internal.UI_OT_override_reset,
    internal.UI_OT_reset_operator,
    fast_loop.FastLoopOperator,
    fast_loop_classic.FastLoopClassicOperator,
    edge_slide.EdgeSlideOperator,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
