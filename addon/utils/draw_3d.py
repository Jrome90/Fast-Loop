from contextlib import suppress
from typing import *
from abc import ABCMeta

from math import radians

import bpy
import blf
import gpu

from gpu import state
from gpu_extras.batch import batch_for_shader
from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Vector, Matrix

from . import ui, common, draw_2d

def draw_debug_points(points, colors, size=3.0):
    ui_scale = ui.get_ui_scale()
    state.point_size_set(size * ui_scale)

    state.depth_test_set('LESS_EQUAL')

    shader = gpu.shader.from_builtin('FLAT_COLOR')
    batch = batch_for_shader(shader, 'POINTS', {"pos": points, "color": colors})
    shader.bind()

    batch.draw(shader)
    state.depth_test_set('NONE')



def draw_point(point, color=(1.0, 1.0, 0.0, 1), size=3.0, depth_test=False):
    draw_points([point], color=color, size=size, depth_test=depth_test)


def draw_points(points, color=(1.0, 1.0, 0.0, 1), size=3.0, depth_test=False):
    ui_scale = ui.get_ui_scale()
    state.point_size_set(size * ui_scale)

    if  depth_test:
        state.depth_test_set('LESS_EQUAL')
   
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'POINTS', {"pos": points})
    shader.bind()
    shader.uniform_float("color", color)

    batch.draw(shader)

    state.depth_test_set('NONE')

def draw_line_loop(points, line_color=(0.0, 1.0, 0.5, 0.9), line_width=1.0, depth_test=False):
    ui_scale = ui.get_ui_scale()
    r, g, b, a = line_color
    if depth_test:
        state.depth_test_set('LESS_EQUAL')

    state.blend_set('ALPHA') if a < 1 else state.blend_set('NONE')

    shader = gpu.shader.from_builtin('POLYLINE_SMOOTH_COLOR')
    batch = batch_for_shader(shader, 'LINE_LOOP', {"pos": points, "color": [line_color] * len(points)})
    
    shader.bind()
    shader.uniform_float("lineWidth", line_width * ui_scale)
    shader.uniform_float("viewportSize", (bpy.context.area.width, bpy.context.area.height))
    batch.draw(shader)

    state.depth_test_set('NONE')
    state.blend_set('NONE')


def draw_line(points, line_color=(0.0, 1.0, 0.5, 0.9), line_width=1.0, depth_test=False):
    ui_scale = ui.get_ui_scale()
    a = line_color[3]

    if depth_test:
        state.depth_test_set('LESS_EQUAL')

    state.blend_set('ALPHA') if a < 1 else state.blend_set('NONE')

    shader = shader = gpu.shader.from_builtin('POLYLINE_SMOOTH_COLOR')
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": points, "color": [line_color] * len(points)})
    
    shader.bind()
    shader.uniform_float("lineWidth", line_width * ui_scale)
    shader.uniform_float("viewportSize", (bpy.context.area.width, bpy.context.area.height))

    batch.draw(shader)

    state.depth_test_set('NONE')


def draw_lines(points,  line_color=(0.0, 1.0, 0.5,.4), line_width=1.0, depth_test=False):
    ui_scale = ui.get_ui_scale()
    shader = gpu.shader.from_builtin('POLYLINE_SMOOTH_COLOR')
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": points, "color": [line_color] * len(points)})
    
    shader.bind()
    r, g, b, a = line_color

    if depth_test:
        state.depth_test_set('LESS_EQUAL')

    state.blend_set('ALPHA') if a < 1 else state.blend_set('NONE')

    shader.uniform_float("lineWidth", line_width * ui_scale)
    shader.uniform_float("viewportSize", (bpy.context.area.width, bpy.context.area.height))
    batch.draw(shader)

    state.depth_test_set('NONE')

def batch_from_points(points, type_, shader):
    return batch_for_shader(shader, type_, {"pos": points})


def draw_arrow(start:Vector, end:Vector, plane_normal:Vector, direction_vec:Vector, chevron_length=1.0, line_color=(1.0, 1.0, 1.0,.4),line_width=1.0):
    draw_line((start, end), line_color=line_color, line_width=line_width)
    line: Vector = direction_vec

    line_perp: Vector = line.cross(plane_normal) * chevron_length
    rot_mat = Matrix.Rotation(radians(-90), 4, plane_normal)
    line_perp.rotate(rot_mat)
    draw_line((end, end+line_perp), line_color=line_color, line_width=line_width)

    line_perp2: Vector = line.cross(plane_normal) * chevron_length
    rot_mat = Matrix.Rotation(radians(90), 4, plane_normal)
    line_perp2.rotate(rot_mat)
    draw_line((end, end+line_perp2), line_color=line_color, line_width=line_width)


class Drawable3D(metaclass=ABCMeta):
    def __init__(self) -> None:
        self.bounding_box = [Vector((0.0, 0.0, 0.0))]*4
        self.calculate_bounding_box()

    def calculate_bounding_box(self) -> List[Vector]:
        pass

    def draw_debug_bbox(self):
         # draw debug BBox corners
        for i, (corner) in enumerate(self.bounding_box):
            if i < 2:
                draw_point(corner, color=(0.0, 1.0 ,0.0, 1.0)) # top
            else:
                draw_point(corner, color=(0.0, 0.0 ,1.0, 1.0)) # bottom
    
    def draw(self):
        pass

    def draw_2d(self):
        pass

class Arrow(Drawable3D):

    def __init__(self, start: Vector, end: Vector, plane_normal: Vector, direction_vector:Vector, chevron_length=1.0, line_color=(1.0, 1.0, 1.0,.4), line_width=1.0):
        self.direction_vector = direction_vector
        self.start: Vector = start
        self.end: Vector = end
        self.chevron_length = chevron_length
        self.line_color = line_color
        self.line_width = line_width
        self.plane_normal = plane_normal
        self.plane_x = None
        self.plane_y = None

        self._label_text = None
        # Screen Space
        self._label_pos = None
        self.display_label = True
        super().__init__()

    
    @property
    def label_text(self):
        return self._label_text

    @label_text.setter
    def label_text(self, value):
        self._label_text = value

    @property
    def label_position(self):
        return self._label_pos

    @label_position.setter
    def label_position(self, value):
        self._label_pos = value


    def calculate_bounding_box(self):
        origin = self.start
        end = self.end
        direction_vec: Vector = (end - origin).normalized()
        self.plane_x =  direction_vec
        self.plane_y = (self.plane_normal).cross(self.plane_x)

        line_perp: Vector =  Vector((0,1)) * self.chevron_length

        rot_mat = Matrix.Rotation(radians(45), 2)
        line_perp = rot_mat @ line_perp

        e_1: Vector = (self.plane_x)
        e_2: Vector = (self.plane_y)
        basis_mat:Matrix = Matrix([(e_1.x, e_2.x),
                                   (e_1.y, e_2.y),
                                   (e_1.z, e_2.z)])
       
        v = (basis_mat @ Vector((0, line_perp.y)))

        self.bounding_box[0] = end + v
        self.bounding_box[1] = origin + v
        self.bounding_box[2] = end - v
        self.bounding_box[3] = origin - v
     

    def draw(self):
        draw_arrow(self.start, self.end, self.plane_normal, self.direction_vector, self.chevron_length, line_color=common.prefs().distance_line_color, line_width=1)
        # self.draw_debug_bbox()


    def draw_2d(self):
        if self.bounding_box and self.display_label:
            self.draw_label()
    

    def draw_label(self):
        
        position = self.bounding_box[2].lerp(self.bounding_box[3], 0.5)
        
        context = bpy.context
        position_2d = location_3d_to_region_2d(context.region, context.space_data.region_3d, position)
        position_end_2d = location_3d_to_region_2d(context.region, context.space_data.region_3d, self.plane_y * 0.001) # Scale the vector down
        if position_end_2d is None:
            return
        position_end_2d = position_2d + position_end_2d.normalized()
        # scale = get_ui_scale()
        font_size = int(10)

        blf.size(0, font_size)
        w, _ = blf.dimensions(0, self.label_text)

        half_w = w * 0.5

        top_left_text =  position_2d + Vector((-half_w, 0))
        with suppress(AttributeError):
            p = (top_left_text - position_2d).project(position_end_2d - position_2d)

        p = position_2d + (position_2d - position_end_2d).normalized() * p.length
        draw_2d.draw_text_on_screen(self.label_text, p, 10, text_color=common.prefs().distance_display_text_color, h_alignment='CENTER', v_alignment='CENTER')
        
