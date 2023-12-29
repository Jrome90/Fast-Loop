
from ..fast_loop_algorithms import ComputeEdgePostitonsSingleAlgorithm
from ..fast_loop_helpers import Mode

from .import insert_multi_loop
from ..actions.insert_loop_base import InsertAction


class InsertSingleLoopAction(InsertAction):
    Mode = Mode.SINGLE

    def __init__(self, context) -> None:
        context.segments = 1
        context.edge_pos_algorithm = ComputeEdgePostitonsSingleAlgorithm()
        super().__init__(context)

    def enter(self):
        self.context.main_panel_hud.set_child_visibility_by_name("Single", True)
        self.context.main_panel_hud.set_title_bar_text("Single")
        self.context.main_panel_hud.layout_widgets()
        super().enter()

    def exit(self):
        self.context.main_panel_hud.set_child_visibility_by_name("Single", False)
        super().exit()

    def handle_input(self, bl_context, bl_event):
        handled = False

        num_lookup = {'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5, 'SIX': 6, 'SEVEN': 7, 'EIGHT': 8, 'NINE': 9,
        'NUMPAD_1': 1, 'NUMPAD_2': 2, 'NUMPAD_3': 3, 'NUMPAD_4': 4, 'NUMPAD_5': 5, 'NUMPAD_6': 6, 'NUMPAD_7': 7, 'NUMPAD_8': 8, 'NUMPAD_9': 9}
        n = num_lookup.get(bl_event.type, None)
        if n is not None and n != 1:
            self.context.segments = n
            self.context.switch_action(insert_multi_loop.InsertMultiLoopAction(self.context))

            handled = True

        if not handled:
            handled = super().handle_input(bl_context, bl_event)
                
        return handled
    

    def handle_modal_event(self, bl_context, modal_event, bl_event):
        handled = False
        
        if modal_event == "Increase Loop Count":
            self.update()
            self.context.switch_action(insert_multi_loop.InsertMultiLoopAction(self.context))
            handled = True

        if not handled:
            handled = super().handle_modal_event(bl_context, modal_event, bl_event)
        
        return handled
        
