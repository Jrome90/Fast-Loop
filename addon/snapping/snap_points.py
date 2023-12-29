from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .snapping import Nearest_2d , SnapObjectEditMeshData
from math import isclose, modf

from bmesh.types import *
from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Vector

from .. import utils

class SnapPointsMixin():

    def __init__(self):

        # Todo: Add a setting in preferences to change this value
        self.snap_radius = 25**2 * utils.ui.get_ui_scale()
        self.radius = 10**2 * utils.ui.get_ui_scale()
        self.draw_snap_indicator = False

        self.snapped_loc = None
        self.draw_snap_points = []
        self.draw_mid_point = None
        self._preselect_vertex_co = None

        self._is_snap_points_locked = False
        self._auto_calc_snap_points = False
        self._snap_increment_divisions = 1
        self._snap_factor = 0.5
        self._use_distance = False
        self._snap_distance = 0.01 # Scene units
        self._increment_snap_points = []
        self._increment_snap_point_dist = {}
        self._locked_snap_edge_points = None
        self._locked_snap_edge_idx = None

    
    def draw_callback_3d(self, context):

        if self.draw_snap_points:
            for line_points in self.draw_snap_points:
                utils.draw_3d.draw_line(line_points, (1.0, 1.0, 1.0, 0.9), line_width=utils.common.prefs().snap_tick_width)

        if self.draw_mid_point is not None:
            utils.draw_3d.draw_point(self.draw_mid_point, color=utils.common.prefs().center_point_color, size=utils.common.prefs().center_point_size)


    def draw_callback_2d(self, context):
        if self._increment_snap_points:
            for i, (position, snap_pos) in enumerate(zip(self._increment_snap_points, self.draw_snap_points)):
                distance_text = self._increment_snap_point_dist.get(i+1, None)
                if distance_text is not None:
                    snap_point_ends = snap_pos
                    snap_point_dir_vec = (snap_point_ends[0] - snap_point_ends[1]) * 0.5
                    position_2d = location_3d_to_region_2d(self.region, self.rv3d, position + snap_point_dir_vec)

                    utils.draw_2d.draw_text_on_screen(distance_text, position_2d, 10, h_alignment={'CENTER'})
            
            if self.draw_snap_indicator:
                utils.draw_2d.draw_circle(location_3d_to_region_2d(self.region, self.rv3d, self.snapped_loc), 3 * utils.ui.get_ui_scale(), utils.ui.get_bl_active_object_color())

    def get_nearest_snap_point_to_mouse(self):
        nearest_point = None
        shortest_dist = float('INF')
        for point in self._increment_snap_points:
            point_2d = location_3d_to_region_2d(
                self.region, self.rv3d, point)

            if point_2d is not None:
                dist = (point_2d - self.mvals).length_squared

                if dist < self.snap_radius and dist < shortest_dist:
                    shortest_dist = dist
                    nearest_point = point
        return nearest_point


    def get_nearest_snap_point(self, snap_object, nearest_2d: Nearest_2d):
        self.do_snap_stuff(snap_object, nearest_2d)

        nearest_loc = self.get_nearest_snap_point_to_mouse()
        if nearest_loc is None:
            nearest_loc = nearest_2d.edge_co
            self.draw_snap_indicator = False
        else:
             self.snapped_loc = nearest_loc
             self.draw_snap_indicator = True
        element_index = nearest_2d.edge.index
        
        if not self.is_snap_points_locked:
            self._preselect_vertex_co = nearest_2d.vert_co
          
        return element_index, nearest_loc

    def do_snap_stuff(self, snap_object, nearest_2d: Nearest_2d):
        if not self.is_snap_points_locked:
            self._increment_snap_points.clear()
            self._increment_snap_point_dist.clear()

            self.draw_snap_points = []
            self._preselect_vertex_co = None
            self.draw_mid_point = None
            self._increment_snap_points, self._increment_snap_point_dist = self.calc_snap_edge_increments(snap_object, nearest_2d, self.region, self.rv3d)
            face = nearest_2d.face
            self.draw_snap_points = self.calculate_incremental_lines(snap_object, self._increment_snap_points, nearest_2d.edge, face)
            self._locked_snap_edge_idx = nearest_2d.edge

    def calc_snap_edge_increments(self, snap_object: SnapObjectEditMeshData, nearest_2d: Nearest_2d, region, rv3d):
        va_co = None
        vb_co = None
        ab_len = 0.0
        edge = nearest_2d.edge

        if edge is not None:
        
            vert_a: BMVert = edge.verts[0]
            va_co = vert_a.co
            
            vb_co = edge.other_vert(vert_a).co
            ab_len = (va_co - vb_co).length

            va_co_world = snap_object.object_matrix @ va_co
            vb_co_world = snap_object.object_matrix @ vb_co
            # ----
            
            va_co_2d: Vector = location_3d_to_region_2d(region, rv3d, va_co_world)
            vb_co_2d: Vector = location_3d_to_region_2d(region, rv3d, vb_co_world)
            start = va_co_world
            end = vb_co_world
            if self.use_distance:
                if va_co_2d is not None and vb_co_2d is not None:
                    
                    center_co_2d = location_3d_to_region_2d(region, rv3d, (va_co_world + vb_co_world) * 0.5)
        
                    dot_x = (va_co_2d - center_co_2d).normalized().dot(Vector((1,0)))

                    # Handle the case where the edge is perpendicular to the screen's X Axis
                    if isclose(dot_x, 0.0, abs_tol=1e-05):
                        dot_y = (va_co_2d - center_co_2d).normalized().dot(Vector((0,1)))
                        if  dot_y > 0: 
                            if utils.ops.options().snap_left:
                                start, end = end, start
                        elif dot_y < 0:
                            if utils.ops.options().snap_right:
                                start, end = end, start

                    # Handle the case where the edge is || to the screen's X Axis
                    elif isclose(dot_x, 1.0, abs_tol=1e-05):
                            if utils.ops.options().snap_left:
                                start, end = end, start
                            elif utils.ops.options().snap_right:
                                pass
                    
                    # Handle the case where the edge is || to the screen's X Axis
                    elif isclose(dot_x, -1.0, abs_tol=1e-05):
                            if utils.ops.options().snap_left:
                                pass
                            elif utils.ops.options().snap_right:
                                start, end = end, start

                    elif  dot_x > 0 and dot_x < 0.7071067: # A ------>

                        dot_y = (va_co_2d - center_co_2d).normalized().dot(Vector((0,1)))
                        if  dot_y > 0: 
                            if utils.ops.options().snap_left:
                                start, end = end, start
                        elif dot_y < 0:
                            if utils.ops.options().snap_right:
                                start, end = end, start

                    elif dot_x > 0 and dot_x > 0.7071067: # A ------>
                        dot_y = (va_co_2d - center_co_2d).normalized().dot(Vector((0,1)))
                        if  dot_y > 0: 
                            if utils.ops.options().snap_left:
                                start, end = end, start
                                
                        elif dot_y < 0:
                            if utils.ops.options().snap_right:
                                start, end = end, start

                    elif dot_x < 0 and dot_x > -0.7071067: # <------ A
                        dot_y = (va_co_2d - center_co_2d).normalized().dot(Vector((0,1)))
                        if  dot_y > 0: 
                            if utils.ops.options().snap_left:
                                start, end = end, start
                        elif dot_y < 0:
                            if utils.ops.options().snap_right:
                                start, end = end, start
                            
                    elif dot_x < 0 and dot_x < -0.7071067: # <------ A
                        dot_y = (va_co_2d - center_co_2d).normalized().dot(Vector((0,1)))
                        if  dot_y > 0: 
                            if utils.ops.options().snap_left:
                                start, end = end, start
                        elif dot_y < 0:
                            if utils.ops.options().snap_right:
                                start, end = end, start
                            

                    from_vert = nearest_2d.vert
                    if from_vert is not None:
                        vert_a: BMVert = from_vert
                        va_co = snap_object.object_matrix @ vert_a.co
                        vb_co = snap_object.object_matrix @ edge.other_vert(vert_a).co
                        if (vb_co - va_co).normalized().dot((end - start).normalized()) < 0:
                            if utils.ops.options().snap_left:
                                utils.ops.set_option("snap_right", True)
                                
                            elif utils.ops.options().snap_right:
                                utils.ops.set_option("snap_left", True)

            use_center = utils.ops.options().snap_center
            if use_center:
                start = (va_co_world + vb_co_world) * 0.5
                end =  nearest_2d.vert_co
                ab_len = ((va_co_world + vb_co_world) * 0.5 - end).length

                self.draw_mid_point = (va_co_world + vb_co_world) * 0.5

            self._locked_snap_edge_points = [va_co, vb_co]

        elif edge is None and self._locked_snap_edge_points is not None:
            va_co = self._locked_snap_edge_points[0]
            vb_co = self._locked_snap_edge_points[1]
            ab_len = (va_co - vb_co).length
            start = va_co
            end = vb_co

        n = self._snap_increment_divisions
        increment_snap_points = []
        snap_point_text = {}
        
        new_factor = 0.0
        if self.use_distance:

            n +=1
            distance = self._snap_distance
            unit_scale = 1 
            new_factor = (distance * unit_scale) / ab_len
            frac, max_n = modf(ab_len / distance)
            max_n = int(max_n)
            
            if isclose(new_factor, max_n, abs_tol=1e-05):
                return increment_snap_points, snap_point_text

            if isclose(frac, 1, abs_tol=1e-05) or frac >= new_factor:
                max_n += 1
            elif max_n == 1 and frac <= new_factor:
                max_n += 1
            n = max_n 

            if not self.auto_calc_snap_points:
                n = min(self._snap_increment_divisions + 1, max_n)

        for i in range(1 if self.use_distance and not use_center else 0, n):
            percent = 0.0
            if self.use_distance:
                percent = new_factor * i
            else:
                percent = ((1.0 + i) / (n + 1.0))

            position = start.lerp(end, percent)

            increment_snap_points.append(position)

            if use_center and i == 0:
                continue

            if (i % 4 == 0 and self._use_distance) or not self._use_distance:
                start_tmp = start
                if utils.ops.options().use_opposite_snap_dist and not use_center:
                    start_tmp = end

                pr = 2
                fmt = "%1." + str(pr) + "f"
                text = utils.ui.format_distance(fmt, "1", (position - start_tmp).length)
                i += 1 if use_center or not self._use_distance else 0
                snap_point_text[i] = text
              
        return increment_snap_points, snap_point_text
    

    def calculate_incremental_lines(self, snap_object, snap_points, bm_element, face):
        if bm_element is None:
            return
            
        bm = snap_object.bm
        bm.edges.ensure_lookup_table()
        loop = None
        edge: BMEdge = None
        if isinstance(bm_element, BMEdge):
            loop = utils.mesh.get_face_edge_share_loop(face, bm_element)
            edge = bm_element
        elif isinstance(bm_element, BMVert) :
            loop = utils.mesh.get_face_loop_for_vert(face, bm_element)
            edge = loop.edge
        
        edge_tangent = None
        if loop is not None:
            edge_tangent = edge.calc_tangent(loop)
            # Fix the rotations of the tangent vectors
            edge_tangent = utils.math.rotate_direction_vec(edge_tangent, snap_object.object_matrix)

        draw_snap_points = []

        for i, position in enumerate(snap_points):
            tick_len = 0.01
            i += 1 if not utils.ops.options().snap_center else 0
            if (i) % 4 == 0:
                tick_len = 0.03

            p1 = position
            p2 = position + ((edge_tangent.normalized() * tick_len))
            p2_scaled = utils.math.scale_points_about_origin([p2], p1, utils.ui.get_ui_scale())[0]
            draw_snap_points.append([p1, p2_scaled])

        return draw_snap_points