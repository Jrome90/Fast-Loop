from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fast_loop import FastLoopOperator

import bpy

from ..edge_slide import EdgeSlideOperator
from ...ops.fast_loop_actions import BaseAction
from ..fast_loop_helpers import (set_mode, Mode)

from .import insert_single_loop
from .import insert_multi_loop

class EdgeSlideAction(BaseAction):
    Mode = Mode.EDGE_SLIDE

    def __init__(self, context, invoked_by_spacebar) -> None:
        self.context: FastLoopOperator = context
        self._invoked_by_spacebar = invoked_by_spacebar
    
    def enter(self):
        set_mode(self.Mode)
        if self.context.use_snap_points:
            self.context.snap_context.disable_increment_mode()
        EdgeSlideOperator.register_listener(self, self.edge_slide_finished)
        bpy.ops.fl.edge_slide('INVOKE_DEFAULT', restricted=not self._invoked_by_spacebar, invoked_by_fla=True)
    
    def exit(self):
        if self.context.use_snap_points:
            self.context.snap_context.enable_increment_mode()
        EdgeSlideOperator.unregister_listener(self)

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

    def edge_slide_finished(self, message=None, data=None):
        if message is not None and message == "switch_modes":
            event = data
            num_lookup = {'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5, 'SIX': 6, 'SEVEN': 7, 'EIGHT': 8, 'NINE': 9}
            n = num_lookup[event.type]
            if n == 1:
                self.context.pop_action()
                self.context.switch_action(insert_single_loop.InsertSingleLoopAction(self.context))
            else:
                self.context.pop_action()
                self.context.switch_action(insert_multi_loop.InsertMultiLoopAction(self.context))
            self.context.segments = n
        else:
            self.context.pop_action()
