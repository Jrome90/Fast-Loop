import bpy
from . import common
from .. import ui

def update_panel_category(self, context):
    category = self.panel_category
    region_type = 'UI' if category else 'HEADER'

    for cls in ui.classes:
        if hasattr(cls, 'bl_category'):
            cls.bl_category = category
            cls.bl_region_type = region_type

            bpy.utils.unregister_class(cls)
            bpy.utils.register_class(cls)


def description(*args):
    return '.\n'.join(args)


def header(*args):
    return ' | '.join(args)


def statistics(header, context):
    if bpy.app.version < (2, 90, 0):
        layout = header.layout
        layout.separator_spacer()

        text = context.scene.statistics(context.view_layer)
        layout.label(text=text, translate=False)

def add_shortcut_info(keymap, text_box, icons_box):
    m_buttons = ['MOUSE_LMB', 'MOUSE_RMB']

    for text, icons in keymap.items():
        text_box.label(text=text)
        icon_row = icons_box.row()
        icon_row.alignment = 'LEFT'
        
        for icon in icons:
            if icon in {'MOUSE_LMB', 'MOUSE_RMB'}:
                i = m_buttons.index(icon) 
                if common.prefs().use_rcs:
                    icon = m_buttons[i-1]

            icon_row.label(icon=icon)

        icon_row.scale_x = len(icons) * 0.15

# Return an ordered list of fast loop's actions needed for ordered UI
def get_ordered_fl_keymap_actions():
    return  ["even", "flip", "mirrored", "midpoint", "perpendicular",  "multi_loop_offset", "select_new_loops", "scale", "snap_points", "lock_snap_points", "freeze_edge", "increase_loop_count", "decrease_loop_count"]

def get_mouse_select_text():
    prefs = common.prefs()
    return "LMB" if not prefs.use_rcs else "RMB"

def get_mouse_other_button_text():
    prefs = common.prefs()
    return "RMB" if not prefs.use_rcs else "LMB"

def get_ui_scale():
    return bpy.context.preferences.system.ui_scale

def get_view3d_width():
    return bpy.context.area.width            

def get_view3d_height():
    return bpy.context.area.height            

def inside_view_3d(mouse_co):
    height = get_view3d_height()
    width = get_view3d_width()

    return (mouse_co[0] < width and mouse_co[1] < height)


def get_toolbar_width():
    for region in bpy.context.area.regions:
        if region.type == "TOOLS":
            return region.width         
    return 0

def inside_toolbar(mouse_co):
    return mouse_co[0] <= get_toolbar_width()

def get_header_height():
    for region in bpy.context.area.regions:
        if region.type in {"HEADER"}:
            return region.height

def get_headers_height():
    total_height = 0.0
    for region in bpy.context.area.regions:
        if region.type in {"HEADER", "TOOL_HEADER"}:
            total_height += region.height
    return total_height           

def get_npanel_width():
    for region in bpy.context.area.regions:
        if region.type == "UI":
            return region.width            
    return 0

def get_npanel_height():
    for region in bpy.context.area.regions:
        if region.type == "UI":
            return region.height          
    return 0

def inside_npanel(mouse_co):
    v3d_width = get_view3d_width()

    npanel_width = get_npanel_width()

    if mouse_co[0] >= (v3d_width - npanel_width):
        return True

def inside_navigation_gizmo(mouse_co):
    axis_gizmo_size_px = 80.0
    major, minor, _ = bpy.app.version
    if major >= 2 and minor >= 93:
        axis_gizmo_size_px = bpy.context.preferences.view.gizmo_size_navigate_v3d

    axis_gizmo_size_px /= 2.0
    axis_gizmo_offset_px = 10.0

    gizmo_size_px = 28.0
    gizmo_offset_px = 2.0

    #mini_axis_gizmo_size_px = bpy.context.preferences.view.mini_axis_size

    ui_scale = get_ui_scale()
    axis_gizmo_size_px *= ui_scale
    axis_gizmo_offset_px *= ui_scale

    npanel_width = get_npanel_width()
    area_width = get_view3d_width()

    region_x_max = area_width - (npanel_width)

    x = region_x_max - (axis_gizmo_size_px + axis_gizmo_offset_px)

    area_height = get_view3d_height()
    headers_height = get_headers_height()
    region_y_max = area_height - (headers_height)

    y =  region_y_max - (axis_gizmo_size_px + axis_gizmo_offset_px)

    mouse_x = mouse_co[0]
    mouse_y = mouse_co[1]
    if (mouse_x - x)**2 + (mouse_y - y)**2 < ((axis_gizmo_size_px)**2):

        return True
    return False
