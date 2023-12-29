from abc import ABCMeta
import blf

import gpu
from gpu import state
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from ... bl_ui_widgets import bl_ui_widget, bl_ui_drag_panel, bl_ui_button
from ...signalslot.signalslot import Signal
from .. import utils


def get_ls_prop():
    return utils.ops.ls_options()
    
def set_ls_prop(prop, value):
    return utils.ops.set_ls_option(prop, value)

def get_ls_prop_enum(prop):
    default =  get_ls_prop().bl_rna.properties[prop].default
    default_value = get_ls_prop().bl_rna.properties[prop].enum_items[default].value
    value = get_ls_prop().get(prop, default_value)
    return value


class BL_UI_SliderMulti(bl_ui_widget.BL_UI_Widget):
    
    def __init__(self, context, x, y, width, height, text_format=None):
        super().__init__(x, y, width, height)
        self._text_color     = (1.0, 1.0, 1.0, 1.0)
        self._thumb_color    = (0.5, 0.5, 0.7, 1.0)
        self._hover_color    = (0.5, 0.5, 0.8, 1.0)
        self._select_color   = (0.7, 0.7, 0.7, 1.0)
        self._bg_color       = (0.941, 0.823, 0.956, 0.6)
        self._min = 0
        self._max = 100
        self.x_screen = x
        self.y_screen = y
        self._text_size = 14
        self._thumb_display_text_size = 10

        self._decimals = 2
        self._show_min_max = True
        self._show_distances = True
        self._show_display_values = True

        self._text_format = text_format

        # States
        self._is_drag = False
        self._is_resizing = False
        self._is_moving = False
        self._mouse_in_resize_box = False

        # Checks to prevent undesired behavior.
        self._can_drag = False # Did the user click on a thumb?
        self._can_resize = False # Did the user click inside the resize box?
        #TODO: Implement the func to support this.
        # self._can_move = False # Did the user click inside the move box?
        self._is_static = False # Can a user move the thumbs at all?

        self._active_thumb_index = 0
        self._hover_thumb_index = None
        self.thumb_pos = [] # Relative to the slider position
        self.thumb_values = []
        self._active_thumb_position = 0
        self._slider_width = 1
        self._slider_height = 16
        self._thumb_offset_y = 5

        self._thumb_shader_batches = []
        self.thumb_display_values = []
        self.distance_values = []

        self.init(context)

        self.on_click = Signal(args=['context', 'value'])
        self.on_thumb_click = Signal(args=['context', 'index', 'value'])
        self.on_thumb_moved = Signal(args=['context', 'index', 'value'])

        utils.common.prefs().show_percentages_changed.connect(Slot(self.on_show_percentages))
        utils.common.prefs().show_slider_changed.connect(Slot(self.on_show_slider_changed))
        utils.common.prefs().slider_scale_changed.connect(Slot(self.on_slider_scale_changed))
        utils.common.prefs().slider_position_changed.connect(Slot(self.on_slider_position_changed))

    # @property
    # def width(self):
    #     return self.width

    @property
    def slider_x(self):
        return self.get_slider_x()
    
    @property
    def slider_y(self):
        return self.get_slider_y()

    @property
    def slider_width(self):
        return utils.ui.get_slider_width()
    
    @slider_width.setter
    def slider_width(self, value):
        return utils.ui.set_slider_width(value)
    
    @property
    def slider_height(self):
        return self.height * utils.ui.get_slider_scale()
    
    @property
    def thumb_width(self):
        return self._slider_width * utils.ui.get_slider_scale()
    
    @property
    def thumb_height(self):
        return self._slider_height * utils.ui.get_slider_scale()

    
    @property
    def text_color(self):
        return self._text_color

    @text_color.setter
    def text_color(self, value):
        self._text_color = value

    @property
    def text_size(self):
        return self._text_size

    @text_size.setter
    def text_size(self, value):
        self._text_size = value
    
    @property
    def color(self):
        return self._bg_color

    @color.setter
    def color(self, value):
        self._bg_color = value

    @property
    def thumb_color(self):
        return self._thumb_color

    @thumb_color.setter
    def thumb_color(self, value):
        self._thumb_color = value

    @property
    def hover_color(self):
        return self._hover_color

    @hover_color.setter
    def hover_color(self, value):
        self._hover_color = value

    @property
    def select_color(self):
        return self._select_color

    @select_color.setter
    def select_color(self, value):
        self._select_color = value

    @property
    def min(self):
        return self._min

    @min.setter
    def min(self, value):
        self._min = value

    @property
    def max(self):
        return self._max

    @max.setter
    def max(self, value):
        self._max = value

    @property
    def decimals(self):
        return self._decimals

    @decimals.setter
    def decimals(self, value):
        self._decimals = value

    @property
    def show_min_max(self):
        return self._show_min_max

    @show_min_max.setter
    def show_min_max(self, value):
        self._show_min_max = value
    
    # @property
    # def show_distances(self):
    #     return self._show_distances

    # @show_distances.setter
    # def show_distances(self, value):
    #     self._show_distances = value
    
    @property
    def show_display_values(self):
        return self._show_display_values

    @show_display_values.setter
    def show_display_values(self, value):
        self._show_display_values = value

    @property
    def thumb_count(self):
        return len(self.thumb_pos)

    @property
    def is_static(self):
        return self._is_static

    @is_static.setter
    def is_static(self, value):
        self._is_static = value

    def get_area_height(self):
        area = self._viewport_area
        return area.height
    
    def get_slider_x(self):
        prefs = utils.common.prefs()
        width = utils.ui.get_slider_width()
        x = prefs.slider_x

        if x == -1:
            x = (self._viewport_area.width - width ) * 0.5
        return x
    
    def get_slider_y(self):
        prefs = utils.common.prefs()
        y = prefs.slider_y

        if y == -1:
            y = utils.ui.get_headers_height_a(self._viewport_area) + 20
        return y

    def get_slider_position(self):
        return self.get_slider_x(), self.get_slider_y()
           
           
    def remove_all_thumbs(self):
        self.thumb_values.clear()
        self.thumb_pos.clear()
        self._thumb_shader_batches.clear()

    
    def _to_slider_space_x(self, x):
        return x - self.slider_x


    def _to_slider_space_y(self, y):
        area_height = self.get_area_height()
        return area_height - (y + self.slider_y)


    def _to_slider_space(self, x, y):
        return self._to_slider_space_x(x), self._to_slider_space_y(y)

       
    def _to_screen_space_x(self, x):
        return x + self.slider_x


    def _to_screen_space_y(self, y):
        area_height = self.get_area_height()
        return area_height - y


    def _to_screen_space(self, x, y):
        return self._to_screen_space_x(x), self._to_screen_space_y(y)


    def _value_to_pos(self, value):
        return self.slider_width * (value - self._min) / (self._max - self._min)


    def _pos_to_value(self, pos, round_to_half=False):
        def round_to_half_point(value):
            return round(value * 2) / 2.0
        val = self._min + round(((self._max - self._min) * pos / self.slider_width), self._decimals)
        # return round_to_half_point(val) if round_to_half else val
        return val


    def _set_thumb_pos(self, x, thumb_index, clamped=True, update_from_ui=False):
        def clamp_thumb_pos(thumb_pos, clamped_thumb_index):

            clamped_pos = utils.math.clamp(0, thumb_pos, self.slider_width)
            index = clamped_thumb_index
            if self.thumb_count > 1:
                max = self.thumb_pos[index + 1] if index != (self.thumb_count - 1) else (self.slider_width)
                min = self.thumb_pos[index - 1] if index != 0 else 0
                clamped_pos = utils.math.clamp(min, clamped_pos, max)

            return clamped_pos

        self.thumb_pos[thumb_index] = clamp_thumb_pos(x, thumb_index) if clamped else x
       
        self._active_thumb_position = self.thumb_pos[thumb_index]
        new_value = self._pos_to_value(self.thumb_pos[thumb_index], round_to_half=True) * 0.01
        self.thumb_values[thumb_index] = new_value
       
        self.update(self.slider_x, self.slider_y)

    
    def get_position(self):
        return self._active_thumb_position

    
    def set_slider_pos(self, values):
        self.remove_all_thumbs()
        if values:
            self.thumb_values = values
            self.thumb_pos = [self._value_to_pos(value) * 100 for value in values]
            
            self._active_thumb_index = utils.math.clamp(0, self._active_thumb_index, self.thumb_count - 1)
            self._active_thumb_position = self.thumb_pos[self._active_thumb_index]
        else:
            self.thumb_values.clear()
            self.thumb_pos.clear()

        self.update(self.slider_x, self.slider_y)

    
    def _update_slider_coords(self):
        if self.visible:
            self.set_slider_pos(self.thumb_values.copy())

    
    def set_active_thumb(self, index):
        self._active_thumb_index = index
    

    def set_display_values(self, values):
        self.thumb_display_values = values


    def set_distance_values(self, values):
        self.distance_values = values

    
    def is_thumb_under_mouse(self, x, y, thumb_index):
        
        scale = utils.ui.get_ui_scale()
        y_offset = self._thumb_offset_y * scale
        slider_y = (self.slider_height / 2.0 * scale) + y_offset
        thumb_pos = self.thumb_pos[thumb_index]
        if (
            (thumb_pos - self.thumb_width <= x <= 
            (thumb_pos + self.thumb_width)) and 
            (slider_y >= y >= slider_y - (self.thumb_height) - y_offset)
            ):
            return True
           
        return False


    def get_thumb_under_mouse(self, x, y) -> int:
        if self.is_static:
            return None

        for index in range(len(self.thumb_pos)):
            if self.is_thumb_under_mouse(x, y, index):
                return index
        return None

    def handle_event(self, event):
        x, y = self._to_slider_space(event.mouse_region_x, event.mouse_region_y)

        handled = False
        if event.type == 'LEFTMOUSE' and event.value == 'CLICK':
            handled = self.on_mouse_click(x, y)
        
        if event.type == 'LEFTMOUSE' and event.value == 'CLICK_DRAG':
            if self._can_drag:
                self._is_drag = True
                handled = True
            elif self._can_resize:
                self._is_resizing = True
                handled = True

        if not handled:
            handled = super().handle_event(event)
        
        return handled

    def on_mouse_click(self, x, y):
        if self.is_in_rect(x,y):
            thumb_index = self.get_thumb_under_mouse(x,y)
            if thumb_index is not None and not self._is_drag:
                self._is_drag = False
                self._active_thumb_index = thumb_index
                self.on_thumb_click.emit(context=self.context, index=thumb_index, value=self.thumb_values[thumb_index])
                return True
            else:
                self.on_click.emit(context=self.context, value=self._pos_to_value(x * 0.01))
                return True

    def mouse_down(self, x, y):
        x, y = self._to_slider_space(x, y)
        if self.is_in_rect(x,y):
            thumb_index = self.get_thumb_under_mouse(x,y)
            if thumb_index is not None and not self._is_drag:
                self._can_drag = True
                self._active_thumb_index = thumb_index

        elif self.is_in_resize_rect(x, y):
            self._can_resize = True

        return False # Always return false
    
    def mouse_move(self, x, y):

        s_x, s_y = self._to_slider_space(x, y)
        if not self._is_resizing:
            thumb_index = self.get_thumb_under_mouse(s_x, s_y)
            if thumb_index is not None:
                if not self._is_drag:
                    self._hover_thumb_index = thumb_index
                elif self._can_drag and self._is_drag:
                    self._set_thumb_pos(s_x, self._active_thumb_index)
                    self.on_thumb_moved.emit(context=self.context, index=self._active_thumb_index, value=self.thumb_values[:])                

            elif self._can_drag and self._is_drag:
                    self._set_thumb_pos(s_x, self._active_thumb_index)
                    self.on_thumb_moved.emit(context=self.context, index=self._active_thumb_index, value=self.thumb_values[:])
            elif self.is_in_resize_rect(s_x, s_y):
                self._mouse_in_resize_box = True

            else:
                self._hover_thumb_index = None
                self._mouse_in_resize_box = False

        elif self._is_resizing:
            self.slider_width = int(x - self.slider_x - 20)
            self._update_slider_coords()
           
    def mouse_up(self, x, y):
        self._can_drag = False
        self._can_resize = False
        self._is_drag = False
        self._is_resizing = False

    
    
    def is_in_rect(self, x, y):
        width = self.slider_width
        
        if (
            (0 <= x <= (width)) and 
            (self.slider_height >= y >= (0))
            ):
            return True
           
        return False
    
    def is_in_resize_rect(self, x, y):
        width = 5
        height = 5
        widget_x = self._to_slider_space_x(self.slider_x + self.slider_width + 20)
        
        widget_y = self.slider_height/2
        if (
            (widget_x - width <= x <= (widget_x + width)) and
            (widget_y + height >= y >= (widget_y - height))
            ):
            return True
           
        return False      


    def draw(self):
        scale = utils.ui.get_ui_scale()
        def draw_thumb_value(px_pos, value):
            blf.size(0, self._thumb_display_text_size*scale)
            sValue = sFormat.format(value)
            size = blf.dimensions(0, sValue)
            blf.position(0, px_pos + 1 - size[0] / 2.0, 
                            area_height - self.slider_y + self._thumb_offset_y, 0)
            
            r, g, b, a = self._text_color
            blf.color(0, r, g, b, a)
                
            blf.draw(0, sValue)

        if not self.visible:
            return

        area_height = self.get_area_height()

        self.shader.bind()
        
        # text_color = self._text_color
        
        # Draw Bar
        self.shader.uniform_float("color", self._bg_color)
        state.blend_set('ALPHA')
        self.batch_bg.draw(self.shader)

        # Draw Thumbs
        color = self._thumb_color
        for thumb_index, thumb_batch in enumerate(self._thumb_shader_batches):
            if self._hover_thumb_index is not None and thumb_index == self._hover_thumb_index:
                color = self._hover_color
            elif thumb_index == self._active_thumb_index:
                color = self._select_color
            
            else:
                color = self._thumb_color
                
            self.shader.uniform_float("color", color)
            thumb_batch.draw(self.shader)

        state.blend_set('NONE')      
        
        # Draw value text
        sFormat = None
        if self._text_format is None:
            sFormat = "{:0." + str(self._decimals) + "f}"
        else:
            sFormat = self._text_format
        
        if self.show_display_values and self.thumb_pos:
            if not self.thumb_display_values:
                value = self.thumb_values[self._active_thumb_index] * 100
                px_pos = self._to_screen_space_x(self.thumb_pos[self._active_thumb_index])
                draw_thumb_value(px_pos, value)
            else:
                for px_pos, value in zip(self.thumb_pos, self.thumb_display_values):
                    px_pos = self._to_screen_space_x(px_pos)
                    draw_thumb_value(px_pos, value)

        if self.distance_values and self.thumb_pos:
            self.draw_distance_values()

        # Draw min and max slider values
        # Min                      Max
        #  |---------V--------------|
        
        if self._show_min_max:
            r, g, b, a = self._text_color
            blf.color(0, r, g, b, a)

            sMin = sFormat.format(self._min)
            blf.size(0, self._text_size)

            size = blf.dimensions(0, sMin)
                        
            blf.position(0, self.slider_x - size[0] / 2.0, 
                            area_height - self.slider_height - self.slider_y, 0)
            blf.draw(0, sMin)

            sMax = sFormat.format(self._max)
            
            size = blf.dimensions(0, sMax)

            blf.position(0, self.slider_x + self.slider_width - size[0] / 2.0, 
                            area_height - self.slider_height - self.slider_y, 0)
            blf.draw(0, sMax)

        # Draw resize handle
        box_color = (1, 1, 1, 1.0)
        if self._mouse_in_resize_box:
            box_color = self._hover_color

        x = self.slider_x + self.slider_width + 20

        # Further offset the rezize handle to center it not just with the bar but the values at the bottom as well
        to_center_y = 1 * scale
        y = self._to_screen_space_y(self.slider_y + (self.slider_height/2) + to_center_y)
        center = (x, y)
        utils.draw_2d.draw_rectangle(size=3, color=box_color, center=center)

    
    def update_slider_bar_batch(self):
        scale = utils.ui.get_slider_scale()
        # batch for background
        pos_y = self._to_screen_space_y(self.slider_y) - (self.slider_height / 2.0)
        pos_x = self.slider_x

        indices = ((0, 1, 2), (0, 2, 3))

        # bottom left, top left, top right, bottom right
        width = self.slider_width
        half_height = 2 * scale
        vertices = (
                    (pos_x, pos_y - half_height), 
                    (pos_x, pos_y + half_height), 
                    (pos_x + width, pos_y + half_height),
                    (pos_x + width, pos_y - half_height) 
        )
        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.batch_bg = batch_for_shader(self.shader, 'TRIS', {"pos" : vertices}, indices=indices)


    def update_thumb_batches(self):
        # Slider triangles
        # 
        #        0
        #     1 /\ 2
        #      |  |
        #     3---- 4

        # batch for slider
        area_height = self.get_area_height()
        scale = utils.ui.get_slider_scale()
        h = self.thumb_height
        w = self.thumb_width
        y_offset = self._thumb_offset_y * scale
        pos_y = area_height - self.slider_y - (self.slider_height / 2.0) + (h / 2.0) + y_offset

        # indices = ((0, 1, 2)),# (1, 2, 3), (3, 2, 4)) # Triangle
        indices = ((0, 1, 2), (2, 1, 3)) # Rectangle
        

        for index, thumb_pos in enumerate(self.thumb_pos):
            pos_x = self._to_screen_space_x(thumb_pos)
            vertices = (
                        # Triangle
                        # (pos_x    , pos_y  - h + y_offset),
                        # (pos_x - w, pos_y - w + y_offset),
                        # (pos_x + w, pos_y - w + y_offset),
                        #-------------------------------
                        # (pos_x - w, pos_y - h),
                        # (pos_x + w, pos_y - h)
                        (pos_x - w, pos_y - w + y_offset),
                        (pos_x + w, pos_y - w + y_offset),
                        (pos_x - w, pos_y - h),
                        (pos_x + w, pos_y - h)
                    )
                        
            self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            shader_batch = batch_for_shader(self.shader, 'TRIS',  
                {"pos" : vertices}, indices=indices)
            if index <= len(self._thumb_shader_batches) - 1:
                self._thumb_shader_batches[index] = shader_batch
            else:
                self._thumb_shader_batches.insert(index, shader_batch)

    
    def update(self, x, y):
        if self.thumb_pos:
            self.update_thumb_batches()
        self.update_slider_bar_batch()

    #TODO: Make Decorators
    def draw_distance_values(self):
        scale = utils.ui.get_slider_scale()
        for i in range(len(self.distance_values)):
            start_pos_x = 0
            end_pos_x = 0
            x_spacing = 3
            screen_space = self._to_screen_space_x
            if i == 0:
                start_pos_x = self.slider_x
                end_pos_x = screen_space(self.thumb_pos[i] - x_spacing)
            elif i == len(self.distance_values) - 1:
                start_pos_x = screen_space(self.thumb_pos[-1] + x_spacing)
                end_pos_x = screen_space(self.slider_width)
            else:
                start_pos_x = screen_space(self.thumb_pos[i-1] + x_spacing)
                end_pos_x = screen_space(self.thumb_pos[i] - x_spacing)

            area_height = self.get_area_height()
            y_offset = (area_height - self.slider_y - self.slider_height*0.7) 

            #└──────┘

            unit_scale = bpy.context.scene.unit_settings.scale_length

            distance = self.distance_values[i] * unit_scale
            updating_values = True if (i == self._active_thumb_index or i == self._active_thumb_index + 1) and self._is_drag else False
            distance_text = utils.ui.format_distance2(distance, updating=updating_values)
            text_pos = (start_pos_x+end_pos_x)*0.5
            utils.draw_2d.draw_text_on_screen(distance_text, (text_pos, y_offset), 10, text_dim=(None, 9.0),h_alignment={'CENTER'}, v_alignment={'TOP'})

            start_pos_a = Vector((start_pos_x, y_offset))
            end_pos_a = Vector((start_pos_x, y_offset - 5))

            start_pos_b = Vector((end_pos_x, y_offset - 5))
            end_pos_b = Vector((end_pos_x, y_offset))

            utils.draw_2d.draw_line_strip((start_pos_a, end_pos_a, start_pos_b, end_pos_b), line_width=1*scale)
    
    def on_show_slider_changed(self):
        self.visible = utils.common.prefs().show_bar
    
    def on_show_percentages(self):
        self.show_display_values = utils.common.prefs().show_percents

    def on_slider_scale_changed(self, **kwargs):
        self._update_slider_coords()

    
    def on_slider_position_changed(self, **kwargs):
        self._update_slider_coords()


# The code below is hacky and is not suitable for general use.
import blf
import bpy
import gpu

from gpu_extras.batch import batch_for_shader

from ...signalslot.signalslot import Slot

from ... bl_ui_widgets.bl_ui_widget import BL_UI_Widget
from ... bl_ui_widgets.bl_ui_label import BL_UI_Label


def get_fl_options():
    return utils.ops.options()
    
def set_fl_options(option, value):
    return utils.ops.set_option(option, value)

def toggle_panel_locked():
    utils.common.set_addon_preference("panel_locked", not utils.common.prefs().panel_locked)

def toggle_panel_minimized():
     utils.common.set_addon_preference("panel_minimized", not utils.common.prefs().panel_minimized)

class TextLabel(BL_UI_Label):
    def __init__(self, x, y, width, height, scale, context, text, can_scale=False):
        self._font_id = 2
        self._can_scale = can_scale

        self._x_offset = 0.0
        self._y_offset = 0.0

        super().__init__(x, y, width, height)

        if text is not None:
            self._text = text

        self.init(context)

        self._text_size = int(11)

    
    @property
    def x_offset(self):
        return self._x_offset
    
    @x_offset.setter
    def x_offset(self, value):
        self._x_offset = value

    
    @property
    def y_offset(self):
        return self._y_offset
    
    y_offset.setter
    def y_offset(self, value):
        self._y_offset = value

    @property
    def scale(self):
        return utils.ui.get_ui_scale()

    @property
    def size(self):
        return blf.dimensions(self._font_id, self._text)

    def init(self, context):
        super().init(context)

    # def handle_event(self, event):
    #     pass

    def update(self, x, y):
        self.x_screen = x + self.x 
        self.y_screen = y + self.y

        self.draw()

    
    def draw(self):
        if not self.visible:
            return

        scale = self.scale
            
        area_height = self.get_area_height()

        blf.size(self._font_id, self._text_size * scale)
        size = blf.dimensions(self._font_id, self._text)
    
        #textpos_y = area_height - (self.y_screen - self.height) #+ self._y_offset
        textpos_y = area_height - (self.y_screen - self.height * self.scale)
        blf.position(self._font_id, self.x_screen + self._x_offset, textpos_y, 0)

        r, g, b, a = self._text_color

        blf.color(self._font_id, r, g, b, a)
            
        blf.draw(self._font_id, self._text)


#TODO Don't hardcode the x offsets
class TextLabelComposition(BL_UI_Widget, metaclass=ABCMeta):
    def __init__(self, context, x, y, width, height, name):
        _, height = blf.dimensions(1, name)
        
        super().__init__(x, y, width, height)

    @property
    def scale(self):
        return utils.ui.get_ui_scale()

    def update(self, x, y):
      pass


    def draw(self):
      pass
        


class TextLabelProperty(TextLabelComposition):
    def __init__(self, x, y, width, height, scale , context, name, initial_val, set_text_func=None, hotkey_hint=None, show_hotkeys=False, use_ui_scale=False):
        
        super().__init__(context, x, y, width, height, name)
        self.hotkey_hint = hotkey_hint
        self.show_hotkeys = show_hotkeys
        if set_text_func is not None:
            self._set_text_func = set_text_func
        else:
            if type(initial_val) is float:
                self._set_text_func = lambda new_val: f"{100*new_val:.3g} %"
            elif type(initial_val) is bool:
                self._set_text_func = lambda new_val: "On" if new_val else "Off"
            else:
                self._set_text_func = lambda new_val: f"{new_val}"

        self._name: TextLabel = self.set_name(context, name)
        self._value: TextLabel = self.set_value(context, initial_val)
        self._hotkey: TextLabel = self.set_hotkey(context, hotkey_hint)

        super().init(context)

    @property
    def name_label(self):
        return self._name
    
    name_label.setter
    def name_label(self, value):
        self._name._text = value
    
    @property
    def format_function(self):
        return self._name
    
    format_function.setter
    def format_function(self, function):
        self._set_text_func = function
    # @property
    # def value_label(self):
    #     return self._name
    
    # value_label.setter
    # def value_label(self, value):
    #     self._value._text = value

    def set_name(self, context, name):
        name_lbl = TextLabel(self.x, 0, 20, 10, 1, context, f"{name}:")
        name_lbl.text_color = (1.0, 1.0, 1.0, 0.5)
        name_lbl._font_id = 1
        return name_lbl
    
    def set_value(self, context, value):
        x_offset = 150
        value_lbl = TextLabel(self.x, 0, 20, 10, 1, context, self._set_text_func(value))

        if value is True:
            value_lbl.text_color = (0.0, 1.0, 0.0, 0.5)
        elif value is False:
            value_lbl.text_color = (1.0, 0.0, 0.0, 0.5)
        else:
            value_lbl.text_color = (1.0, 1.0, 1.0, 0.5)

        value_lbl._font_id = 1
        return value_lbl

    
    def set_hotkey(self, context, hotkey_hint):
        x_offset = 210
        if hotkey_hint is not None:
            hotkey = TextLabel(self.x, 0, 20, 10, 1, context, hotkey_hint)
            hotkey.text_color = (1.0, 1.0, 1.0, 0.5)
            hotkey._font_id = 1
            return hotkey

        return hotkey_hint
    
    def update(self, x, y):
        self._value.x_offset = 150 * self.scale #self._name.size[0] * self.scale
        self._name.update(x, y)
        self._value.update(x, y)
        if self._hotkey is not None:
            self._hotkey.x_offset =  210 * self.scale#self._value.x_offset + self._value.size[0] * self.scale
            self._hotkey.update(x, y)


    def draw(self):
        self._value.x_offset = 150 * self.scale#max(150, (self._name.size[0] * self.scale)) #(self._name.size[0] * self.scale)
        self._name.draw()
        self._value.draw()
        if self._hotkey is not None and self.show_hotkeys:
            self._hotkey.x_offset = 210* self.scale #self._value.x_offset + self._value.size[0] * self.scale
            self._hotkey.draw()

    
    def update_widget(self, text):
        if text is True:
             self._value.text_color = (0.0, 1.0, 0.0, 0.5)
        elif text is False:
             self._value.text_color = (1.0, 0.0, 0.0, 0.5)
        else:
             self._value.text_color = (1.0, 1.0, 1.0, 0.5)

        self._value.text = self._set_text_func(text)


class TextLabelHotkey(TextLabelComposition):
    def __init__(self, x, y, width, height, scale , context, name, hotkey_hint,  use_ui_scale=False):
        
        super().__init__(context, x, y, width, height, name)
        self.hotkey_hint = hotkey_hint

        self._name: TextLabel = self.set_name(context, name)
        self._hotkey: TextLabel = self.set_hotkey(context, hotkey_hint)

        super().init(context)

    def set_name(self, context, name):
        name_lbl = TextLabel(self.x, 0, 20, 10, 1, context, f"{name}:")
        name_lbl.text_color = (1.0, 1.0, 1.0, 0.5)
        name_lbl._font_id = 1
        return name_lbl
    
    def set_hotkey(self, context, hotkey_hint):
        x_offset = 210
        if hotkey_hint is not None:
            hotkey = TextLabel(self.x, 0, 20, 10, 1, context, hotkey_hint)
            hotkey.text_color = (1.0, 1.0, 1.0, 0.5)
            hotkey._font_id = 1
            return hotkey

        return hotkey_hint

    
    def update(self, x, y):
        self._hotkey.x_offset = 210* self.scale
        self._name.update(x, y)
        self._hotkey.update(x, y)


    def draw(self):
        self._hotkey.x_offset = 210* self.scale
        self._name.draw()
        self._hotkey.draw()
    
    
class VLayoutPanel(BL_UI_Widget):
    def __init__(self, context, width, height, position, scale, title_text=None):
        x, y = position
        self.x_screen = x
        self.y_screen = y
        self._vertical_spacing = int(10)
        self.widgets = {}

       
        self._inherit_parent_size = True

        super().__init__(x, y, width, height)
        super().init(context)
        
        self.layout_widgets()

        utils.common.prefs().on_hud_scale_changed.connect(Slot(self.on_hud_scale_changed))


    @property
    def scale(self):
        return utils.ui.get_ui_scale()

    @property
    def vertical_spacing(self):
        return self._vertical_spacing * self.scale

    @property
    def visible(self):
        return self._is_visible

    @visible.setter
    def visible(self, value):
        self._is_visible = value

        for widget in self.widgets.values():
            widget.visible = value

    @property
    def inherit_parent_size(self):
        return self._inherit_parent_size

    @inherit_parent_size.setter
    def inherit_parent_size(self, value):
        self._inherit_parent_size = value

    def on_hud_scale_changed(self):
        pass


    def add_child_widget(self, att_name, obj):
        #assert for instance type text
        name_found, obj_found = self.check_if_registered(att_name, obj)
        assert (not name_found and not obj_found), \
            "Failed to Add widget as a child. Name Exists: {0} Object Exists: {1}".format(name_found, obj_found)

        self.widgets[att_name] = obj

    def check_if_registered(self, att_name, obj):
        name_found = False
        obj_found = False
        for key, val in self.widgets.items():
            if key == att_name:
                name_found =True
            if val is obj:
                obj_found = True
            if name_found or obj_found:
                break

        return name_found, obj_found


    def layout_widgets(self):
        next_y = 0
        for text_obj in self.widgets.values():
            text_obj.update(self.x_screen, self.y_screen + next_y)
            if text_obj.visible:
                v_spacing = self.vertical_spacing
                next_y +=  v_spacing + text_obj.height * self.scale
        self.height = next_y

    def child_widget_focused(self, x, y):
        for widget in self.widgets.values():
            if widget.is_in_rect(x, y):
                return True
        return False
    

    def update(self, x, y):
        super().update(x, y)
        self.layout_widgets()


    def draw(self):
        if not self.visible:
            return

        super().draw()
        for text_obj in self.widgets.values():
             text_obj.draw()
        

    #TODO: Dont just update TextLabelProperty objects that are children but any child widget 
    def update_widget(self, name, new_value):
        obj = self.widgets.get(name, None)
        if obj is not None:
            if isinstance(obj, TextLabelProperty):
                if name == 'scale':
                    pass
                obj.update_widget(new_value)
            else:
                obj.text = f"{name}: {new_value}"


class VLayoutDragPanel(bl_ui_drag_panel.BL_UI_Drag_Panel):
    def __init__(self, context, width, height, position, scale, title_text=None):
        x, y = position
        super().__init__(x, y, width, height)
        self._skip_prop_update = False

        self.x_screen = x
        self.y_screen = y
        self._vertical_spacing = int(10)
        self.widgets = {}

        self._ignore_child_widget_focus = False

        self._image = None
        self._image_size = (24, 24)
        self._image_position = (0, 0)
        self._texture = None
        self._title_bar = None

        super().init(context)

        
        if title_text is not None:
            self.add_title(context, title_text)

        utils.common.prefs().on_hud_scale_changed.connect(Slot(self.on_hud_scale_changed))
        utils.common.prefs().on_display_panel_pos_changed.connect(Slot(self.on_panel_pos_changed))

    
    @property
    def title_bar(self):
        return self._title_bar

    @title_bar.setter
    def title_bar(self, value):
        self._title_bar = value
    
    @property
    def scale(self):
        return utils.ui.get_ui_scale()

    @property
    def vertical_spacing(self):
        return self._vertical_spacing * self.scale

    @property
    def visible(self):
        return self._is_visible

    @visible.setter
    def visible(self, value):
        self._is_visible = value

        for widget in self.widgets.values():
            widget.visible = value

    @property
    def ignore_child_widget_focus(self):
        return self._ignore_child_widget_focus

    @ignore_child_widget_focus.setter
    def ignore_child_widget_focus(self, value):
        self._ignore_child_widget_focus = value


    def on_hud_scale_changed(self):
        self.update(self.x, self.y)


    def on_panel_pos_changed(self):
        if not self.is_drag:
            self.update(utils.common.prefs().operator_panel_x, utils.common.prefs().operator_panel_y)


    def add_title(self, context, title_text=None):
        y_offset = 0 #-40
        self.title_bar: bl_ui_widget = Title_Bar(context, self, self.x_screen , self.y_screen, self.width + 8 * self.scale, 24, title_text)
        self.title_bar._bg_color = (1.,1.,1., 0.05)


    def add_child_widget(self, att_name, obj: BL_UI_Widget):
        name_found, obj_found = self.check_if_registered(att_name, obj)
        assert (not name_found and not obj_found), \
            "Failed to Add widget as a child. Name Exists: {0} Object Exists: {1}".format(name_found, obj_found)

        self.widgets[att_name] = obj

        if obj.inherit_parent_size:
            obj.width = self.width
            obj.height = self.height

    def check_if_registered(self, att_name, obj):
        name_found = False
        obj_found = False
        for key, val in self.widgets.items():
            if key == att_name:
                name_found =True
            if val is obj:
                obj_found = True
            if name_found or obj_found:
                break

        return name_found, obj_found

    # def load_image_as_texture(self, image_file_path):
    #     try:
    #         self._image = bpy.data.images.load(image_file_path, check_existing=True)
    #         self._image.alpha_mode = 'STRAIGHT' 
    #         self._texture = gpu.texture.from_image(self._image)
    #     except:
    #         pass

    
    def update(self, x, y):

        super().update(x, y)
        if self.is_drag:
            utils.common.set_addon_preference("operator_panel_x", self.x_screen)
            utils.common.set_addon_preference("operator_panel_y", self.y_screen)


        if self.title_bar is not None:
            y_offset = (-self.title_bar.height -10 ) * self.scale 
            self.title_bar.update(self.x_screen, self.y_screen + y_offset)     
            self.title_bar.y_offset = y_offset

        self.layout_widgets()


    def handle_event(self, event):
        x = event.mouse_region_x
        y = event.mouse_region_y

        handled = False

        if(event.type == 'LEFTMOUSE'):
            if(event.value == 'PRESS'):
                self._mouse_down = True
                self.mouse_down(x, y)
            else:
                self._mouse_down = False
                self.mouse_up(x, y)
                
        
        elif(event.type == 'MOUSEMOVE'):
            self.mouse_move(x, y)

            inrect = self.is_in_rect(x, y)

            # we enter the rect
            if not self._inrect and inrect:
                self._inrect = True
                self.mouse_enter(event, x, y)

            # we are leaving the rect
            elif self._inrect and not inrect:
                self._inrect = False
                self.mouse_exit(event, x, y)

        if not handled:
            if self.title_bar is not None:
                handled = self.title_bar.handle_event(event)

        return handled
       

    def layout_widgets(self):
        next_y = 0
        for text_obj in self.widgets.values():
            text_obj.update(self.x_screen, self.y_screen + next_y)
            if text_obj.visible:
                next_y += self.vertical_spacing + text_obj.height
        self.height = next_y


    def child_widget_focused(self, x, y):
        for widget in self.widgets.values():
            if widget.is_in_rect(x, y):
                return True
        return False

    def can_move(self, x, y):
        if self.title_bar is not None and not utils.common.prefs().panel_locked:
           return self.title_bar.is_in_rect(x, y)


    def mouse_move(self, x, y):
        super().mouse_move(x, y)

        if self.can_move(x, y):
            bpy.context.window.cursor_set("SCROLL_XY")
        else:
            bpy.context.window.cursor_set("DEFAULT")


    def mouse_down(self, x, y):
        if not self.visible:
         return False

        if self.child_widget_focused(x, y) and not self.ignore_child_widget_focus:
            return False
        
        if self.can_move(x, y):
            height = self.get_area_height()
            self.is_drag = True
            self.drag_offset_x = x - self.x_screen
            self.drag_offset_y = y - (height - self.y_screen)
            return True

        return False
    

    def draw(self):
        if not self.visible:
            return

        super().draw()
        for text_obj in self.widgets.values():
             text_obj.draw()


        if self.title_bar is not None:
            self.title_bar.draw()

    #TODO: Dont just update TextLabelProperty objects that are children but any child widget 
    def update_widget(self, name, new_value):

        obj = self.widgets.get(name, None)
        if obj is not None:
            if isinstance(obj, TextLabelProperty):
                obj.update_widget(new_value)
            else:
                obj.text = f"{name}: {new_value}"
    

    def set_child_visibility_by_name(self, child_name, visible):
        try:
            child_widget = self.widgets[child_name]
            child_widget.visible = visible
        except Exception: 
            raise
    
    def get_child_visibility_by_name(self, child_name):
        try:
            child_widget = self.widgets[child_name]
            return child_widget.visible
        except Exception: 
            raise
    
    def set_title_bar_text(self, text):
        self.title_bar.title_text = text

        
# Helpers
def make_property_label(self, context, name, attribute, hotkey=None, format_text_func=None):
    return TextLabelProperty(0, 0, 50, 16, 1, context, name,
    getattr(self, attribute), set_text_func=format_text_func,
    hotkey_hint=hotkey, show_hotkeys=True, use_ui_scale=True)

def make_hotkey_label(self, context, name, hotkey):
    return TextLabelHotkey(0, 0, 50, 16, 1, context, name, hotkey)


# This button class has an active state. Good for booleans, not regular buttons.
class Button(bl_ui_button.BL_UI_Button):

    def __init__(self, context, x, y, width, height):
        super().__init__(x, y, width, height)
        self._active = False
        self._image = None
        self._shader = None
        self._batch = None
        self._texcoords = ((0, 1), (0, 0), (1, 0), (1, 1))
        self.init(context)

        self.set_mouse_enter(self.on_mouse_hover)
        self.set_mouse_exit(self.on_mouse_hover_exit)
    
    @property
    def scale(self):
        return utils.ui.get_ui_scale()

    @property
    def texcoords(self):
        return self._texcoords

    @texcoords.setter
    def texcoords(self, value):
        self._texcoords = value

    def set_image(self, rel_filepath):
        try:
            self._image = bpy.data.images.load(rel_filepath, check_existing=True)
            self._image.alpha_mode = 'STRAIGHT' 
            self._texture = gpu.texture.from_image(self._image)
        except:
            pass

    def set_shader(self, shader):
          self._shader = shader

    def update(self, x, y):
        self._textpos = [x, y]
        self.x_screen = x
        self.y_screen = y
        
        if self._shader is not None:

            off_x, off_y = self._image_position #(self.width * 2, -title.height - (self._image_size[1]/2) - title.size[1]/2) #self._image_position
            off_x *= self.scale
            off_y *= self.scale

            sx, sy = self._image_size
            sx *= self.scale
            sy *= self.scale

            indices = ((0, 1, 2), (0, 2, 3))
            left, right, top, bottom = self.calc_button_bounds()
            bottom_left = (left, bottom)
            top_left = (left, top)
            top_right = (right, top)
            bottom_right = (right, bottom)
            # bottom left, top left, top right, bottom right
            vertices = (bottom_left, top_left, top_right, bottom_right)
            
            self._batch = batch_for_shader(self._shader, 'TRIS',
            { "pos" : vertices, 
            }, indices= indices)

            self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')


    def draw(self):
        if not self.visible:
            return
            
        self.shader.bind()       
        self.set_colors()    
        state.blend_set('ALPHA')   

        self.draw_shader()

        state.blend_set('NONE')

    def draw_text(self, area_height):
        blf.size(0, self._text_size)
        size = blf.dimensions(0, self._text)

        textpos_y = area_height - self._textpos[1] + (size[1]) #/ 2.0
        blf.position(0, self._textpos[0] + (self.width - size[0]) / 2.0, textpos_y + 1, 0)

        r, g, b, a = self._text_color
        if self._state == 2:
            r, g, b, a = (0.0, 1.0, 0.0, 1.0)

        blf.color(0, r, g, b, a)

        blf.draw(0, self._text)


    def draw_image(self):
        if self._image is not None:
            try:
                y_screen_flip = self.get_area_height() - self.y_screen
        
                off_x, off_y = self._image_position
                sx, sy = self._image_size


                utils.draw_2d.draw_rectangle(size=2,color=(1,1,1,1), center = (self.x_screen + off_x, y_screen_flip - off_y))
                utils.draw_2d.draw_rectangle(size=2,color=(1,0,0,1), center = (self.x_screen + off_x + sx, y_screen_flip - sy - off_y))

                # bottom left, top left, top right, bottom right
                vertices = (
                            (self.x_screen + off_x, y_screen_flip - off_y), 
                            (self.x_screen + off_x, y_screen_flip - sy - off_y), 
                            (self.x_screen + off_x + sx, y_screen_flip - sy - off_y),
                            (self.x_screen + off_x + sx, y_screen_flip - off_y))
                

                gpu.state.blend_set('ALPHA')

                shader = gpu.shader.from_builtin('IMAGE')

                shader.bind()
                shader.uniform_sampler("image", self._texture)
                self._batch.draw(shader) 
                return True
            except:
                pass

        return False


    def draw_shader(self):
        if self._shader is not None and self._batch is not None:
            try:
                y_screen_flip = self.get_area_height() - self.y_screen
        
                off_x, off_y = (0,0)
                off_x *= self.scale
                off_y *= self.scale

                sx, sy = (32, 32)
                sx *= self.scale
                sy *= self.scale
           
                shader = self._shader
               
                shader.bind()
                shader.uniform_float("Color", self.text_color )
                shader.uniform_float("u_scale", self.scale)

                shader.uniform_float("u_position", [self.x_screen, y_screen_flip])
                shader.uniform_float("u_active", self._active)

                self._batch.draw(shader)
                return True
            except:
                pass

        return False

    
    def calc_button_bounds(self):
        area_height = self.get_area_height()
        left = self.x_screen
        right = self.x_screen + (self.width) * self.scale
        top = area_height - self.y_screen + (self.height * self.scale)
        bottom =  top - (self.height * self.scale)

        return left, right, top, bottom
        

    def is_in_rect(self, x, y):
        left, right, top, bottom = self.calc_button_bounds()
        if (
            (left <= x <= right) and 
            (top >= y >= (bottom))
            ):
            return True
           
        return False      

    def handle_event(self, event):
        x = event.mouse_region_x
        y = event.mouse_region_y

        if(event.type == 'LEFTMOUSE'):
            if(event.value == 'PRESS'):
                self._mouse_down = True
                return self.mouse_down(x, y)
            else:
                self._mouse_down = False
                self.mouse_up(x, y)
                
        elif(event.type == 'MOUSEMOVE'):
            self.mouse_move(x, y)

            inrect = self.is_in_rect(x, y)

            # we enter the rect
            if not self._inrect and inrect:
                self._inrect = True
                self.mouse_enter(event, x, y)
                return True

            # we are leaving the rect
            elif self._inrect and not inrect:
                self._inrect = False
                self.mouse_exit(event, x, y)

            return False

        elif event.value == 'PRESS' and (event.ascii != '' or event.type in self.get_input_keys()):
            return self.text_input(event)
                        
        return False 

    def on_mouse_hover(self):
        self.text_color = (0.9, 0.9, 0.9, 1.0)
    
    def on_mouse_hover_exit(self):
        self.text_color = (0.8, 0.8, 0.8, 0.9)



class Title_Bar(bl_ui_widget.BL_UI_Widget):
    def __init__(self, context, parent_widget, x, y, width, height, title_text, minimize_button=True, pin_button=True):
        
        super().__init__(x, y, width, height)
        self.context = context
        self._parent_widget = parent_widget
        self.y_offset = 0
       
        if title_text is not None:
            self._title_text_label = self.create_title_text_label(context, title_text)

        # Use self.height as the width for the button since they are square
        button_size = self.height
        if minimize_button:
            self.minimize_button = Button(self.context, self.width - (2 * button_size), 0, button_size, button_size)
            self.minimize_button.set_image_position((-2, -1920 - self.minimize_button.height))
            self.minimize_button.set_image_size((1080, 1920))
            shader = utils.shaders.create_2d_shader(fragment_shader="icon_minimize_fs.glsl")
            self.minimize_button.set_shader(shader)
            self.minimize_button._active = utils.common.prefs().panel_minimized
            self.minimize_button.set_mouse_down(self.on_minimized_button_clicked)

        if pin_button:
            self.pin_button = Button(self.context, self.width, 0, button_size, button_size)
            self.pin_button.set_image_position((-2, -1920 - self.pin_button.height))
            self.pin_button.set_image_size((1080, 1920))
            shader = utils.shaders.create_2d_shader(fragment_shader="icon_test_fs.glsl")
            self.pin_button.set_shader(shader)

            self.pin_button._active = utils.common.prefs().panel_locked
            self.pin_button.set_mouse_down(self.on_pin_button_clicked)
            

        self.init(context)

    
    @property
    def scale(self):
        return utils.ui.get_ui_scale()
    
    @property
    def title_text(self):
        return self._title_text_label.text
    
    @title_text.setter
    def title_text(self, value):
        self._title_text_label.text = value


    def can_move_parent(self):
        return self._inrect


    def create_title_text_label(self, context, text):
        h_offset = 2 * self.scale
        v_offset = 8 * self.scale
        label = TextLabel(h_offset, self.height * self.scale / 2 - v_offset, 20, 10, 1, context, text) #40, 65
        label.text_color = (1.0, 1.0, 1.0, 0.5)
        label.text_size = 16
        label._font_id = 1

        return label

    def update(self, x, y):
        width = self.width * self.scale
        height = self.height * self.scale

        self.x_screen = x
        self.y_screen = y

        self._title_text_label.update(x, y)
        x_offset = self.pin_button.width * self.scale
        self.pin_button.update(self.x_screen + width - x_offset, self.y_screen)
        self.minimize_button.update(self.x_screen + width - 2.0 * x_offset, self.y_screen)


        area_height = self.get_area_height()
                
        indices = ((0, 1, 2), (0, 2, 3))

        y_screen_flip = area_height - self.y_screen

        button_widths = 0 # TODO: Add other buttons.
        # top left, bottom left, top right, bottom right
        vertices = (
                    (self.x_screen, y_screen_flip), 
                    (self.x_screen, y_screen_flip + height), 
                    (self.x_screen + width + button_widths, y_screen_flip + height),
                    (self.x_screen + width + button_widths, y_screen_flip))
                    
        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.batch_panel = batch_for_shader(self.shader, 'TRIS', {"pos" : vertices}, indices=indices)
        
    
    def draw(self):
        super().draw()
        self._title_text_label.draw()
        self.pin_button.draw()
        self.minimize_button.draw()
        # DEBUG
        # area_height = self.get_area_height()       
        # y_screen_flip = area_height - self.y_screen

        # width = (self.width - (self.pin_button.width + self.minimize_button.width)) * self.scale
        # height  = self.height * self.scale
        # utils.draw_2d.draw_rectangle(size=2,color=(1,1,1,1), center = (self.x_screen, y_screen_flip))
        # utils.draw_2d.draw_rectangle(size=2,color=(1,0,0,1), center =  (self.x_screen + width, y_screen_flip + height))


    def is_in_rect(self, x, y):
        area_height = self.get_area_height()

        width = self.width * self.scale
        height = self.height * self.scale

        widget_y = area_height - self.y_screen
        y_offset = 0
        # Subtract the width of the minimize button. Not ideal.
        if (self.x_screen <= x <= (self.x_screen + width ) - (self.minimize_button.width + self.pin_button.width) * self.scale):
            if ((widget_y + height) + y_offset >= y >= widget_y + y_offset):
                return True
        
        return False  

    
    def handle_event(self, event):
      
        x = event.mouse_region_x
        y = event.mouse_region_y

        handled = False

        if not handled:
            handled = self.pin_button.handle_event(event)
        if not handled:
            handled = self.minimize_button.handle_event(event)

        if not handled:
            if(event.type == 'LEFTMOUSE'):
                if(event.value == 'PRESS'):
                    self._mouse_down = True
                    handled = self.mouse_down(x, y)

                    if utils.common.prefs().panel_locked:
                        return False
                else:
                    self._mouse_down = False
                    self.mouse_up(x, y)
                    
            elif(event.type == 'MOUSEMOVE'):
                self.mouse_move(x, y)
                inrect = self.is_in_rect(x, y)

                # we enter the rect
                if not self._inrect and inrect:
                    self._inrect = True
                    self.mouse_enter(event, x, y)

                # we are leaving the rect
                elif self._inrect and not inrect:
                    self._inrect = False
                    self.mouse_exit(event, x, y)

        return handled 
    
    def on_pin_button_clicked(self):
        toggle_panel_locked()
        self.pin_button._active = utils.common.prefs().panel_locked

    def on_minimized_button_clicked(self):
        toggle_panel_minimized()
        self.minimize_button._active = utils.common.prefs().panel_minimized
        visible = self._parent_widget.get_child_visibility_by_name("Extras")
        self._parent_widget.set_child_visibility_by_name("Extras", not visible)
        self._parent_widget.layout_widgets()


# class Widget_Base(bl_ui_widget.BL_UI_Widget):

#     def __init__(self, x, y, width, height):
#         super().__init__(x, y, width, height)

#         del bl_ui_widget.BL_UI_Widget.width
#         del bl_ui_widget.BL_UI_Widget.height

#         self._width = 0
#         self._height = 0

#     @property
#     def width(self):
#         return self._width

#     @width.setter
#     def width(self, value):
#         self._width = value

#     @property
#     def height(self):
#         return self._height

#     @height.setter
#     def height(self, value):
#         self._height = value


    # def handle_event(self, event):
    #     x = event.mouse_region_x
    #     y = event.mouse_region_y

    #     if(event.type == 'LEFTMOUSE'):
    #         if(event.value == 'PRESS'):
    #             self._mouse_down = True
    #             return self.mouse_down(x, y)
    #         else:
    #             self._mouse_down = False
    #             self.mouse_up(x, y)
                
        
    #     elif(event.type == 'MOUSEMOVE'):
    #         self.mouse_move(x, y)

    #         inrect = self.is_in_rect(x, y)

    #         # we enter the rect
    #         if not self.__inrect and inrect:
    #             self.__inrect = True
    #             self.mouse_enter(event, x, y)

    #         # we are leaving the rect
    #         elif self.__inrect and not inrect:
    #             self.__inrect = False
    #             self.mouse_exit(event, x, y)

    #         return False

    #     elif event.value == 'PRESS' and (event.ascii != '' or event.type in self.get_input_keys()):
    #         return self.text_input(event)
                        
    #     return False 