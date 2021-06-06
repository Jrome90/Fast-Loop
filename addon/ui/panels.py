import bpy
from bpy.types import Context, Panel
from bl_ui.space_toolsystem_common import ToolSelectPanelHelper, ToolActivePanelHelper

from .. import utils 
from . ui import DrawFastLoopUI

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

        preferences = utils.common.prefs()

        col = layout.column()        
        col.label( text = "Set Flow Options" )
        col.prop(preferences, "set_edge_flow_enabled" , text = "Set Flow" , expand = True, toggle=True )

        box = col.box()

        row = box.row()
        row.prop(preferences, "tension", text= "Tension", expand = True)
        row = box.row()
        row.prop(preferences, "iterations", text= "Iterations", expand = True)
        row = box.row()
        row.prop(preferences, "min_angle", text= "Min Angle", expand = True)