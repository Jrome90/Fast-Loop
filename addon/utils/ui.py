from __future__ import annotations
from typing import Dict

from collections import namedtuple
import bpy
from bpy.types import Area, Region, RegionView3D
from mathutils import Color, Vector

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


def get_ordered_fl_keymap_actions():
        return  {"use_even": "Even", "flipped": "Flip", "mirrored": "Mirrored", 
        "perpendicular": "Perpendicular", "use_multi_loop_offset": "Multi Loop Offset",
        "loop_space_value": "Loop Spacing", "insert_verts": "Insert Verts", "insert_on_selected_edges": "Use Selected Edges", 
        "freeze_edge": "Freeze Edge", "use_snap_points": "Snap Points", 
        "lock_snap_points": "Lock Snap Points",
        "increase_loop_count": "Increase Loop Count", 
        "decrease_loop_count": "Decrease Loop Count",
        "insert_midpoint": "Insert Loop At Midpoint"}

def append_modifier_keys(key_string, ctrl, shift, alt):
        if ctrl:
            key_string += "+Ctrl"
        if shift:
            key_string += "+Shift"
        if alt:
            key_string += "+Alt"
        return key_string

def get_ui_scale():
    return common.prefs().hud_scale

def get_slider_scale():
    return common.prefs().slider_scale

def get_slider_x():
    prefs = common.prefs()
    width = get_slider_width()
    x = prefs.slider_x

    if x == -1:
        x = (get_view3d_width() - width ) * 0.5
    return x

def get_slider_y():
    prefs = common.prefs()
    y = prefs.slider_y

    if y == -1:
        y = get_headers_height() + 20
    return y

def get_slider_position():
    return get_slider_x(), get_slider_y()

def get_slider_width():
    return common.prefs().slider_width

def set_slider_width(value):
    common.prefs().slider_width = value

def get_dpi():
    return bpy.context.preferences.system.dpi

def get_view3d_width():
    return bpy.context.area.width            

def get_view3d_height():
    return bpy.context.area.height 

ScreenData = namedtuple("ScreenData", "region win_size rv3d is_perspective")
def get_screen_data_for_3d_view(context, mvals_win):

    area = get_active_area(mvals_win, context)
    if area is None:
        return None, None, None, None
    region = get_region_from_area(mvals_win, area)
    if region is None:
        return None, None, None, None
    win_size = Vector((region.width, region.height))
    rv3d = get_3d_region(area)
    is_perspective = rv3d.is_perspective
    return ScreenData(region, win_size, rv3d, is_perspective)


def get_active_area(mouse_co, context)-> None | Area:
    x, y = mouse_co
    for area in context.screen.areas:
        if area.type != 'VIEW_3D':
            continue
        
        if (x >= area.x and
                    y >= area.y and
                    x < area.width + area.x and
                    y < area.height + area.y):
            return area
    else:
        return None


def get_region_from_area(mouse_coords_win, area: Area):
    if area is None:
        return None 
    x, y = mouse_coords_win
    for region in area.regions:
        if region.type != 'WINDOW':
            continue
        
        if (x >= area.x and
                    y >= region.y and
                    x < region.width + region.x and
                    y < region.height + region.y):
            return region
    else:
        return None

def get_3d_region(area)-> None | RegionView3D:
    if area is None:
        return None 

    for space in area.spaces:
        if space.type == 'VIEW_3D':
            return space.region_3d
    else:
        return None

def inside_view_3d(mouse_co)-> bool:
    headers_height = get_headers_height()
    height = get_view3d_height()
    width = get_view3d_width()
    area_x = bpy.context.area.x
    area_y = bpy.context.area.y

    return (mouse_co[0] < (area_x + width) and mouse_co[1] < (height + area_y - headers_height))


def get_toolbar_width()-> float:
    for region in bpy.context.area.regions:
        if region.type == "TOOLS":
            return region.width         
    return 0

def inside_toolbar(mouse_co)-> bool:
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

def get_headers_height_a(area:Area):
    if area is None:
        return 0.0
    
    total_height = 0.0
    for region in area.regions:
        if region.type in {"TOOL_HEADER"}: 
            total_height += region.height if region.alignment in {'TOP'} else 0
        
        if region.type in {"HEADER"}: 
            total_height += region.height if region.alignment in {'TOP'} else 0
            
    return total_height               

def get_npanel_width():
    for region in bpy.context.area.regions:
        if region.type == "UI":
            return region.width            
    return 0

def get_npanel_width_a(area: Area):
    if area is None:
        return 0

    for region in area.regions:
        if region.type == "UI":
            return region.width  
    return 0

def get_npanel_height():
    for region in bpy.context.area.regions:
        if region.type == "UI":
            return region.height          
    return 0

def inside_npanel(mouse_coords_win, area):
    if area is None:
        return False
     
    v3d_width = area.width

    npanel_width = get_npanel_width_a(area)

    region: Region = get_region_from_area(mouse_coords_win, area)
    if region is None:
        return False
    
    mouse_x = mouse_coords_win[0] - region.x

    if mouse_x >= (v3d_width - npanel_width):
        return True

def inside_navigation_gizmo(mouse_co, mouse_coords_win, area: Area):
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

    npanel_width = get_npanel_width_a(area)
    
    if area is None:
        return
    
    region: Region = get_region_from_area(mouse_coords_win, area)
    if region is None:
        return False

    region_x_max =  region.width - (npanel_width)

    x = region_x_max - (axis_gizmo_size_px + axis_gizmo_offset_px)

    headers_height = get_headers_height_a(area)
    region_y_max =  region.height - headers_height
    y =  region_y_max - (axis_gizmo_size_px + axis_gizmo_offset_px)

    mouse_x = mouse_coords_win[0] - region.x
    mouse_y = mouse_coords_win[1] - region.y

    if (mouse_x - x)**2 + (mouse_y - y)**2 < ((axis_gizmo_size_px)**2):

        return True
    return False



# def get_align_text_angle_3d(p1: Vector, p2: Vector):
#     """ returns the angle in radians to rotate text so that
#         the text is aligned with the line defined by p1 and p2 in 3d space.
#     """
#     context = bpy.context
#     p1_2d = location_3d_to_region_2d(context.region, context.space_data.region_3d, p1)
#     p2_2d = location_3d_to_region_2d(context.region, context.space_data.region_3d, p2)

#     dir_vec = (p1_2d - p2_2d).normalized()
#     x_axis = Vector((1, 0))
#     y_axis = Vector((0, 1))

#     a: Vector = x_axis
#     b: Vector = dir_vec

#     rot_mat = Matrix([(a.x * b.x + a.y * b.y, b.x * a.y - a.x * b.y),
#                       (a.x * b.y - b.x * a.y, a.x * b.x + a.y*b.y)]
#         )
    
#     v = rot_mat @ a

#     return -x_axis.angle_signed(v)


def get_units_to_display(disable: bool):
    units_to_display = get_units_from_bl_settings().keys()
    unit_system = bpy.context.scene.unit_settings.system
    if disable:
        units_to_disable = set(units_to_display)
        if unit_system == "METRIC":
            all_possible_units = {"kilometers", "meters", "centimeters", "millimeters", "micrometers"}
            units_to_disable = all_possible_units.difference(units_to_disable)

        elif unit_system == "IMPERIAL":
            all_possible_units = {"miles", "feet", "inches", "thou"}
            units_to_disable = all_possible_units.difference(units_to_disable)

        for unit in units_to_disable:
            setattr(common.prefs(), unit, False)

    return units_to_display

def get_units_from_bl_settings() -> Dict[str, str]:
    # metric_units = {"kilometers": "km", "meters": "m", "centimeters": "cm", "millimeters": "mm", "micrometers": "µm"}

    units = {}
    unit_system = bpy.context.scene.unit_settings.system
    len_unit = bpy.context.scene.unit_settings.length_unit
    if unit_system == "METRIC":
        if bpy.context.scene.unit_settings.length_unit == "KILOMETERS":
            units = {"kilometers": "km", "meters": "m", "centimeters": "cm", "millimeters": "mm", "micrometers": "µm"}
        elif len_unit == "METERS":
            units = {"meters": "m", "centimeters": "cm", "millimeters": "mm", "micrometers": "µm"}
        elif len_unit == "CENTIMETERS":
            units = {"centimeters": "cm", "millimeters": "mm", "micrometers": "µm"}
        elif len_unit == "MILLIMETERS":
            units = {"millimeters": "mm", "micrometers": "µm"}
        elif len_unit == "MICROMETERS":
            units = {"micrometers": "µm"}

    elif unit_system == "IMPERIAL":
        if len_unit == "MILES":
            units = {"miles": "mi", "feet": "'", "inches": "\"", "thou": "thou"}
        elif len_unit == "FEET":
            units = {"feet": "'", "inches": "\"", "thou": "thou"}
        elif len_unit == "INCHES":
            units = {"inches": "\"", "thou": "thou"}
        elif len_unit == "THOU":
            units = {"thou": "thou"}

    return units

def get_units_from_prefs():
    units = []
    units_lookup = get_units_from_bl_settings()
    for attr, unit in units_lookup.items():
        value = getattr(common.prefs(), attr, None)
        if value is not None:
            if value:
                units.append(unit)
    return units


from decimal import ROUND_05UP, ROUND_CEILING, Decimal, getcontext, ROUND_FLOOR, ROUND_HALF_UP
def format_distance2(value, updating=False, places=6, override_settings=False):
    value_str = ""

    value = Decimal(value).quantize(Decimal(10)**-places)
    
    unit_conversion_lookup = {}
    units = []
    values = []
    rounding_policy = []
    
    if bpy.context.scene.unit_settings.system == "METRIC":
        # if bpy.context.scene.unit_settings.use_separate:
        unit_conversion_lookup = {"km": 0.001, "m": 1, "cm": 100, "mm": 1000, "µm": 1000000} 
        if bpy.context.scene.unit_settings.length_unit == "METERS":
            units = get_units_from_prefs() if not override_settings else ["m", "cm", "mm", "µm"]
            values = [0] * len(units)
            rounding_policy = [ROUND_FLOOR]*3
            rounding_policy.append(ROUND_HALF_UP)

        elif bpy.context.scene.unit_settings.length_unit == "CENTIMETERS":
            units =  get_units_from_prefs() if not override_settings else ["cm", "mm", "µm"]
            values = [0,0,0]
            rounding_policy = [ROUND_FLOOR]*2
            rounding_policy.append(ROUND_HALF_UP)

        elif bpy.context.scene.unit_settings.length_unit == "MILLIMETERS":
            units =  get_units_from_prefs() if not override_settings else ["mm", "µm"]
            values = [0,0]
            rounding_policy = [ROUND_FLOOR, ROUND_HALF_UP]

        elif bpy.context.scene.unit_settings.length_unit == "MICROMETERS":
            units =  get_units_from_prefs() if not override_settings else ["µm"]
            values = [0]
            rounding_policy = [ROUND_HALF_UP]

        elif bpy.context.scene.unit_settings.length_unit == "KILOMETERS":
            units =  get_units_from_prefs() if not override_settings else ["km", "m", "cm", "mm", "µm"]
            values = [0] * len(units)
            rounding_policy = [ROUND_FLOOR]*4
            rounding_policy.append(ROUND_HALF_UP)

    elif bpy.context.scene.unit_settings.system == "IMPERIAL":
        unit_conversion_lookup = {"mi": 0.000621371,"'": 3.2808399, "\"": 39.3700787, "thou": 39370.0787401}
        if bpy.context.scene.unit_settings.length_unit == "MILES":
            units =  get_units_from_prefs() if not override_settings else ["mi","'","\"", "thou"]
            values =  [0]* len(units)
            rounding_policy = [ROUND_FLOOR]*3
            rounding_policy.append(ROUND_HALF_UP)

        elif bpy.context.scene.unit_settings.length_unit == "FEET":
            units =  get_units_from_prefs() if not override_settings else ["'","\"", "thou"]
            values =  [0]* len(units)
            rounding_policy = [ROUND_FLOOR]*2
            rounding_policy.append(ROUND_HALF_UP)
        elif bpy.context.scene.unit_settings.length_unit == "INCHES":
            units =  get_units_from_prefs() if not override_settings else ["\"", "thou"]
            values =  [0] * len(units)
            rounding_policy = [ROUND_FLOOR, ROUND_HALF_UP]

        elif bpy.context.scene.unit_settings.length_unit == "THOU":
            units = ["thou"]
            values = [0]
            rounding_policy = []
            rounding_policy.append(ROUND_HALF_UP)

    for i, unit in enumerate(units):
        if value < 0.0:
            break

        scale = Decimal(unit_conversion_lookup[unit])
        value *= scale
        val = 0.0
        if i != len(units) - 1:
            val = value.to_integral_value(rounding=rounding_policy[i])
        else:
            if value > 1.0:
                val = value.quantize(Decimal('1.00'), rounding=ROUND_HALF_UP)
            else:
                val = value.quantize(Decimal('1.000'), rounding=ROUND_HALF_UP)

            # Strip trailing zeros
            val = val.to_integral() if val == val.to_integral() else val.normalize()

        values[i] = val
        value -= val
        value /= scale

    for val, unit in zip(values, units):
        if not updating and (val == 0):
            continue
        
        pre_space = " " if unit == "thou" else ""
        value_str += str(val) + pre_space + unit + " "    

    return value_str

# -------------------------------------------------------------
# Format a number to the right unit
#
# -------------------------------------------------------------
def format_distance(fmt, units, value, factor=1):
    s_code = "\u00b2"  # Superscript two
    hide_units = False 

    value *= bpy.context.scene.unit_settings.scale_length
    # ------------------------
    # Units automatic
    # ------------------------
    if units == "1":
        # Units
        if bpy.context.scene.unit_settings.system == "IMPERIAL":
            feet = value * (3.2808399 ** factor)
            if round(feet, 2) >= 1.0:
                if hide_units is False:
                    fmt += " ft"
                if factor == 2:
                    fmt += s_code
                tx_dist = fmt % feet
            else:
                inches = value * (39.3700787 ** factor)
                if hide_units is False:
                    fmt += " in"
                if factor == 2:
                    fmt += s_code
                tx_dist = fmt % inches
        elif bpy.context.scene.unit_settings.system == "METRIC":
            if round(value, 2) >= 1.0:
                if hide_units is False:
                    fmt += " m"
                if factor == 2:
                    fmt += s_code
                tx_dist = fmt % value
            else:
                if round(value, 2) >= 0.01:
                    if hide_units is False:
                        fmt += " cm"
                    if factor == 2:
                        fmt += s_code
                    d_cm = value * (100 ** factor)
                    tx_dist = fmt % d_cm
                else:
                    if hide_units is False:
                        fmt += " mm"
                    if factor == 2:
                        fmt += s_code
                    d_mm = value * (1000 ** factor)
                    tx_dist = fmt % d_mm
        else:
            tx_dist = fmt % value
    # ------------------------
    # Units meters
    # ------------------------
    elif units == "2":
        if hide_units is False:
            fmt += " m"
        if factor == 2:
            fmt += s_code
        tx_dist = fmt % value
    # ------------------------
    # Units centimeters
    # ------------------------
    elif units == "3":
        if hide_units is False:
            fmt += " cm"
        if factor == 2:
            fmt += s_code
        d_cm = value * (100 ** factor)
        tx_dist = fmt % d_cm
    # ------------------------
    # Units millimeters
    # ------------------------
    elif units == "4":
        if hide_units is False:
            fmt += " mm"
        if factor == 2:
            fmt += s_code
        d_mm = value * (1000 ** factor)
        tx_dist = fmt % d_mm
    # ------------------------
    # Units feet
    # ------------------------
    elif units == "5":
        if hide_units is False:
            fmt += " ft"
        if factor == 2:
            fmt += s_code
        feet = value * (3.2808399 ** factor)
        tx_dist = fmt % feet
    # ------------------------
    # Units inches
    # ------------------------
    elif units == "6":
        if hide_units is False:
            fmt += " in"
        if factor == 2:
            fmt += s_code
        inches = value * (39.3700787 ** factor)
        tx_dist = fmt % inches
    # ------------------------
    # Default
    # ------------------------
    else:
        tx_dist = fmt % value

    return tx_dist


def get_bl_active_object_color() -> Color:
    return (*bpy.context.preferences.themes.items()[0][1].view_3d.object_active, 1.0)