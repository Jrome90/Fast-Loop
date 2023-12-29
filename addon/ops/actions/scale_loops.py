from copy import copy
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fast_loop import FastLoopOperator

from mathutils import Vector

from ...utils.ops import cursor_warp
from ...utils import draw_2d, ui

from ..edge_data import EdgeData
from ..fast_loop_actions import (DrawLoopsMixin, BaseAction)


class ScaleLoopsAction(DrawLoopsMixin, BaseAction):
    def __init__(self, context, bl_event) -> None:
        self.context: FastLoopOperator = context
        context.start_mouse_pos_x = bl_event.mouse_x
        context.event_handler.numeric_input_begin(bl_event, self.on_numeric_input_changed)
        self.mouse_coords = (bl_event.mouse_region_x, bl_event.mouse_region_y)
        self.prev_numeric_input_copy = copy(context.last_numeric_input_results)
        self.prev_scale_value = context.scale
        self._mouse_updated = False


    def enter(self):
        if self.context.current_edge is None:
            self.context.report({'INFO'}, 'No edge near mouse. Cannot enter scale mode.')
            self.context.pop_action()
            return

        self.context.is_scaling = True
        self.context.report({'INFO'}, 'Enter to confirm. Esc to cancel.')


    def exit(self):
        self.context.is_scaling = False
        self.context.event_handler.numeric_input_end()
    

    def update(self):
        if self._mouse_updated:
            self.context.last_numeric_input_results = None
            self._mouse_updated = False


    def handle_input(self, bl_context, bl_event):
       
        handled = False
        # Cancelled action. Revert to prev values
        if bl_event.type in {'ESC'} and bl_event.value == 'PRESS':
            self.context.last_numeric_input_results = copy(self.prev_numeric_input_copy)
            self.context.scale = self.prev_scale_value
            self.context.pop_action()
            handled = True

        elif bl_event.type in {'RET'} and bl_event.value == 'PRESS':
            self.context.pop_action()
            handled = True
    
        return handled
    

    def on_mouse_move(self, bl_event):
        cursor_warp(bl_event)
        self.mouse_coords = (bl_event.mouse_region_x, bl_event.mouse_region_y)
        delta_x = bl_event.mouse_x - bl_event.mouse_prev_x
        delta_x *= 0.001 if bl_event.shift else 0.01
        self.context.scale += delta_x
        self.update_scale(self.context.scale)
        if self.context.update_loops():
            props = self.context.get_all_props_no_snap()
            self.context.edge_data = EdgeData(self.context.loop_data, props)
            self.context.start_mouse_pos_x = bl_event.mouse_x
            self._mouse_updated = True
            
        self.context.update_slider()


    def handle_modal_event(self, bl_context, modal_event, bl_event):
        handled = False
        if modal_event == "Loop Spacing":
            self.context.pop_action()
            handled = True
        return handled

    
    def draw_ui(self, bl_context):
        if self.context.area_invoked != bl_context.area:
            return

        if self.context.slider_widget is not None:
            self.context.slider_widget.draw()

        self.draw_scale_text(bl_context)
        self.context.main_panel_hud.draw()   
    

    def draw_scale_text(self, context):
        if len(self.context.edge_data.points) < 1:
            return 

        position = Vector((self.mouse_coords))
        position[0] += 5 * ui.get_ui_scale()
        position[1] -= 50 * ui.get_ui_scale()
        
        text_size = 12 * ui.get_ui_scale()
        if self.context.last_numeric_input_results is None :
            draw_2d.draw_text_on_screen(f"{100*self.context.scale:.3g} %", position, text_size)
        else:
            value_str = ""
            input_str = self.context.last_numeric_input_results.input_string
            if self.context.last_numeric_input_results.is_distance:
                value_str += "Distance: " + input_str
           
            draw_2d.draw_text_on_screen(value_str, position, text_size)

    def on_numeric_input_changed(self, results):

        self.context.last_numeric_input_results = copy(results)
        
        if results.value is None:
            return
        self.context.scale = self.context.calculate_scale_value()
    
        if self.context.update_loops():
            props = self.context.get_all_props_no_snap()
            self.context.edge_data = EdgeData(self.context.loop_data, props)
            self.context.ensure_bmesh_(self.context.active_object)
        
        self.update_scale(self.context.scale)
        self.context.update_slider()


    def update_scale(self, scale_value):
        if self.context.last_numeric_input_results is None or not self.context.last_numeric_input_results.is_distance:
            self.context.multi_loop_props.loop_space_value = f"{100*scale_value:.3g} %"
        else:
            self.context.multi_loop_props.loop_space_value = self.context.last_numeric_input_results.input_string
    
