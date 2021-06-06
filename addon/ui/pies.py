import bpy
from .. import utils

class FastLoopPie(bpy.types.Menu):
    bl_idname = 'FL_MT_FastLoop_Pie'
    bl_label = 'Fast Loop Pie'

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        # Left
        self.menu_modes(pie, context)

        # Right
        self.menu_snapping(pie, context)

        # Bottom
        self.menu_edge_flow(pie, context)
      
        # Top
        self.menu_options(pie, context)


        # 9 - TOP - RIGHT
        pie.separator()
        self.exit_button(pie, context)


    def menu_modes(self, pie, context):
        box = pie.split()

        b = box.box()
        col = b.column()

        col.label(text="Mode")

        options = utils.ops.options()
        if options is not None:
            col.prop(options, "mode", toggle=True, expand=True,)
        
        col.separator()
        
        sub_mode = col.box()
        sub_mode.label(text="Sub Mode")

        sub_mode.prop(options, 'insert_midpoint', toggle=True, text="Midpoint", icon='SNAP_MIDPOINT')
        sub_mode.prop(options, 'perpendicular', toggle=True, text="Perpendicular", icon='SNAP_PERPENDICULAR')
        sub_mode.prop(options, 'mirrored', toggle=True, text="Mirrored", icon='MOD_MIRROR')

    def menu_snapping(self, pie, context):
        box = pie.split()

        b = box.box()
        col = b.column(align=True)

        col.label(text="Snapping")

        options = utils.ops.options()
        if options is not None:
            col.prop(options, "use_snap_points" , toggle=True, text="Turn off Snapping" if options.use_snap_points else "Turn on Snapping", icon='SNAP_INCREMENT')
            col.prop(options, "lock_snap_points" , toggle=True, text="Unlock Points" if options.lock_snap_points else "Lock Points", icon='LOCKED' if options.lock_snap_points else 'UNLOCKED')
            col.prop(options, "snap_divisions", slider=True)
            col.prop(options, "snap_factor")

    
    def menu_options(self, pie, context):
        box = pie.split()
        b = box.box()
        col = b.column(align=True)

        col.label(text="Options")

        options = utils.ops.options()
        if options is not None:
            col.prop(options, "select_new_edges", toggle=True, text="Select New Edge Loops", icon='RESTRICT_SELECT_OFF')
            col.prop(options, "flipped", toggle=True, text="Flip", icon='ARROW_LEFTRIGHT')
            col.prop(options, "use_even", toggle=True, text="Even", icon='SNAP_MIDPOINT')
            col.prop(options, "multi_loop_offset", toggle=True, text="Multi Loop Offset",)
    
    def exit_button(self, pie, context):
        box = pie.split()
        box.ui_units_y = 3
        
        options = utils.ops.options()
        if options is not None:
            box.prop(options, "cancel", text="Exit", icon='CANCEL', emboss=True)
    
    def menu_edge_flow(self, pie, context):
        box = pie.split()
        b = box.box()
        col = b.column(align=True)

        col.label(text="Edge Flow")
        preferences = utils.common.prefs()

        if preferences is not None:
            col.prop(preferences, "set_edge_flow_enabled" , toggle=True, text="Set Edge Flow")
