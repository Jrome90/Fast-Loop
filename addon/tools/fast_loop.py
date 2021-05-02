import os
import bpy

from ... addon import utils


class FL_ToolBase(bpy.types.WorkSpaceTool):
    bl_space_type='VIEW_3D'
    bl_context_mode='EDIT_MESH'
    bl_widget  = "FL_GGT_Preview"
    

    @classmethod
    def draw_settings( cls ,context, layout, tool):
        region_type = context.region.type

        if region_type == 'UI' :
            cls.draw_settings_ui(context , layout , tool)
        elif region_type == 'WINDOW' :
            cls.draw_settings_ui(context , layout , tool)
        elif region_type == 'TOOL_HEADER' :
            cls.draw_settings_toolheader(context , layout , tool)

    
    @classmethod
    def draw_settings_toolheader(cls, context, layout, tool):        
        pass

    
    @classmethod
    def draw_settings_ui(cls, context, layout, tool):        
        pass

        
class FL_FastLoop(FL_ToolBase):

    bl_idname = "fl.fast_loop_tool"
    bl_label = "Fast Loop"
    bl_description = ( "Add loop cuts or modify existing ones" )
    bl_icon = os.path.join(os.path.join(os.path.dirname(__file__), "icons") , "fl.fast_loop")

    
    @classmethod
    def draw_settings_toolheader(cls, context, layout, tool):        

        row = layout.row(align=True)

        options = utils.ops.options()
        if options is not None:
            row.prop(options, "mode", toggle=True, expand=True,)

        popover_kw = {"space_type": 'VIEW_3D', "region_type": 'UI', "category": "Tool"}
        layout.popover_group(context=".set_flow_options", **popover_kw)

    
    @classmethod
    def draw_settings_ui(cls, context, layout, tool):        

        col = layout.column(align=True)

        options = utils.ops.options()
        if options is not None:
            col.prop(options, "mode", toggle=True, expand=True,)

            box = layout.split()
            b = box.box()

            col = b.column(align=True)
            col.label(text="Options")

            col.prop(options, "flipped" , toggle=True, text="Flip", icon='ARROW_LEFTRIGHT')
            col.prop(options, "use_even" , toggle=True, text="Even", icon='SNAP_MIDPOINT')
            col.prop(options, "multi_loop_offset" , toggle=True, text="Multi Loop Offset", icon='ANCHOR_LEFT')

            box = layout.split()

            b = box.box()
            col = b.column(align=True)

            col.label(text="Muli Loop Options")

            options = utils.ops.options()
            if options is not None:
                col.prop(options, "segments", text="Segments")
                col.prop(options, "scale", text="Scale")

            box = layout.split()

            b = box.box()
            col = b.column(align=True)

            col.label(text="Snapping")

            options = utils.ops.options()
            if options is not None:
                col.prop(options, "use_snap_points" , toggle=True, text="Turn off Snapping" if options.use_snap_points else "Turn on Snapping", icon='SNAP_INCREMENT')
                col.prop(options, "lock_snap_points" , toggle=True, text="Unlock Points" if options.lock_snap_points else "Lock Points", icon='LOCKED' if options.lock_snap_points else 'UNLOCKED')
                col.prop(options, "snap_divisions", slider=True)
                col.prop(options, "snap_factor")
