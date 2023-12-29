from re import compile, finditer, IGNORECASE, Match
from dataclasses import dataclass
from typing import *

import bpy 

from . modal_keymapping import ModalKeymap
from .. utils.math import cm_to_meters, mm_to_meters, meters_to_cm, meters_to_mm


# SEMI_COLON ;.
# PERIOD ..
# COMMA ,.
# QUOTE “.
# ACCENT_GRAVE `.
# MINUS -.
# PLUS +.
# SLASH /.
# BACK_SLASH \.
# EQUAL =.
# LEFT_BRACKET [.
# RIGHT_BRACKET ].
# LEFT_ARROW Left Arrow – ←.
# DOWN_ARROW Down Arrow – ↓.
# RIGHT_ARROW Right Arrow – →.
# UP_ARROW Up Arrow – ↑.
# NUMPAD_2 Numpad 2 – Pad2.
# NUMPAD_4 Numpad 4 – Pad4.
# NUMPAD_6 Numpad 6 – Pad6.
# NUMPAD_8 Numpad 8 – Pad8.
# NUMPAD_1 Numpad 1 – Pad1.
# NUMPAD_3 Numpad 3 – Pad3.
# NUMPAD_5 Numpad 5 – Pad5.
# NUMPAD_7 Numpad 7 – Pad7.
# NUMPAD_9 Numpad 9 – Pad9.
# NUMPAD_PERIOD Numpad . – Pad..
# NUMPAD_SLASH Numpad / – Pad/.
# NUMPAD_ASTERIX Numpad * – Pad*.
# NUMPAD_0 Numpad 0 – Pad0.
# NUMPAD_MINUS Numpad - – Pad-.
# NUMPAD_ENTER Numpad Enter – PadEnter.
# NUMPAD_PLUS Numpad + – Pad+.

key_name_to_ascii = {"SEMI_COLON": ";", "PERIOD": ".", "COMMA": ",", "QUOTE": "\"", 
"ACCENT_GRAVE": "`", "MINUS": "-", "PLUS": "+", "SLASH": "/", "BACK_SLASH": "\\", "EQUAL": "=",
}

num_pad_to_value_str = {'NUMPAD_1': "1", 'NUMPAD_2': "2", 'NUMPAD_3': "3", 'NUMPAD_4': "4", 'NUMPAD_5': "5", 'NUMPAD_6': "6", 'NUMPAD_7': "7", 'NUMPAD_8': "8", 'NUMPAD_9': "9", 'NUMPAD_PERIOD': "."}

@dataclass
class NumericInputResults():
    input_string: str = None
    value: float = 0.0
    is_distance:bool  = True
    valid_input: bool = False


class Event_Handler():
    def __init__(self, keymap):
        self._modal_keymap: ModalKeymap = keymap
        self._numeric_input_enabled = False
        self._adv_numeric_input_enabled = False
        self._numeric_value = ""
        self._numeric_input_done_keys: Set = set()
        self._metric_pattern = None
        self._imperial_pattern = None
        self._percent_pattern = None
        self._callback = None
        self._consume_mouse_events = False

    def handle_event(self, event):
        if self._numeric_input_enabled:
            return self._handle_complex_numeric_input(event)
                
        key = event.type
        if event.type in key_name_to_ascii:
            key = key_name_to_ascii[event.type]

        keymapping = (key, event.value, event.ctrl, event.shift, event.alt)
        return self._modal_keymap.get_action_from_mapping(keymapping)

    def _handle_numeric_input(self, event):
        changed = False
        if str.isnumeric(event.ascii):
            self._numeric_value += event.ascii
            changed = True
        elif event.ascii == '.' and event.value == 'PRESS':
            if self._numeric_value.find('.') == -1:
                if len(self._numeric_value) == 0:
                    self._numeric_value += "0"
                    
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
            key = event.type
            if key in self._numeric_input_done_keys:
                keymapping = (key, event.value, event.ctrl, event.shift, event.alt)
                return self._modal_keymap.get_action_from_mapping(keymapping)
            elif key not in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'} or self._consume_mouse_events:
                return "numeric_input"
        
        if changed:
            self._callback(self._numeric_value)
            self._consume_mouse_events = True
            return "numeric_input"

        return None

    # Regex: (?P<val>[0-9,./]+)(?P<unit>mm|cm|m|)(?:'s|s)?\b
    def _handle_complex_numeric_input(self, event):
        changed = False
        unit_value_pairs = []
        valid_input = False
        # print(f"Event: type: {event.type} ascii: {event.ascii}")
        if str.isnumeric(event.ascii) or event.type in {'C', 'M', 'F', 'T', 'I', 'N', 'H', 'O', 'U', 'QUOTE','PERIOD', 'COMMA', 'SPACE', 'SLASH', 'P', 'NUMPAD_SLASH', 'NUMPAD_PERIOD'}:
        #or event.type in num_pad_to_value_str:

            # if event.type in num_pad_to_value_str:  
            #     self._numeric_value += num_pad_to_value_str[event.type]
            # else:
            self._numeric_value += event.ascii
            for pattern in [self._percent_pattern, self._imperial_pattern, self._metric_pattern]:
                unit_value_pairs, valid_input = self.parse_numeric_input_str(self._numeric_value, pattern)
                if valid_input:
                    changed = True
                    break
                
            else:
                changed = True

                if not valid_input:
                    unit, val = unit_value_pairs[0]
                    if val is not None and unit is None:
                        valid_input = True
                        default_unit = get_default_unitless_typing()
                        unit_value_pairs = [(default_unit, val)]

            
        elif event.type == 'BACK_SPACE' and event.value == 'PRESS':
            self._numeric_value = self._numeric_value[:-1]

            for pattern in [self._percent_pattern, self._imperial_pattern, self._metric_pattern]:
                unit_value_pairs, valid_input = self.parse_numeric_input_str(self._numeric_value, pattern)
                if valid_input:
                    changed = True
                    break
            else:
                changed = True

                if not valid_input:
                    unit, val = unit_value_pairs[0]
                    if val is not None and unit is None:
                        valid_input = True
                        default_unit = get_default_unitless_typing()
                        unit_value_pairs = [(default_unit, val)]

        else:

            key = event.type
            if key in self._numeric_input_done_keys:
                keymapping = (key, event.value, event.ctrl, event.shift, event.alt)
                return self._modal_keymap.get_action_from_mapping(keymapping)

            # elif key in {'E'}:
            #     return "numeric_input_pass_through"

            elif key not in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'ESC'} or self._consume_mouse_events:
                return "numeric_input"
        
        if changed:
            results = None
            if valid_input:
                value, is_distance = convert_unit_value_pairs(unit_value_pairs)
                results = NumericInputResults(self._numeric_value, value, is_distance, valid_input)
            else:
                results = NumericInputResults(self._numeric_value, None, True, valid_input)

            self._callback(results)
            self._consume_mouse_events = True
            return "numeric_input"
        
        # if event.type == "C":
        #     print("Passed through C :(")
        return None

    def parse_numeric_input_str(self, input_string, pattern):
        # print(input_string)
        unit_value_pairs = []
        valid_input = True
        matches = pattern.finditer(input_string)
        match: Match
        default_unit = None
        for match in matches:
            try:
                unit, val = match.group("unit", "val")
                # print(f"unit:{unit}, val:{val} pat: {pattern}" )
                if val is None or unit is None:
                    valid_input = False
                
                if val is not None and (unit is None or not unit) and pattern is self._percent_pattern:
                    valid_input = False

                # if not valid_input and default_unit is not None:
                #     unit = default_unit
                #     valid_input = True

                unit_value_pairs.append((unit, val))

            except IndexError:
                print("No Match")
          
        return unit_value_pairs, valid_input

    
    def numeric_input_begin(self, event, input_changed_callback):
        self._percent_pattern = compile(r"(?P<val>[0-9.,]+(?:(?: \d+)*[/0-9]+)?)(?P<unit>p)?", IGNORECASE)
        # (?P<val>[0-9,./]+)(?P<unit>mm|cm|m|)(?:'s|s)?\b
        # (?P<val>[0-9.,]+(?:(?:\d+)*[/0-9]+)?)(?P<unit>mm|cm|m|)(?:'s|s)?\b
        self._metric_pattern= compile(r"(?P<val>[0-9.,]+(?:(?: \d+)*[/0-9]+)?)(?P<unit>mm|cm|m)?", IGNORECASE)
        self._imperial_pattern =  compile(r"(?P<val>[0-9.,]+(?:(?: \d+)*[/0-9]+)?)(?P<unit>\'|\"|thou|ft|in)?", IGNORECASE)

        self._numeric_input_enabled = True
        self._numeric_input_done_keys.add(event.type)
        self._numeric_input_done_keys.add('ESC')
        self._numeric_input_done_keys.add('RET')
        self._callback = input_changed_callback

    def numeric_input_end(self):
        self._numeric_input_enabled = False
        self._numeric_value = ""
        self._numeric_input_done_keys.clear()
        self._consume_mouse_events = False
        self._callback = None


from fractions import Fraction
def convert_unit_value_pairs(unit_value_pairs) -> float:

    def value_str_to_float(value: str):
        whole = "0"
        fraction = value
        parts = value.split(" ", 1)

        if len(parts) == 2:
            whole = parts[0]
            fraction = parts[1]
        try:
            return float(int(whole) + Fraction(fraction))
        except ValueError:
            return float(int(whole))

    unit_settings = bpy.context.scene.unit_settings
    unit_system = unit_settings.system
    unit_scale = unit_settings.scale_length
    length_unit = unit_settings.length_unit

    length = 0.0
    unit: str
    value: str
    for unit, value in unit_value_pairs:
        value = value.replace(",", ".") # For Europe
        if unit.lower() == "m":
            length += value_str_to_float(value)
        elif unit.lower() == "cm":
            length += cm_to_meters(value_str_to_float(value))
        elif unit.lower() == "mm":
            length += mm_to_meters(value_str_to_float(value))
        elif unit.lower() == "p":
            return value_str_to_float(value), False
        elif unit.lower() == "ft":
            length += value_str_to_float(value) * 0.304800
        elif unit.lower() == "in":
            length += value_str_to_float(value) * 0.0254
        elif unit.lower() == "thou":
         length += value_str_to_float(value) * 0.0000254
    
    return length/unit_scale, True

from .. utils import common
def get_default_unitless_typing():
    prefs = common.prefs()

    #TODO: Based on blender unit system use metric or imperial
    unit_settings = bpy.context.scene.unit_settings
    unit_system = unit_settings.system

    default_unit_system_items = prefs.bl_rna.properties['metric_unit_default'].enum_items if unit_system in {"METRIC"} \
                                else prefs.bl_rna.properties['imperial_unit_default'].enum_items
    get = None
    if unit_system in {'METRIC'}:
        get = prefs.metric_unit_default
    else:
        get = prefs.imperial_unit_default

    return default_unit_system_items.get(get).description