import bpy

from .. import utils
from .. keymaps.modal_keymapping import (ModalOperatorKeymapCache as km_cache, 
                                        ModalKeymap, save_keymap)

class UI_OT_override_reset(bpy.types.Operator):
    bl_idname = 'ui.overrride_reset'
    bl_label = 'Override Reset'
    bl_options = {'REGISTER','INTERNAL'}

    bl_description = "Reset the current slot"

    def execute(self, context):
        self.reset(context)
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)

    def reset(self, context):
        scene = context.scene
        slots = scene.Loop_Cut_Slots.loop_cut_slots
        index = scene.Loop_Cut_Lookup_Index
        slot = slots[index]
        for i, loop_cut in enumerate(slot.loop_cut_slot.values()):
            if loop_cut.get_method() == 'PERCENT':
                percent = ((1.0 + i) / ( (len(slot.loop_cut_slot.values())) + 1.0))
                loop_cut.percent = percent * 100
            else:
                loop_cut.distance = 0.0


class UI_OT_reset_operator(bpy.types.Operator):
    bl_idname = 'ui.reset_operator'
    bl_label = 'Reset Operator'
    bl_options = {'REGISTER','INTERNAL'}

    bl_description = "If you get an error and now the Fast loop operators wont work, Run this to reset the state"

    def execute(self, context):
        self.reset(context)
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)

    def reset(self, context):
        utils.ops.fl_props().is_running = False



class UI_OT_keymap_input_operator(bpy.types.Operator):
    bl_idname = 'ui.keymap_input_operator'
    bl_label = ''
    bl_options = {'REGISTER','INTERNAL'}

    bl_description = "Click to change keymap"

    active_keymap: bpy.props.StringProperty(
        name="Active Keymap",
        description="Keymap that is being changed"
    )

    previous_shortcut: bpy.props.StringProperty(
        name="Previous shortcut",
        description="Store the keybaord shortcut before being remapped"
    )

    operator: bpy.props.StringProperty(
        name="Active Operator Keymap",
        description="Active Operator Keymap is for"
    )

    def invoke(self, context, event):
        wm = context.window_manager
        self.previous_shortcut = getattr(wm.keymap_strings, self.active_keymap)
        
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        wm = context.window_manager
        setattr(wm.keymap_strings, self.active_keymap, "Press any key")
        context.area.tag_redraw()
        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'TIMER', 'LEFT_CTRL', 'LEFT_ALT', 'LEFT_SHIFT', 'RIGHT_ALT', 'RIGHT_CTRL', 'RIGHT_SHIFT'}:
            return {'RUNNING_MODAL'}
       
        keymap: ModalKeymap = km_cache.get_keymap(self.operator)
        key = event.unicode if event.unicode else event.type
        if keymap.update_mapping(self.active_keymap, key, 'PRESS', ctrl=event.ctrl, shift=event.shift, alt=event.alt):
            key_with_mods = self.append_modifier_keys(key, event.ctrl, event.shift, event.alt)
            setattr(wm.keymap_strings, self.active_keymap, key_with_mods)
        else:
            setattr(wm.keymap_strings, self.active_keymap, self.previous_shortcut)
        return {'FINISHED'}
    
    @staticmethod
    def append_modifier_keys(key_string, ctrl, shift, alt):
        if ctrl:
            key_string += "+Ctrl"
        if shift:
            key_string += "+Shift"
        if alt:
            key_string += "+Alt"
        return key_string

class UI_OT_save_keymap_operator(bpy.types.Operator):
    bl_idname = 'ui.save_keymap_operator'
    bl_label = 'Save Keymap Operator'
    bl_options = {'REGISTER','INTERNAL'}

    bl_description = "Save modal keymap preferences"

    def execute(self, context):
        self.save()
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)

    def save(self):
        found = False
        for operator_id, keymap in km_cache.get_all_keymaps():
            save_keymap(operator_id, keymap)
            found = True

        if not found:
            save_keymap("FL_OT_fast_loop")