from typing import *
from . modal_keymapping import ModalKeymap

class Event_Handler():
    def __init__(self, keymap):
        self._modal_keymap: ModalKeymap = keymap

    def handle_event(self, event):
        key = event.unicode if event.unicode else event.type
        keymapping = (key, event.value, \
        event.ctrl, event.shift, event.alt)
        return self._modal_keymap.get_action_from_mapping(keymapping)
