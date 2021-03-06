import bpy

from . import common
from . import ui
from .. import utils

def cursor_warp(event: bpy.types.Event):
    '''
    Warp the cursor to keep it inside the active area.
    
    Args:
        event: Modal operator event.
    '''

    area = bpy.context.area
    prefs = bpy.context.preferences
    offset = prefs.view.ui_scale * 100

    left = area.x + offset
    right = area.x + area.width - offset
    x = event.mouse_x

    down = area.y + offset
    up = area.y + area.height - offset
    y = event.mouse_y

    if x < left:
        x = right + x - left
    elif x > right:
        x = left + x - right

    if y < down:
        y = up + y - down
    elif y > up:
        y = down + y - up

    if x != event.mouse_x or y != event.mouse_y:
        bpy.context.window.cursor_warp(x, y)

def get_m_button_map(button):
        prefs = common.prefs()
        if button == 'LEFTMOUSE':
            return 'LEFTMOUSE' if not prefs.use_rcs else 'RIGHTMOUSE'

        if button == 'RIGHTMOUSE':
            return 'RIGHTMOUSE' if not prefs.use_rcs else 'LEFTMOUSE'

def fl_props():
    context = bpy.context
    if hasattr(context.scene, "fl_props"):
        return context.scene.fl_props
    return None

def set_fl_prop(property, value)-> bool:
    context = bpy.context
    if hasattr(context.scene, "fl_props"):
        if hasattr(context.scene.fl_props, property):
            setattr(context.scene.fl_props, property, value)
            return True
    return False

def options():
    context = bpy.context
    if hasattr(context.scene, "fl_options"):
        return context.scene.fl_options
    return None

def set_option(option, value)-> bool:
    context = bpy.context
    if hasattr(context.scene, "fl_options"):
        if hasattr(context.scene.fl_options, option):
            setattr(context.scene.fl_options, option, value)
            return True
    return False


def generate_status_layout(shortcuts, layout):

    for shortcut in shortcuts:

        row = layout.row()
        row.alignment = 'LEFT'
        
        icons_box = row.column()
        icons_box.alignment = 'LEFT'
        icons_box.scale_x = 1
        row.separator(factor=0.1)
        text_box = row.column()
        text_box.alignment = 'LEFT'
        text_box.scale_x = 1

        ui.add_shortcut_info(shortcut, text_box, icons_box)
    
    return layout


from .. keymaps.modal_keymapping import ModalKeymap
def generate_status_layout_text_only(keymap: ModalKeymap , layout, extra_mapppings=None):
    def add_keymap_label(action, key):
        row = layout.row()
        row.alignment = 'LEFT'
        text_box = row.column()
        text_box.alignment = 'LEFT'
        text_box.scale_x = 1
        text_box.label(text=f"{action} ({key})")

    if extra_mapppings is not None:
        for action, mapping in extra_mapppings.items():
            add_keymap_label(action, mapping)

    for action in utils.ui.get_ordered_fl_keymap_actions():
        mapping = keymap.get_mapping_from_action(action)
        key = mapping[0].upper()
        action = action.replace("_", " ").capitalize()
        add_keymap_label(action, key)
    
    return layout

def get_context_overrides(*objects):

    def get_base_context():
        window = bpy.context.window_manager.windows[0]
        screen_area = None
        area_region = None
        area_space = None
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                screen_area = area
                for region in area.regions:
                    if region.type == 'WINDOW':
                        area_region = region
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        area_space = space
                

        return {'window': window, 'screen': window.screen, 'area' : screen_area, 'region': area_region, 'space': area_space}

    context = get_base_context()
    context['object'] = objects[0]
    context['active_object'] = objects[0]
    context['selected_objects'] = objects
    context['selected_editable_objects'] = objects
    return context