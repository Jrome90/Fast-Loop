from . import insert_loop_base
from .import insert_single_loop, scale_loops
from ..fast_loop_algorithms import ComputeEdgePostitonsMultiAlgorithm
from ..fast_loop_helpers import Mode


class InsertMultiLoopAction(insert_loop_base.InsertAction):
    Mode = Mode.MULTI_LOOP

    def __init__(self, context) -> None:
        if context.segments == 1:
            context.segments = 2
        context.edge_pos_algorithm = ComputeEdgePostitonsMultiAlgorithm()
        super().__init__(context)

    
    def enter(self):
        self.context.main_panel_hud.set_child_visibility_by_name("Multi", True)
        self.context.main_panel_hud.set_title_bar_text(f"Multi [{self.context.segments}]")

        self.context.main_panel_hud.layout_widgets()
        super().enter()

    def exit(self):
        self.context.main_panel_hud.set_child_visibility_by_name("Multi", False)
        super().exit()
    

    def handle_input(self, bl_context, bl_event):
        handled = False
        num_lookup = {'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5, 'SIX': 6, 'SEVEN': 7, 'EIGHT': 8, 'NINE': 9,
        'NUMPAD_1': 1, 'NUMPAD_2': 2, 'NUMPAD_3': 3, 'NUMPAD_4': 4, 'NUMPAD_5': 5, 'NUMPAD_6': 6, 'NUMPAD_7': 7, 'NUMPAD_8': 8, 'NUMPAD_9': 9}
        n = num_lookup.get(bl_event.type, None)
        if n == 1:
            self.context.switch_action(insert_single_loop.InsertSingleLoopAction(self.context))
            handled = True

        elif n is not None:
            self.context.segments = n
            self.context.main_panel_hud.set_title_bar_text(f"Multi [{self.context.segments}]")
            handled = True

        if not handled:
            handled = super().handle_input(bl_context, bl_event)

        return handled


    def handle_modal_event(self, bl_context, modal_event, bl_event):
        handled = False
        
        if modal_event == "Decrease Loop Count":
            self.context.segments -= 1
            if self.context.segments == 1:
                self.update()
                self.context.switch_action(insert_single_loop.InsertSingleLoopAction(self.context))
            else:
                self.context.main_panel_hud.set_title_bar_text(f"Multi [{self.context.segments}]")
                self.context.scale = self.CalculateDefaultScaleValue()

            handled = True

        elif modal_event == "Increase Loop Count":
            self.update()
            self.context.segments += 1
            self.context.main_panel_hud.set_title_bar_text(f"Multi [{self.context.segments}]")
            self.context.scale = self.CalculateDefaultScaleValue()
            handled = True

        elif modal_event == "Loop Spacing":
            self.context.push_action(scale_loops.ScaleLoopsAction(self.context, bl_event))
            handled = True
        
        elif modal_event in {"Multi Loop Offset"}:
            self.context.use_multi_loop_offset = not self.context.use_multi_loop_offset
            handled = True
                    
        if not handled:
            handled = super().handle_modal_event(bl_context, modal_event, bl_event)
        
        return handled
    
    def CalculateDefaultScaleValue(self) -> float:
        return 1 - (2/(self.context.segments + 1))