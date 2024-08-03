import os
import bpy

from .. ui.ui import DrawFastLoopUI

class FL_ToolBase(bpy.types.WorkSpaceTool):
    bl_space_type='VIEW_3D'
    bl_context_mode='EDIT_MESH'

    def get_operator():
        raise NotImplementedError

    @classmethod
    def draw_settings( cls ,context, layout, tool):
        region_type = context.region.type

        if region_type == 'UI' :
            cls.draw_settings_ui(context, layout)
        elif region_type == 'WINDOW' :
            cls.draw_settings_ui(context, layout)
        elif region_type == 'TOOL_HEADER' :
            cls.draw_settings_toolheader(context, layout, tool)

    
    @classmethod
    def draw_settings_toolheader(cls, context, layout, tool):
        pass

    
    @classmethod
    def draw_settings_ui(cls, context, layout):
        pass

        
class FL_FastLoop(FL_ToolBase, DrawFastLoopUI):
    bl_idname = "fl.fast_loop_tool"
    bl_label = "Fast Loop"
    bl_description = ( "Add loop cuts or modify existing ones" )
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "fl.fast_loop")
    bl_keymap = (("exe.fast_loop",{"type": 'MOUSEMOVE', "value": 'ANY' },{"properties": []}),)
    
    @classmethod
    def draw_settings_toolheader(cls, context, layout, tool):
        

        popover_kw = {"space_type": 'VIEW_3D', "region_type": 'UI', "category": "Tool"}
        layout.popover_group(context=".set_flow_options", **popover_kw)

        popover_kw = {"space_type": 'VIEW_3D', "region_type": 'UI', "category": "Tool"}
        layout.popover_group(context=".hud_settings", **popover_kw)

    
    @classmethod
    def draw_settings_ui(cls, context, layout):
        cls.draw_fastloop_ui(context, layout)

    
    def get_operator():
        return 'fl.fast_loop'