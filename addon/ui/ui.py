import bpy

from .. import utils 


class FL_UL_Percentages(bpy.types.UIList):
    def __init__(self):
        super().__init__()
        self.use_filter_show =  False
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            col = layout.column()
            col.prop(item, item.get_method().lower(), text=f"{index}", emboss=False)

        elif self.layout_type in {'GRID'}:
            pass


class DrawFastLoopUI():

    @classmethod
    def draw_fastloop_ui(cls, context, layout):        

        col = layout.column(align=True)

        options = utils.ops.options()
        if options is not None:
            col.prop(options, "mode", toggle=True, expand=True,)


            sub_mode = col.box()
            sub_mode.label(text="Sub Mode")

            sub_mode.prop(options, 'insert_midpoint', toggle=True, text="Midpoint", icon='SNAP_MIDPOINT')
            sub_mode.prop(options, 'perpendicular', toggle=True, text="Perpendicular", icon='SNAP_PERPENDICULAR')
            sub_mode.prop(options, 'mirrored', toggle=True, text="Mirrored", icon='MOD_MIRROR')


            box = layout.split()
            b = box.box()

            col = b.column(align=True)
            col.label(text="Options")

            col.prop(options, "select_new_edges" , toggle=True, text="Select New Edge Loops", icon='RESTRICT_SELECT_OFF')
            col.prop(options, "flipped" , toggle=True, text="Flip", icon='ARROW_LEFTRIGHT')
            col.prop(options, "use_even" , toggle=True, text="Even", icon='SNAP_MIDPOINT')

            box = layout.split()

            b = box.box()
            col = b.column(align=True)

            col.label(text="Muli Loop Options")

            options = utils.ops.options()
            if options is not None:
                col.prop(options, "segments", text="Loops")
                col.prop(options, "scale", text="Scale")
                col.prop(options, "multi_loop_offset" , toggle=True, text="Multi Loop Offset", icon='ANCHOR_LEFT')
                

            box = layout.split()
            b = box.box()
            col = b.column()
            col.prop(options, "loop_position_override" , toggle=True, text="Custom Values", icon='SHADERFX')

            prefs = utils.common.prefs()
            col.prop(prefs, "interpolation_type")

            col.operator("ui.overrride_reset", text="Reset", icon='FILE_REFRESH')
            col.label(text="Loop Postitions")
            
            scene = bpy.context.scene
            index = scene.Loop_Cut_Lookup_Index
            lc_slot = scene.Loop_Cut_Slots.loop_cut_slots[index]
            col.template_list("FL_UL_Percentages", "", lc_slot, "loop_cut_slot", bpy.context.scene, "Loop_Cut_Slots_Index")

            box = layout.split()

            b = box.box()
            col = b.column(align=True)

            col.label(text="Snapping")

            if options is not None:
                col.prop(options, "use_snap_points" , toggle=True, text="Turn off Snapping" if options.use_snap_points else "Turn on Snapping", icon='SNAP_INCREMENT')
                col.prop(options, "lock_snap_points" , toggle=True, text="Unlock Points" if options.lock_snap_points else "Lock Points", icon='LOCKED' if options.lock_snap_points else 'UNLOCKED')
                col.prop(options, "snap_divisions", slider=True)
                col.prop(options, "snap_factor")

            
            box = layout.split()
            b = box.box()

            col = b.column(align=True)
            col.label(text="Edge Flow")

            preferences = utils.common.prefs()
            if preferences is not None:
                col.prop(preferences, "set_edge_flow_enabled" , toggle=True, text="Set Edge Flow")
