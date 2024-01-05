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

        options = utils.ops.options()
        if options is not None:

            box = layout.split()
            b = box.box()
            col = b.column()
            col.prop(options, "loop_position_override" , toggle=True, text="Position Override", icon='SHADERFX')
            
            pos_override_col = b.column()
            pos_override_col.enabled = True if options.loop_position_override else False
            prefs = utils.common.prefs()
            pos_override_col.prop(prefs, "interpolation_type")

            pos_override_col.operator("ui.overrride_reset", text="Reset", icon='FILE_REFRESH')
            pos_override_col.label(text="Loop Postitions")
            
            window_manager = context.window_manager
            if len(window_manager.Loop_Cut_Slots.loop_cut_slots) > 0:
                index = window_manager.Loop_Cut_Lookup_Index
                lc_slot = window_manager.Loop_Cut_Slots.loop_cut_slots[index]
                pos_override_col.template_list("FL_UL_Percentages", "", lc_slot, "loop_cut_slot", window_manager, "Loop_Cut_Slots_Index")

            box = layout.split()

            b = box.box()
            col = b.column(align=True)

            col.label(text="Snapping")

            if options is not None:
                col.prop(options, "use_snap_points", toggle=True, text="Toggle Snap Points", icon='SNAP_INCREMENT')
                col.prop(options, "lock_snap_points", toggle=True, text="Unlock Points" if options.lock_snap_points else "Lock Points", icon='LOCKED' if options.lock_snap_points else 'UNLOCKED')
                col.prop(options, "snap_divisions", slider=True)

                col.prop(options, "use_distance")
                use_dist_col = b.column()
                use_dist_col.enabled = True if options.use_distance else False
                use_dist_col.prop(options, "auto_segment_count")
                use_dist_col.prop(options, "snap_distance")
                use_dist_col.prop(options, "use_opposite_snap_dist", toggle=True)

                col = b.row(align=True)
                col.prop(options, "snap_left", toggle=True, text="Left")
                col.prop(options, "snap_center", toggle=True, text="Center")
                col.prop(options, "snap_right", toggle=True, text="Right")
        
            box = layout.split()
            b = box.box()
            col = b.column()
            unit_settings = bpy.context.scene.unit_settings
            unit_system = unit_settings.system
            col.label(text="Numeric Input Default Unit")
            if unit_system in {'METRIC'}:
                col.prop(prefs, "metric_unit_default")
            else:
                 col.prop(prefs, "imperial_unit_default")



            # box = layout.split()
            # b = box.box()

            # col = b.column(align=True)
            # col.label(text="Edge Flow")

            # preferences = utils.common.prefs()
            # if preferences is not None:
            #     col.prop(preferences, "set_edge_flow_enabled" , toggle=True, text="Set Edge Flow")

            #     box = col.box()

            #     row = box.row()
            #     row.prop(preferences, "tension", text= "Tension", expand = True)
            #     row = box.row()
            #     row.prop(preferences, "iterations", text= "Iterations", expand = True)
            #     row = box.row()
            #     row.prop(preferences, "min_angle", text= "Min Angle", expand = True)




class DrawLoopSliceUI():

    @classmethod
    def draw_loopslice_ui(cls, context, layout):        

        options = utils.ops.ls_options()
        if options is not None:
                
            box = layout
            b = box.box()
            col = b.column()

            col.prop(options, "edit_mode")
            col.prop(options, "mode")

            # box = layout.split()
            b = box.box()
            col = b.column()

            col.prop(options, "active_index", text="Current")
            col.prop(options, "slice_count", text="Count")

            b = box.box()
            col = b.column()
            col.prop(options, "use_split", text="Split")

            split_col = b.column()
            split_col.enabled = True if options.use_split else  False
            split_col.prop(options, "cap_sections", text="Cap Sections")
            split_col.prop(options, "gap_distance", text="Gap")

            b = box.box()
            col = b.column()
            col.label(text="Slider")
            col.prop(options, "active_position", text="Position")
            
            # box = layout.split()
            # b = box.box()

            # col = b.column(align=True)
            # col.label(text="Edge Flow")

            # preferences = utils.common.prefs()
            # if preferences is not None:
            #     col.prop(preferences, "set_edge_flow_enabled" , toggle=True, text="Set Edge Flow")

            #     box = col.box()

            #     row = box.row()
            #     row.prop(preferences, "tension", text= "Tension", expand = True)
            #     row = box.row()
            #     row.prop(preferences, "iterations", text= "Iterations", expand = True)
            #     row = box.row()
            #     row.prop(preferences, "min_angle", text= "Min Angle", expand = True)
