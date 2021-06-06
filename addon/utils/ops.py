import bpy

from . import common
from . import ui

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


def get_context_overrides(*objects):

    def get_base_context():
        window = bpy.context.window_manager.windows[0]
        area = None
        region = None
        space = None
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area = area
                for region in area.regions:
                    if region.type == 'WINDOW':
                        region = region
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space = space
                

        return {'window': window, 'screen': window.screen, 'area' : area, 'region': region, 'space': space}

    context = get_base_context()
    context['object'] = objects[0]
    context['active_object'] = objects[0]
    context['selected_objects'] = objects
    context['selected_editable_objects'] = objects
    return context