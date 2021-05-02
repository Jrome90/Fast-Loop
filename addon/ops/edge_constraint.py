from typing import *
from dataclasses import dataclass, field

import bpy, bmesh
from bmesh.types import *
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_point_line, intersect_line_plane

from .. import utils

@dataclass
class EdgeVertexSlideData():
    
    vert: BMVert = None
    vert_orig_co: Vector = None
    vert_side: List[BMVert] = field(default_factory=lambda: [None, None])
    # Store a copy of other verts co vector here
    dir_side: List[Vector] =  field(default_factory=lambda: [None, None])

    edge_len: List[float] = field(default_factory=lambda: [None, None])    

    def __repr__(self) -> str:
        vert_side_a = self.vert_side[0].index if self.vert_side[0] is not None else None
        vert_side_b = self.vert_side[1].index if self.vert_side[1] is not None else None
        string = f"vert_side: a {vert_side_a}; b {vert_side_b} \n"
        string += f"dir_side: a {self.dir_side[0]}; b {self.dir_side[1]} \n"
        return string


class EdgeConstraint_Translation():
    active_axis = None
    axis_vec = None
    axis_draw_points = []
    axis_draw_colors = []
    slide_edge_draw_lines = []

    def finished(self, context):
        self.axis_draw_points.clear()

    def draw_callback_3d(self, context):
         if self.slide_edge_draw_lines:
            for line in self.slide_edge_draw_lines:
                utils.drawing.draw_line(line, line_width=3)

    def draw_callback_px(self, context):
        if self.axis_draw_points:
            for i, points in enumerate(self.axis_draw_points):
                utils.drawing.draw_line_2d(points, line_color=self.axis_draw_colors[i], line_width=1)
    
    def calculate_axis_draw_points(self, context, nearest_vert, current_axis, world_mat):
        self.axis_draw_points.clear()
        axis_color = {"X": [1, 0, 0, 1], "Y": [0, 1, 0, 1], "Z":[0, 0, 1, 1]}
        for axis, color in axis_color.items():
            # Multiply by 0.001 to fix an issue caused when the vector is too far out when put into screen space.
            # Not sure how to handle this preoperly yet.
            axis_vec = self.get_axis(axis, world_mat) * 0.001
            if axis_vec is not None:
                p1 = utils.math.location_3d_to_2d(world_mat @ nearest_vert.co.copy())
                p2 = utils.math.location_3d_to_2d(world_mat @ nearest_vert.co.copy() + axis_vec)
                size_px = 50 * utils.ui.get_ui_scale()
                
                axis_2d = (p2-p1)
                axis_2d.normalize()
                axis_2d *= size_px
                self.axis_draw_points.append([p1, p1 + axis_2d])

                if axis != current_axis:
                    color[3] = 0.2
                self.axis_draw_colors.append(color)

    
    def calculate_slide_draw_lines(self, nearest_vert, slide_verts, world_mat):
        nearest_vert_data: EdgeVertexSlideData = slide_verts[nearest_vert.index]
        lines = []
        for side in nearest_vert_data.dir_side:
            if side is not None:
                lines.append([world_mat @ self.nearest_vert_co, world_mat @ side])
        return lines


    def get_slide_edges(self, selected_verts, axis_vec_og, world_mat):

        to_origin = Matrix.Translation(-world_mat.to_translation()) @ world_mat
        axis_vec = -axis_vec_og.copy()

        slide_verts: Dict[int ,EdgeVertexSlideData] = {}
        for v in selected_verts:

            slide_verts[v.index] = EdgeVertexSlideData()
            sv: EdgeVertexSlideData = slide_verts[v.index]
            sv.vert = v
            sv.vert_orig_co =  v.co.copy()
            
            alpha = 0.0
            beta = 0.0
            for edge in v.link_edges:
                other_vert = edge.other_vert(v)
                dir = to_origin @ (other_vert.co - v.co)
       
                dir_norm = dir.copy()
                dir_norm.normalize()
                dir_norm = dir_norm

                axis_vec *= -1
                d1 = dir_norm.dot(axis_vec)
               
                cos_theta = float('-INF')
                if dir_norm.length > 0.0:
                    cos_theta = d1 

                epsilon = 0.001
                if cos_theta >= utils.math.clamp(0.0, alpha - epsilon, 1) and not (abs(cos_theta) < 0.1):
                    
                    sv.dir_side[0] = other_vert.co.copy()
                    sv.vert_side[0] = other_vert
                    sv.edge_len[0] = dir.length
                    alpha = cos_theta

                axis_vec *= -1 
                d2 = dir_norm.dot(axis_vec)
                cos_theta = float('-INF')
                if dir_norm.length > 0.0:  
                    cos_theta = d2
               
                if cos_theta >= utils.math.clamp(0.0, beta - epsilon, 1.0) and not (abs(cos_theta) < 0.1):
                    sv.dir_side[1] = other_vert.co.copy()
                    sv.vert_side[1] = other_vert
                    sv.edge_len[1] = dir.length
                    beta = cos_theta 

        return slide_verts

    #TODO: Fix invalid bm vert error when undoing while edge constaitn is active
    def edge_constraint_slide(self, context, mouse_coords, axis, world_mat):
        ray_origin, ray_dir_vec = utils.raycast.get_ray(context.region, context.region_data, mouse_coords)
        plane_co = world_mat @ self.nearest_vert_co
        plane_n = axis

        proj_vec = utils.math.project_point_plane(plane_n, ray_dir_vec)
        proj_vec.normalize()

        factor = utils.math.ray_plane_intersection(plane_co, plane_n, ray_origin, proj_vec)

        to_origin = Matrix.Translation(-world_mat.to_translation()) @ world_mat
        from_origin = to_origin.inverted_safe()
     
        for data in self.slide_verts.values():

            vert = data.vert

            dir_a = data.dir_side[0]
            dir_b = data.dir_side[1]

            if factor > 0 and dir_a is not None:
                other_vert_co = dir_a
                dir_edge_a = [data.vert_orig_co, other_vert_co]
                
                start: Vector = to_origin @ dir_edge_a[0]
                end: Vector = to_origin @ dir_edge_a[1]

                # if  use_indiviual_orgins:
                #     dir_vec =  ((end-start).normalized())
                #     self.axis_vec = dir_vec * self.slide_value
               
                plane_offset = axis * factor
                plane_normal = axis
                
                intersect_vec = intersect_line_plane(start, end, start + plane_offset, plane_normal)

                if intersect_vec:
                    perc = intersect_point_line(intersect_vec, start, end)[1]
                    if 1.0 >= perc >= 0.0:
                        vert.co = from_origin @ intersect_vec

            elif factor < 0.0 and dir_b is not None:
                other_vert_co = dir_b
                dir_edge_b = [data.vert_orig_co, other_vert_co]

                axis_vec_copy = axis.copy()
                axis_vec_copy.negate()
                axis_vec_opp = axis_vec_copy

                start: Vector = to_origin @ dir_edge_b[0]
                end: Vector = to_origin @ dir_edge_b[1]

                # if  use_indiviual_orgins:
                #     dir_vec =  ((end-start).normalized())
                #     axis_vec_opp = dir_vec * -self.slide_value
               
                plane_offset = axis_vec_opp * -factor
                plane_normal = axis_vec_opp

                intersect_vec = intersect_line_plane(start, end, start + plane_offset, plane_normal)
                if intersect_vec:
                    perc = intersect_point_line(intersect_vec, start, end)[1]
                    if 1.0 >= perc >= 0.0:
                        vert.co = from_origin @ intersect_vec
               
        bmesh.update_edit_mesh(context.active_object.data, destructive=False)

    
    def get_axis(self, axis, world_mat):
        axis_lookup = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1))}
        slot = bpy.context.window.scene.transform_orientation_slots[0]
        transform_orientation = slot.type
        if transform_orientation == 'GLOBAL':
            return axis_lookup[axis]

        elif transform_orientation == 'LOCAL':
                return world_mat.to_3x3() @ axis_lookup[axis]

        elif transform_orientation == 'VIEW':
            view_mat = bpy.context.region_data.perspective_matrix.to_3x3().normalized().inverted()
            if axis != "Z":
                return view_mat @ axis_lookup[axis]
            else:
                return None

        elif transform_orientation == 'CURSOR':
            cursor_mat = bpy.context.scene.cursor.matrix
            return cursor_mat.to_3x3() @ axis_lookup[axis]

        else:
            custom_mat = slot.custom_orientation.matrix
            return custom_mat.to_3x3() @ axis_lookup[axis]

  
def get_valid_orientation():
    valid_types = {'GLOBAL','LOCAL', 'VIEW', 'CURSOR'}
    invalid_types = {'NORMAL', 'GIMBAL'}
    transform_orientation =  bpy.context.window.scene.transform_orientation_slots[0].type
    if transform_orientation in valid_types or transform_orientation not in invalid_types:
        return transform_orientation
    else:
        return None

def edge_constraint_status(layout):
    orientation = get_valid_orientation()
    if orientation is not None:                
        layout.label(text=f"Edge Constraint:({orientation})",)
        layout.label(text="X Axis", icon='EVENT_X')
        layout.label(text="Y Axis", icon='EVENT_Y')
        layout.label(text="Z Axis", icon='EVENT_Z')

