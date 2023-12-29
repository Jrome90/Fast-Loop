import bpy
from bpy.types import Panel

from .. import utils 
from . ui import (DrawFastLoopUI, DrawLoopSliceUI)

class VIEW3D_PT_FastLoopToolPanel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Edit'
    bl_context = "mesh_edit"
    bl_label = "Fast Loop"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        DrawFastLoopUI.draw_fastloop_ui(context, self.layout)


class VIEW3D_PT_FastLoopSetFlowOptions(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    bl_context = ".set_flow_options"
    bl_label = "Set Flow Options"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.ui_units_x  = 7.0
        preferences = utils.common.prefs()
        col = layout.column()        
        # col.label( text = "Set Flow Options" )
        col.prop(preferences, "set_edge_flow_enabled" , text = "Set Flow" , expand = True, toggle=True )

        box = col.box()

        row = box.row()
        row.prop(preferences, "tension", text= "Tension", expand = True)
        row = box.row()
        row.prop(preferences, "iterations", text= "Iterations", expand = True)
        row = box.row()
        row.prop(preferences, "min_angle", text= "Min Angle", expand = True)


class VIEW3D_PT_HUDSettings(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    bl_category = "Tool"
    bl_context = ".hud_settings"
    bl_label = "HUD Settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        prefs = utils.common.prefs()
        layout = self.layout

        layout.ui_units_x  = 5.0
        layout.label(text="Segment Bar")

        layout_split = layout.split()
        b = layout_split.box()
        col = b.column()
        col.prop(prefs, "show_bar", text="Show" if not utils.common.prefs().show_bar else "Hide", toggle=True)
        col.prop(prefs, "show_percents", text="Show Percents" if not utils.common.prefs().show_percents else "Hide Percents", toggle=True)

        layout.label(text="Display Units")
        layout_split = layout.split()
        b = layout_split.box()
        col = b.column()
        units_to_display = utils.ui.get_units_to_display(True)
        for unit in units_to_display:
            col.prop(prefs, unit, toggle=True)


class VIEW3D_PT_LoopSlicePanel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Edit'
    bl_context = "mesh_edit"
    bl_label = "Loop Slice"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        DrawLoopSliceUI.draw_loopslice_ui(context, self.layout)