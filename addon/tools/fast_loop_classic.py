import os
from ... addon import utils
from . fast_loop import FL_ToolBase

class FL_FastLoopClassic(FL_ToolBase):

    bl_idname = "fl.fast_loop_classic_tool"
    bl_label = "Fast Loop Classic"
    bl_description = ( "Add loop cuts or modify existing ones.")
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "fl.fast_loop_classic")

    
    @classmethod
    def draw_settings_toolheader(cls, context, layout, tool):        

        popover_kw = {"space_type": 'VIEW_3D', "region_type": 'UI', "category": "Tool"}
        layout.popover_group(context=".set_flow_options", **popover_kw)


