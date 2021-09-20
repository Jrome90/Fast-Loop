
from functools import partial

import bpy
from  bmesh.types import *
from ... import utils
from ... tools.fast_loop import FL_FastLoop
from ... tools.fast_loop_classic import FL_FastLoopClassic       

# def get_context_overrides(*objects):

#     def get_base_context():
#         window = bpy.context.window_manager.windows[0]
#         area = None
#         for area in window.screen.areas:
#             if area.type == 'VIEW_3D':
#                 area = area
#                 break
#         return {'window': window, 'screen': window.screen, 'area' : area, "workspace" : window.workspace}

#     context = get_base_context()
#     context['object'] = objects[0]
#     context['active_object'] = objects[0]
#     context['selected_objects'] = objects
#     context['selected_editable_objects'] = objects
#     return context

def execute_operator(operator):
    active_obj = bpy.context.scene.view_layers[0].objects.active
    context_override =  utils.ops.get_context_overrides(active_obj)

    if operator == 'fl.fast_loop':
         bpy.ops.fl.fast_loop(context_override, 'INVOKE_DEFAULT', invoked_by_tool=True)

    elif operator == 'fl.fast_loop_classic':
         bpy.ops.fl.fast_loop_classic(context_override, 'INVOKE_DEFAULT', invoked_by_tool=True)


class FL_GGT_GizmoGroupBase(bpy.types.GizmoGroup):
    bl_label = "(internal)"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}

    def get_tool(self):
        raise NotImplementedError

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

    def setup(self, context):
        tool = self.get_tool()

        tools = bpy.context.workspace.tools
        current_active_tool = tools.from_space_view3d_mode(bpy.context.mode).idname
        if current_active_tool == tool.bl_idname:
            bpy.app.timers.register(partial(execute_operator, tool.get_operator()), first_interval=0.01)
        

    # def __del__(self):
    #     if hasattr(self, "widget"):
    #         object.__getattribute__(self.widget, 'removed_widget')()



class FL_GGT_FastLoop(FL_GGT_GizmoGroupBase):
    tool = FL_FastLoop
    bl_idname = tool.bl_widget
    bl_label = "Fast Loop GG"

    def get_tool(self):
        return __class__.tool

class FL_GGT_FastLoopClassic(FL_GGT_GizmoGroupBase):
    tool = FL_FastLoopClassic
    bl_idname = tool.bl_widget
    bl_label = "Fast Loop Classic GG"

    def get_tool(self):
        return __class__.tool
        