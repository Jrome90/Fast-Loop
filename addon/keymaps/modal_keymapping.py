import os
from .. import utils


class ModalKeymap():
    _keymap = {}
    _action_to_keymap = {}
    _events = set()
    def __init__(self, keymap):
        self._keymap = {v: k for k, v in keymap.items()}
        #self._action_to_keymap = {k: v for k, v in keymap.items()}
        self._actions = {action for action in keymap.keys()}


    def update_mapping(self, action, event_type, event_value, ctrl=False, shift=False, alt=False):
        #keymap_string = keymap_to_string(event_type, event_value, ctrl, shift, alt)
        keymap_item = (event_type, 'PRESS', ctrl, shift, alt)

        if action in self._keymap.values():
            if keymap_item in self._keymap:
                if action != self._keymap[keymap_item]:
                    return False
            else:
                self.remove_mapping(action)
                self._keymap[keymap_item] = action      
            return True 


    def remove_mapping(self, event):
        for keymap, keymap_value in self._keymap.items():
            if event == keymap_value:
                del self._keymap[keymap]
                break

    def get_all_mappings(self):
        return self._keymap.items()

    def get_action_from_mapping(self, mapping):
        return self._keymap.get(mapping)
    
    def get_mapping_from_action(self, action):
        action_to_keymap = {v: k for k, v in self._keymap.items()}
        return action_to_keymap[action]

    def get_valid_keymap_actions(self):
        return self._actions


class ModalOperatorKeymapCache():
    keymaps = {}

    @classmethod
    def get_keymap(cls, operator_id) -> ModalKeymap:
        if operator_id in cls.keymaps:
            return cls.keymaps[operator_id]
        else:
            keymap = load_keymap(operator_id)
            cls.keymaps[operator_id] = ModalKeymap(keymap)
            return  cls.keymaps[operator_id]

    @classmethod
    def get_all_keymaps(cls):
        return cls.keymaps.items()
     

# from dataclasses import dataclass
# from typing import *
# @dataclass(eq=True, unsafe_hash=True)      
# class ModalKeymapItem():
#     event_type: str
#     event_value: str
#     ctrl: bool
#     shift: bool
#     alt: bool

#     def __init__(self, event_type, event_value, ctrl=False, shift=False, alt=False):
#         self.event_type = event_type
#         self.event_value= event_value
#         self.ctrl = ctrl
#         self.shift = shift
#         self.alt = alt



# def keymap_to_string(event_type, event_value, ctrl, shift, alt):
#     return f"{event_type}_{event_value}_{str(ctrl)}_{str(shift)}_{str(alt)}"


def load_keymap(operator_id):
    def repair_data(data):
        return {k: tuple(v) for k, v in data.items()}
   
    directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.dirname(directory)
    file_path = os.path.join(parent_directory, "HotkeyPrefs.JSON")

    deserializer = utils.serialization.JSONDeserializer(file_path)
    data = repair_data(deserializer.deserialize()[operator_id])
    return data
    

def save_keymap(operator_id, modal_keymap: ModalKeymap=None):
    directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.dirname(directory)
    file_path = os.path.join(parent_directory, "HotkeyPrefs.JSON")
   
    data = None
    if modal_keymap is not None:
        keymap_data = {v: k for k, v in modal_keymap.get_all_mappings()}
        data = {operator_id:
            keymap_data
        }
    else:
        data = {operator_id : 
            {"even": ('e', 'PRESS', False, False, False),
            "flip": ('f', 'PRESS', False, False, False),
            "midpoint": ('c', 'PRESS', False, False, False), 
            "mirrored": ('m', 'PRESS', False, False, False),
            "perpendicular": ('/', 'PRESS', False, False, False),
            "select_new_loops": ('h', 'PRESS', False, False, False),
            "multi_loop_offset": ('o', 'PRESS', False, False, False),
            "scale": ('w', 'PRESS', False, False, False),
            "snap_points": ('s', 'PRESS', False, False, False),
            "lock_snap_points": ('x', 'PRESS', False, False, False),
            "freeze_edge": (',', 'PRESS', False, False, False)
            }
        }

    utils.serialization.JSONSerializer(file_path).serialize(data)

    print(f" Saved modal keymap preferences to: {file_path}")