from typing import *
from . modal_keymapping import ModalKeymap

class Event_Handler():
    def __init__(self, keymap):
        self._modal_keymap: ModalKeymap = keymap
        self._numeric_input_enabled = False
        self._numeric_value = ""
        self._numeric_input_done_key = None
        self._callback = None
        self._consume_mouse_events = False

    def handle_event(self, event):
        if self._numeric_input_enabled:
            return self._handle_numeric_input(event)
                

        key = event.unicode if event.unicode else event.type
        keymapping = (key, event.value, event.ctrl, event.shift, event.alt)
        return self._modal_keymap.get_action_from_mapping(keymapping)

    def _handle_numeric_input(self, event):
        changed = False
        if str.isnumeric(event.ascii):
            self._numeric_value += event.ascii
            print(self._numeric_value)
            changed = True
        elif event.ascii == '.' and event.value == 'PRESS':
            if self._numeric_value.find('.') == -1:
                self._numeric_value += event.ascii
                changed = True
        elif event.type == 'BACK_SPACE' and event.value == 'PRESS':
            if len(self._numeric_value) >= 2:
                self._numeric_value = self._numeric_value[:-1]
                changed = True
            elif len(self._numeric_value) == 1:
                self._numeric_value = "0"
                changed = True

        else:
            key = event.unicode if event.unicode else event.type
            if key == self._numeric_input_done_key:
                keymapping = (key, event.value, event.ctrl, event.shift, event.alt)
                return self._modal_keymap.get_action_from_mapping(keymapping)
            elif key not in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'} or self._consume_mouse_events:
                return "numeric_input"
        
        if changed:
            self._callback(self._numeric_value)
            self._consume_mouse_events = True
            return "numeric_input"

        return None

    
    def numeric_input_begin(self, event, input_changed_callback):
        self._numeric_input_enabled = True
        self._numeric_input_done_key = event.unicode if event.unicode else event.type
        self._callback = input_changed_callback

    def numeric_input_end(self):
        self._numeric_input_enabled = False
        self._numeric_value = ""
        self._numeric_input_done_key = None
        self._consume_mouse_events = False
        self._callback = None
