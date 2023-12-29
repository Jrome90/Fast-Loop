import os
from .. import utils
# To add a new modal keymap:
# 1) Add a default keymap to the dict named data in the Method save_keymap() below (modifier key order is: ctrl, shift, alt)
# 2) Add a new bpy.props.StringProperty to the ModalDisplay Class in addon.py
# 3) Add a new entry into the dict returned by get_ordered_fl_keymap_actions() 
#    where the key is a string with the value of the name of the bpy.props.StringProperty that was created in the  ModalDisplay Class

class ModalKeymap():
    _keymap = {}
    _action_to_keymap = {}
    _events = set()
    def __init__(self, keymap):
        self._keymap = {v: k for k, v in keymap.items()}
        self._actions = {action for action in keymap.keys()}


    def update_mapping(self, action, event_type, event_value, ctrl=False, shift=False, alt=False):
        keymap_item = (event_type, event_value, ctrl, shift, alt)
        action = utils.ui.get_ordered_fl_keymap_actions().get(action, None)
        if action is not None:
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
            {"Even": ('E', 'PRESS', False, False, False),
            "Flip": ('F', 'PRESS', False, False, False),
            # "Midpoint": ('C', 'PRESS', False, False, False), 
            "Mirrored": ('M', 'PRESS', False, False, False),
            "Perpendicular": ('/', 'PRESS', False, False, False),
            "Multi Loop Offset": ('O', 'PRESS', False, False, False),
            "Loop Spacing": ('W', 'PRESS', False, False, False),
            "Insert Verts": ('V', 'PRESS', False, False, False),
            "Use Selected Edges": ('A', 'PRESS', False, False, False),
            "Snap Points": ('S', 'PRESS', False, False, False),
            "Lock Snap Points": ('X', 'PRESS', False, False, False),
            "Freeze Edge": (',', 'PRESS', False, False, False),
            "Increase Loop Count": ('=', 'PRESS', False, False, False),
            "Decrease Loop Count": ('-', 'PRESS', False, False, False),
            "Insert Loop At Midpoint": ('RIGHTMOUSE', 'PRESS', False, True, False)
            }
        }

    utils.serialization.JSONSerializer(file_path).serialize(data)

    print(f" Saved modal keymap preferences to: {file_path}")

