import bpy
from bpy.types import Region
from .. import utils
from .. keymaps.modal_keymapping import (ModalOperatorKeymapCache as km_cache, 
                                        ModalKeymap, save_keymap)

class FastLoopRunner(bpy.types.Operator):
    bl_idname = "exe.fast_loop"
    bl_label = "Execute the fast loop operator"
    bl_options = {'INTERNAL'}

    @property
    def is_running(self):
        return utils.ops.fl_props().is_running

    @is_running.setter
    def is_running(self, value):
        utils.ops.set_fl_prop('is_running', value)

    @property
    def prompted(self):
        return utils.ops.fl_props().prompted

    # @prompted.setter
    # def prompted(self, value):
    #     utils.ops.set_fl_prop('prompted', value)

    
    @classmethod
    def poll( cls , context ) :
        return not utils.ops.fl_props().is_running

    def modal(self, context, event):
        if context.mode != 'EDIT_MESH' or (not \
        any(tool_name in {'fl.fast_loop_tool'} \
            for tool_name in [tool.idname for tool in context.workspace.tools])):
            return self.cancel(context)
        
        if not self.is_running: #and self.prompted:
            self.is_running = True
            bpy.ops.fl.fast_loop('INVOKE_DEFAULT', invoked_by_tool=True)
        return {'PASS_THROUGH'}


    def invoke(self, context, event):
        if self.is_running:
            return {'CANCELLED'}
        else:
            context.window_manager.modal_handler_add(self)
            # if not self.prompted:
                # bpy.ops.ui.alt_nav_detected('INVOKE_DEFAULT')
        return{'RUNNING_MODAL'}


    def cancel(self, context):
        self.is_running = False
        return {'CANCELLED'}


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
        window_manager = context.window_manager
        window_manager.Loop_Cut_Slots.reset_active(context)


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
        context.area.tag_redraw()
        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'TIMER', 'LEFT_CTRL', 'LEFT_ALT', 'LEFT_SHIFT', 'RIGHT_ALT', 'RIGHT_CTRL', 'RIGHT_SHIFT'}:
            return {'RUNNING_MODAL'}

        if not wm.keymap_strings.awaiting_input:
            keymap: ModalKeymap = km_cache.get_keymap(self.operator)
            key = event.type
            if keymap.update_mapping(self.active_keymap, key, 'PRESS', ctrl=event.ctrl, shift=event.shift, alt=event.alt):
                key_with_mods = self.append_modifier_keys(key, event.ctrl, event.shift, event.alt)
                setattr(wm.keymap_strings, self.active_keymap, key_with_mods)
            else:
                setattr(wm.keymap_strings, self.active_keymap, self.previous_shortcut)
            return {'FINISHED'}
    
        return {'RUNNING_MODAL'}
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
    bl_idname = "ui.save_keymap_operator"
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


class UI_OT_distance_display_settings_operator(bpy.types.Operator):
    bl_idname = "ui.distance_display_settings_operator"
    bl_label = "Display Units"

    def execute(self, context):
        prefs = utils.common.prefs()
        message = f"{prefs.meters} {prefs.centimeters} {prefs.millimeters} {prefs.micrometers}"
        self.report({'INFO'}, message)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=450)

    
    def draw(self, context):
        layout = self.layout
        row = layout.row()

        prefs = utils.common.prefs()
        units_to_display = utils.ui.get_units_to_display(True)
        for unit in units_to_display:
            row.prop(prefs, unit, toggle=True)



class UI_OT_AltNavDetected_operator(bpy.types.Operator):
    bl_idname = 'ui.alt_nav_detected'
    bl_label = 'Alt navigation was detected'
    bl_options = {'REGISTER','INTERNAL'}

    bl_description = ""

    uses_alt_nav: bpy.props.BoolProperty(name= "Enable Alt Navigation settings", default=False)

    @property
    def prompted(self):
        return utils.ops.fl_props().prompted

    @prompted.setter
    def prompted(self, value):
        utils.ops.set_fl_prop('prompted', value)

    def execute(self, context):
        self.prompted = True
        return {'FINISHED'}
    

    def invoke(self, context, event):
        # if not self.uses_alt_nav:
        window_manager = context.window_manager
        mouse_coords_win = (event.mouse_x, event.mouse_y)
        area_3d = utils.ui.get_active_area(mouse_coords_win, context)
        region: Region = utils.ui.get_region_from_area(mouse_coords_win, area_3d)
        center_x = int(area_3d.x + (region.width/2)) 
        center_y = int(area_3d.y + (region.height/2))

        context.window.cursor_warp(center_x, center_y)
        result = window_manager.invoke_props_dialog(self)
        context.window.cursor_warp(*mouse_coords_win)

        return result
    
    
    def draw(self, context):
        layout = self.layout
        row = layout.row()

