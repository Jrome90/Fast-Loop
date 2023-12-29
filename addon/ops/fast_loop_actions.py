from __future__ import annotations
from abc import ABCMeta
from contextlib import suppress

from ..utils.common import prefs
from ..utils import draw_3d


class DrawLoopsMixin():
   def draw_3d(self, bl_context):
        color = prefs().loop_color
        line_width = prefs().line_width
        transposed_array = list(map(list, zip(*self.context.loop_draw_points)))
        for loop in transposed_array:
            if self.context.is_loop:
                draw_3d.draw_line_loop(loop, color, line_width, depth_test=prefs().occlude_lines)
            else:
                # TODO find out and fix the cause of a value exception after placing loops while used selected edges is enabled.
                with suppress(ValueError):
                    draw_3d.draw_line(loop, color, line_width, depth_test=prefs().occlude_lines)
            
            if prefs().draw_loop_vertices:
                draw_3d.draw_points(loop, prefs().vertex_color, prefs().vertex_size, depth_test=prefs().occlude_points)

        start_pos = self.context.loop_data.get_active_loop_endpoints().start if self.context.loop_data is not None else None
        if self.context.use_even and start_pos is not None:
            draw_3d.draw_point(start_pos, color=(1.0, 0.0, 0.0, 0.4))
            
        if self.context.is_single_edge and self.context.loop_draw_points:
            
            for loop in self.context.loop_draw_points:
                with suppress(ValueError):
                    draw_3d.draw_points(loop, prefs().vertex_color, prefs().vertex_size, depth_test=prefs().occlude_points)

class DrawDirectionArrowMixin():
    def draw_3d(self, bl_context):
        for arrow in self.context.draw_direction_arrow_lines:
            arrow.draw()
    
    def draw_ui(self, bl_context):
        for arrow in self.context.draw_direction_arrow_lines:
            arrow.draw_2d()


class Actions():
    action_stack = []

    @property
    def current_action(self):
        return self.action_stack[-1]


    def switch_action(self, action):
        self.action_stack.pop().exit()
        self.push_action(action)


    def push_action(self, action):
        self.action_stack.append(action)
        action.enter()


    def pop_action(self):
        self.action_stack.pop().exit()
        self.current_action.enter()


class BaseAction(metaclass=ABCMeta):

    def enter(self):
        pass
    
    def exit(self):
        pass

    def update(self):
        pass

    def handle_input(self, bl_context, bl_event):
        pass

    def on_mouse_move(self, bl_event):
        pass
    
    def draw_3d(self, bl_context):
        pass

    def draw_ui(self, bl_context):
        pass

    
# class VertexSnapSelectAction(BaseAction):

#     def __init__(self, context) -> None:
#         self.context: FastLoopOperator = context

    
#     def enter(self):
#         self.context.snap_context.enable_vertex_sel_mode()


#     def exit(self):
#         self.context.snap_context.disable_vertex_sel_mode()

#     def update(self):
#         pass


#     def handle_input(self, bl_context, bl_event):
#         handled = False
#         if bl_event.type == 'PERIOD'and bl_event.value == 'RELEASE':
#             self.context.pop_action()
#             handled = True
        
#         return handled
