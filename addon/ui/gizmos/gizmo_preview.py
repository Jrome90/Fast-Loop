import bpy
import mathutils
from  bmesh.types import *
from ... import utils
from ... snapping.snapping import (
                                    SnapContext,
                                  )

class PreviewWidget( bpy.types.Gizmo):
    bl_idname = "FL_GT_Preview"

    # __slots__ = (
    #     'snap_context',
    #     'is_setup',
    #     'current_element',
    #     'current_position'      
    # )

    def __init__(self):
        self.snap_context = None
        self.is_setup = False
        self.current_element = None
        self.current_position = None

    def draw(self, context):
        pass
    #     if self.current_element is not None:
    #         utils.drawing.draw_points([self.current_position])
    #         self.current_element = None

    def test_select(self, context, mouse_co):
        if not self.is_setup:
          return -1

        else:
            active_object = context.active_object
            element_index, nearest_co = self.snap_context.do_snap(mouse_co, active_object)

            if element_index is not None:
                bm: BMesh = self.snap_context.snap_objects[active_object.name].bm
                bm.edges.ensure_lookup_table()
                edge = bm.edges[element_index]
                self.current_element = edge
                self.current_position = nearest_co

            context.area.tag_redraw()
        return -1
            

    def init_widget(self, context):
        active_object = context.active_object
        self.snap_context = SnapContext.get(context, context.evaluated_depsgraph_get(), context.space_data, context.region)
        self.snap_context.add_object(active_object)
        self.is_setup = True

    def removed_widget(self):
        SnapContext.remove()

    def setup(self):
        self.is_setup = False


class PreviewWidgetGroupBase(bpy.types.GizmoGroup):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}

    @classmethod
    def poll(cls, context):
        tools = context.workspace.tools
        mode = context.mode
        for tool in tools:
            if (tool.widget == cls.bl_idname) and (tool.mode == mode):
                break
        else:
            context.window_manager.gizmo_group_type_unlink_delayed(cls.bl_idname)
            return False
            
        return True


    def setup_(self, context, gizmo_name):
        self.widget = self.gizmos.new(gizmo_name)
        self.widget.init_widget(context)

    def __del__(self):
        if hasattr(self, "widget"):
            object.__getattribute__(self.widget, 'removed_widget')()


class PreviewWidgetGroup(PreviewWidgetGroupBase):
    bl_idname = "FL_GGT_Preview"
    bl_label = "Preview loop cuts"

    def setup(self, context):
        self.setup_(context, PreviewWidget.bl_idname)

        tools = context.workspace.tools
        for tool in tools:
            name = tool.idname 
            if name in {"fl.fast_loop_tool", "fl.fast_loop_classic_tool"}:
                if name == "fl.fast_loop_tool":
                    bpy.ops.fl.fast_loop('INVOKE_DEFAULT', invoked_by_tool=True)
                else:
                    bpy.ops.fl.fast_loop_classic('INVOKE_DEFAULT', invoked_by_tool=True)

                break
        