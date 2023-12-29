from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fast_loop import FastLoopOperator

from ...utils.ops import get_m_button_map as btn
from ..fast_loop_actions import BaseAction

class RightClickAction(BaseAction):
    
    def __init__(self, context) -> None:
        self.context: FastLoopOperator = context


    def handle_input(self, bl_context, bl_event):
        handled = False
        if bl_event.type == btn('RIGHTMOUSE') and bl_event.value == 'RELEASE':
            self.context.cancelled = True
            self.context.pop_action()
            handled = True
        return handled
    

    def draw_ui(self, bl_context):

        if self.context.area_invoked != bl_context.area:
            return

        self.context.main_panel_hud.draw()

        if self.context.slider_widget is not None:
            self.context.slider_widget.draw()
