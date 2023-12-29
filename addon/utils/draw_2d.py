from typing import List
import blf
import gpu

from gpu import state
from gpu_extras.batch import batch_for_shader
from gpu_extras import presets
from mathutils import Vector, Color

from struct import pack

from . ui import get_ui_scale, get_headers_height

def batch_from_points(points, type_, shader):
    return batch_for_shader(shader, type_, {"pos": points})

def draw_points(points, color=(.0, 1.0, 0.0, 1), size=3.0):
    ui_scale = get_ui_scale()
    state.point_size_set(size * ui_scale)
    
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'POINTS', {"pos": points})
    shader.bind()
    shader.uniform_float("color", color)

    batch.draw(shader)

def draw_line(points, line_color=(0.0, 1.0, 0.5, 0.4), line_width=1.0):
    ui_scale = get_ui_scale()
    state.line_width_set(line_width * ui_scale)

    state.blend_set('ALPHA')

    # bgl.glEnable(bgl.GL_LINE_SMOOTH)

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_from_points(points, 'LINE_STRIP', shader)
    
    shader.bind()
    color = shader.uniform_from_name("color")
    r, g, b, a = line_color
    shader.uniform_vector_float(color, pack("4f", r, g, b, a), 4)
    batch.draw(shader)


def draw_line_smooth(points, line_colors, line_width):
    #POLYLINE_SMOOTH_COLOR

    ui_scale = get_ui_scale()
    state.line_width_set(line_width * ui_scale)

    state.blend_set('ALPHA')

    # bgl.glEnable(bgl.GL_LINE_SMOOTH)

    shader = gpu.shader.from_builtin('POLYLINE_SMOOTH_COLOR')
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": points, "color": line_colors})
    
    shader.bind()
    # color = shader.uniform_from_name("color")
    # r, g, b, a = line_color
    # shader.uniform_vector_float(color, pack("4f", r, g, b, a), 4)
    batch.draw(shader)

def draw_rectangle(size=10, color=(1.0, 1.0, 1.0, 1.0), center=(0,0)):
    size *= get_ui_scale()
    bottom_left = Vector(center) + Vector((-1,-1)) * size
    bottom_right = Vector(center) + Vector((1,-1)) * size
    top_right = Vector(center) + Vector((1,1)) * size
    top_left = Vector(center) + Vector((-1,1)) * size
    vertices = (top_left, top_right, bottom_right, bottom_left)


    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINE_LOOP', {"pos": vertices})


    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)

def draw_circle(center, radius, color: Color = (1,1,1,1)):
    ui_scale = get_ui_scale()
    presets.draw_circle_2d(center, color, radius * ui_scale)


def draw_line_strip(coords, line_width=2):
   
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": coords})
    ui_scale = get_ui_scale()
    state.line_width_set(line_width * ui_scale)

    shader.bind()
    shader.uniform_float("color", (1, 1, 1, 1.0))
    batch.draw(shader)

    state.line_width_set(1)
    state.blend_set('NONE')


def draw_region_border(context, line_color=(1, 1, 1, 1), width=2, text="Selection"):
    region = context.region
    scale = get_ui_scale()
    width *= scale
    header_height = get_headers_height()
    top_left = Vector((width, region.height - (width + header_height)))
    top_right = Vector((region.width - width, region.height - (width + header_height)))
    bottom_right = Vector((region.width - width, width))
    bottom_left = Vector((width, width))
    vertices = (top_left, top_right, bottom_right, bottom_left,)

    state.line_width_set(width)

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    shader.bind()

    shader.uniform_float("color", line_color)

    batch = batch_for_shader(shader, 'LINE_LOOP', {"pos": vertices})
    batch.draw(shader)

    if text:

        font_size = int(16 * scale)

        blf.size(0, font_size)
        blf.color(0, *line_color)

        center = (region.width) / 2 - 20
        blf.position(0, center - int(60 * scale), region.height - header_height - int(font_size) - 5, 0)

        blf.draw(0, text)

def draw_text_on_screen(text, position, font_size, text_dim=None, text_color=(1.0, 1.0, 1.0, 1.0), h_alignment: set=None, v_alignment: set=None, rotation=None):
    if  position is None:
        return

    scale = get_ui_scale()
    font_size = int(font_size * scale)

    blf.color(0, *text_color)
    blf.size(0, font_size)
    # if not (h_aligned_center and not v_aligned_center):
    #     blf.position(0, position[0], position[1], 0)
    # else:
    h_pos = position[0]
    v_pos = position[1]

    if text_dim is None:
        width, height = blf.dimensions(0, text)
    else:
        # This is dumb. But it's annoying when the height of the text changes the position when v_align is TOP
        width, height = text_dim
        if width is None:
            width, _ = blf.dimensions(0, text)
        height *= scale


    half_width = width * 0.5
    half_height = height * 0.5
    if h_alignment:
        if 'CENTER' in h_alignment:
            h_pos = position[0] - half_width
    
    if v_alignment:
        if 'CENTER' in v_alignment:
            v_pos = position[1] - half_height
        elif 'TOP' in v_alignment:
            v_pos = position[1] - (2 * height)
        elif 'BOTTOM' in v_alignment:
            v_pos =  v_pos = position[1] + (2 * height)

    # h_aligned_center = False if 'CENTER' not in h_alignment else True
    # v_aligned_center = False if 'CENTER' not in v_alignment else True
    # v_aligned_top = False if 'TOP' not in v_alignment else True


    # h_pos = position[0] - half_width if h_aligned_center else position[0]
    # v_pos = position[1] - half_height if v_aligned_center else position[1]

    blf.position(0, h_pos, v_pos, 0)
    # if rotation is not None:
    #     blf.enable(0, blf.ROTATION)        
    #     blf.rotation(0, rotation)
    # else:
    #     blf.disable(0, blf.ROTATION)        

    blf.draw(0, text)

    # if rotation is not None:
    #     blf.disable(0, blf.ROTATION)        
    #     blf.rotation(0, 0)



def draw_debug_text_border(position:Vector, font_size, line_color=(1, 1, 1, 1), text="Selection"):
    
    scale = get_ui_scale()
    #font_size = int(font_size * scale)
    height =  int(font_size * scale)
    width = font_size * len(text) * (0.60)

    
    width *= scale
    top_left = position + Vector((0, height))
    top_right = position + Vector((width, height))
    bottom_right = position + Vector((width, -height* 0.25))
    bottom_left = position + Vector((0, -height* 0.25))


    vertices = (top_left, top_right, bottom_right, bottom_left,)

    state.line_width_set(1)

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    shader.bind()

    shader.uniform_float("color", line_color)

    batch = batch_for_shader(shader, 'LINE_LOOP', {"pos": vertices})
    batch.draw(shader)