import bpy
from . import internal
from . import fast_loop
from . import edge_slide
from . import edge_constraint
from . abs_edge_loop import OT_Absolute_Edge_Loop


classes = (
    internal.FastLoopRunner,
    internal.UI_OT_override_reset,
    internal.UI_OT_reset_operator,
    internal.UI_OT_keymap_input_operator,
    internal.UI_OT_save_keymap_operator,
    internal.UI_OT_distance_display_settings_operator,
    internal.UI_OT_AltNavDetected_operator,
    fast_loop.FastLoopOperator,
    edge_slide.EdgeSlideOperator,
    edge_constraint.EdgeConstraintTranslationOperator,
    OT_Absolute_Edge_Loop,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
