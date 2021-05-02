import bpy
from . import fast_loop
from . import fast_loop_classic
from. import edge_slide 

classes = (
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
