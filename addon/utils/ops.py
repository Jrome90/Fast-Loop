from collections import namedtuple
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
        bpy.context.window.cursor_warp(int(x), int(y))

def get_m_button_map(button):
    select_mouse_val = bpy.context.window_manager.keyconfigs.user.keymaps['3D View'].keymap_items['view3d.select'].type #bpy.context.window_manager.keyconfigs.active.preferences.select_mouse
    if button == 'LEFTMOUSE':
        return 'LEFTMOUSE' if select_mouse_val == "LEFTMOUSE" else 'RIGHTMOUSE'

    if button == 'RIGHTMOUSE':
        return 'RIGHTMOUSE' if select_mouse_val == "LEFTMOUSE" else 'LEFTMOUSE'

KeyMapItem = namedtuple("KeyMapItem", "type value ctrl alt shift")
def get_undo_keymapping():
    item = bpy.context.window_manager.keyconfigs.user.keymaps['Screen'].keymap_items['ed.undo']
    return KeyMapItem(item.type, item.value, item.ctrl, item.alt, item.shift)


def match_event_to_keymap(event, key_map_item):
    return (event.type, event.value, event.ctrl, event.alt, event.shift) == key_map_item


#bpy.context.window_manager.keyconfigs.active.keymaps['Screen'].keymap_items['ed.undo']

def fl_props():
    context = bpy.context
    if hasattr(context.window_manager, "fl_props"):
        return context.window_manager.fl_props
    return None

def set_fl_prop(property, value)-> bool:
    context = bpy.context
    if hasattr(context.window_manager, "fl_props"):
        if hasattr(context.window_manager.fl_props, property):
            setattr(context.window_manager.fl_props, property, value)
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


def ls_options():
    context = bpy.context
    if hasattr(context.window_manager, "ls_options"):
        return context.window_manager.ls_options
    return None


def set_ls_option(option, value)-> bool:
    context = bpy.context
    if hasattr(context.window_manager, "ls_options"):
        if hasattr(context.window_manager.ls_options, option):
            setattr(context.window_manager.ls_options, option, value)
            return True
    return False


# def generate_status_layout(shortcuts, layout):

#     for shortcut in shortcuts:

#         row = layout.row()
#         row.alignment = 'LEFT'
        
#         icons_box = row.column()
#         icons_box.alignment = 'LEFT'
#         icons_box.scale_x = 1
#         row.separator(factor=0.1)
#         text_box = row.column()
#         text_box.alignment = 'LEFT'
#         text_box.scale_x = 1

#         ui.add_shortcut_info(shortcut, text_box, icons_box)
    
#     return layout


# from .. keymaps.modal_keymapping import ModalKeymap
# def generate_status_layout_text_only(keymap: ModalKeymap , layout, extra_mapppings=None):
#     def add_keymap_label(action, key):
#         row = layout.row()
#         row.alignment = 'LEFT'
#         text_box = row.column()
#         text_box.alignment = 'LEFT'
#         text_box.scale_x = 1
#         text_box.label(text=f"{action} ({key})")

#     if extra_mapppings is not None:
#         for action, mapping in extra_mapppings.items():
#             add_keymap_label(action, mapping)

#     for action, action_name in utils.ui.get_ordered_fl_keymap_actions().items():
#         mapping = keymap.get_mapping_from_action(action)
#         key = mapping[0].upper()
#         action = action.replace("_", " ").capitalize()
#         add_keymap_label(action_name, key)
    
#     return layout

def get_context_overrides(*objects, area=None):

    def get_base_context(area):
        window = bpy.context.window_manager.windows[0]
        screen_area = None
        area_region = None
        area_space = None
        if area is None:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    screen_area = area
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            area_region = region
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            area_space = space
        else:
            if area.type == 'VIEW_3D':
                screen_area = area
                for region in area.regions:
                    if region.type == 'WINDOW':
                        area_region = region
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        area_space = space
                

        return {'window': window, 'screen': window.screen, 'area' : screen_area, 'region': area_region, 'space': area_space}

    context = get_base_context(area)
    context['object'] = objects[0]
    context['active_object'] = objects[0]
    context['selected_objects'] = objects
    context['selected_editable_objects'] = objects
    return context
