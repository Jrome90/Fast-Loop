from dataclasses import dataclass
from enum import IntFlag
from math import isclose

import bpy
from bpy.types import Object
import bmesh
from bmesh.types import *
from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_point_line

from .. import utils
from . import snap_math

""" A partial adaptation of the object/mesh snapping code found in Blender's source code.
    Currently ony supports snapping to edges in edit mode (single object at a time). Object mode is not supported.
    The projected bouding box check found in snap math is not used and always returns True.
    This is due to a bug that breaks the projected BB check when subsurface mod is active and edit mesh cage is enabled.
"""


class GlobalSnapContext():
    snap_context = None

    @classmethod
    def del_snap_context(cls):
        if cls.snap_context is not None:
            cls.snap_context.free()
            cls.snap_context = None

@dataclass
class SnapObjectEditMeshData():
    min: int
    max: int
    is_dirty: bool = False
    bvh_tree: BVHTree = None
    object_matrix: Matrix = None
    bm: BMesh = None
   

class SNAPMODE(IntFlag):
    FACE = 1
    EDGE = 2
    VERTEX = 4
    INCREMENT = 8


class SnapContext():

    def __init__(self, context, depsgraph, rv3d, region):
        self.depsgraph = depsgraph
        self.rv3d = rv3d
        self.region = region
        self.is_perpective = True
        self.snap_objects = {}
        self.mval = Vector((0.0, 0.0, 0.0))
        self.proj_matrix = None
        self.MVP = None

        # Todo: Add a setting in preferences to change this value
        self.radius = 30**2 * utils.ui.get_ui_scale()
        self.win_size = Vector((region.width, region.height))
        self.current_ray = None
        self.loc = None
        self.draw_snap_points = None
        self.draw_mid_point = None
        # Hard code this to edge for now
        self.snap_flags = SNAPMODE.EDGE
        self._is_snap_points_locked = False
        self._snap_increment_divisions = 1
        self._snap_factor = 0.5
        self._increment_snap_points = []
        self._locked_snap_edge_points = None
        self._locked_snap_edge_idx = None

        bpy.types.SpaceView3D.draw_handler_add(self._draw_callback_3d, (context, ), 'WINDOW', 'POST_VIEW')
        bpy.app.handlers.depsgraph_update_post.append(self._handler)

    @staticmethod
    def get(context, depsgraph, space, region):
        if not getattr(GlobalSnapContext, 'snap_context', None):
            GlobalSnapContext.snap_context = SnapContext(
                context, depsgraph, space.region_3d, region)

        return GlobalSnapContext.snap_context

    @staticmethod
    def remove():
        if getattr(GlobalSnapContext, 'snap_context', None):
            GlobalSnapContext.del_snap_context()
            return True
        return False

    def free(self):
        handler = object.__getattribute__(self, '_handler')
        bpy.app.handlers.depsgraph_update_post.remove(handler)

        # self.draw_snap_points = None
        # self.draw_mid_point = None
        if getattr(self, '_draw_handler_3d', False):
            self.draw_handler_3d = bpy.types.SpaceView3D.draw_handler_remove(
                self._draw_handler_3d, 'WINDOW')

    def increment_mode_active(self):
        return self.snap_flags & SNAPMODE.INCREMENT

    def enable_increment_mode(self):
        if not self.snap_flags & SNAPMODE.INCREMENT:
            self.snap_flags |= SNAPMODE.INCREMENT
            return True
        return False

    def disable_increment_mode(self):
        if self.snap_flags & SNAPMODE.INCREMENT:
            self.snap_flags &= ~SNAPMODE.INCREMENT
            self.draw_snap_points = None
            self._is_snap_points_locked = False
            self._locked_snap_edge_points = None
            self._locked_snap_edge_idx = None
            self.draw_mid_point = None
            return True
        return False

    def set_snap_increment_divisions(self, n: int):
        if n > 0:
            self._snap_increment_divisions = n
        else:
            raise ValueError("n value passed in must be > 0")

    def set_snap_factor(self, n: float):
        if  0.0 <= n <= 100.0:
            self._snap_factor = n*0.01
        else:
            raise ValueError("n value passed in must be >= 0.0 and <= 100.0")

    @property
    def is_snap_points_locked(self):
        return self._is_snap_points_locked

    def lock_snap_points(self):
        self._is_snap_points_locked = True

    def unlock_snap_points(self):
        self._is_snap_points_locked = False
        self._locked_snap_edge_points = None
        self._locked_snap_edge_idx = None
        self.draw_snap_points = None
        self.draw_mid_point = None


    def _handler(self, scene, depsgraph):
        updated = depsgraph.id_type_updated('MESH') or \
            depsgraph.id_type_updated('OBJECT')

        if updated:
            for update in depsgraph.updates:
                if update.id.name in self.snap_objects:
                    self.snap_objects[update.id.name].is_dirty = True


    def add_object(self, snap_object: Object):

        if snap_object.name not in self.snap_objects:
            object_data = SnapObjectEditMeshData(
                snap_object.bound_box[0], snap_object.bound_box[6])
            object_data.object_matrix = snap_object.matrix_world
            self.snap_objects[snap_object.name] = object_data

            if snap_object.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(snap_object.data)
                object_data.bm = bm
                object_data.bvh_tree = BVHTree.FromBMesh(bm, epsilon=0.001)


    def _update_snap_object(self, snap_object):
        if snap_object.name in self.snap_objects:
            snap_object_data = self.snap_objects[snap_object.name]

            snap_object_data.object_matrix = snap_object.matrix_world

            if snap_object.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(snap_object.data)
                snap_object_data.bm = bm
                snap_object_data.bvh_tree = BVHTree.FromBMesh(
                    bm, epsilon=0.001)

    def do_snap(self, mvals, object_=None):
        inside_toolbar = utils.ui.inside_toolbar(mvals)
        inside_npanel = utils.ui.inside_npanel(mvals)
        inside_gizmo = utils.ui.inside_navigation_gizmo(mvals)
        if inside_toolbar or inside_npanel or inside_gizmo:
            return None, None

        if object_ is None:
            pass
        else:
            if object_.name in self.snap_objects:

                snap_object_data = self.snap_objects[object_.name]
                if snap_object_data.is_dirty:
                    self._update_snap_object(object_)
                    snap_object_data.is_dirty = False

                return self._snap_object(self.snap_objects[object_.name], mvals)

        return None, None
    

    def _draw_callback_3d(self, context):
        if self.loc is not None:
            utils.drawing.draw_points([self.loc])
            self.loc = None

        if self.draw_snap_points is not None:
            utils.drawing.draw_points(self.draw_snap_points)

        if self.draw_mid_point is not None:
            utils.drawing.draw_point(self.draw_mid_point, size=6.0)

            # if not self.is_snap_points_locked:
            #     self.draw_snap_points = None
            #     self.draw_mid_point = None
                

    def _snap_object(self, snap_object, mvals):
        ray_origin, ray_vector = utils.raycast.get_ray(
            self.region, self.rv3d, mvals)
        mat_inv = snap_object.object_matrix.inverted_safe()
        ray_orig_local = mat_inv @ ray_origin
        ray_dir_local = mat_inv.to_3x3() @ ray_vector

        self.current_ray = [ray_orig_local, ray_dir_local]
        self.proj_matrix = self.rv3d.perspective_matrix.copy()
        self.is_perpective = self.rv3d.is_perspective

        self.MVP = self.proj_matrix @ snap_object.object_matrix

        self.mval = Vector(mvals)

        #if snap_math.snap_bound_box_check_dist(snap_object.min, snap_object.max, self.MVP, self.win_size, self.mval, self.radius, (ray_orig_local, ray_dir_local)):
        ray_co, _, index, _ = snap_object.bvh_tree.ray_cast(
            ray_orig_local, ray_dir_local)


        if self.is_snap_points_locked and self._locked_snap_edge_idx is not None:
            self.draw_mid_point = None
            self._calc_snap_edge_increments()

        nearest_loc = None
        element_index = None
        if index is not None:

            if snap_object.bm.is_valid:
                bm: BMesh = snap_object.bm
                if self.snap_flags & SNAPMODE.EDGE:
                    bm.faces.ensure_lookup_table()

                    shortest_dist = float('INF')
                    try:
                        face = bm.faces[index]
                    except IndexError:
                        return None, None

                    if face.hide == True:
                        return None, None

                    for loop in utils.mesh.bmesh_face_loop_walker(face):
                        edge = loop.edge
                        edge_index = edge.index

                        nearest_co, _ = self._cb_snap_edge(
                            edge_index)

                        if nearest_co is not None:
                            nearest_co = snap_object.object_matrix @ nearest_co
                            ray_coo = snap_object.object_matrix @ ray_co
                            dist = (nearest_co - ray_coo).length_squared

                            if dist < shortest_dist:
                                shortest_dist = dist
                                nearest_loc = nearest_co
                                element_index = edge_index

                    if element_index is not None and (self.snap_flags & SNAPMODE.EDGE and self.snap_flags & SNAPMODE.INCREMENT):
                        # if self.is_snap_points_locked and self._locked_snap_edge_idx is None:
                        #     self.draw_mid_point = None
                        #     self._calc_snap_edge_increments(element_index)
                            
                        # if self.is_snap_points_locked and self._locked_snap_edge_idx is not None:
                        #     self.draw_mid_point = None
                        #     self._calc_snap_edge_increments()

                        if not self.is_snap_points_locked or self.draw_snap_points is None:
                            self._calc_snap_edge_increments(element_index)
                            self._locked_snap_edge_idx = element_index

                        if self._snap_increment_divisions > 1:
                            shortest_dist = float('INF')
                            for point in self._increment_snap_points:
                                point_2d = location_3d_to_region_2d(
                                    self.region, self.rv3d, point)

                                dist = (point_2d - self.mval).length_squared

                                if dist < self.radius and dist < shortest_dist:
                                    shortest_dist = dist
                                    nearest_loc = point
                        else:
                            nearest_loc = self._increment_snap_points[0]

                    elif self.snap_flags & SNAPMODE.EDGE and not self.snap_flags & SNAPMODE.INCREMENT:
                        self.draw_snap_points = None

                    return element_index, nearest_loc
        else:
            return None, None

        return None, None


    def _calc_snap_edge_increments(self, index=None):
        snap_object = list(self.snap_objects.values())[0]
        va_co = None
        vb_co = None
        if index is not None:
            bm = snap_object.bm
            bm.edges.ensure_lookup_table()
            edge: BMEdge = bm.edges[index]

            va_co = edge.verts[0].co
            vb_co = edge.other_vert(edge.verts[0]).co

            self._locked_snap_edge_points = [va_co, vb_co]

        elif index is None and self._locked_snap_edge_points is not None:
            va_co = self._locked_snap_edge_points[0]
            vb_co = self._locked_snap_edge_points[1]

        self.draw_snap_points = []
        n = self._snap_increment_divisions
        self._increment_snap_points.clear()
        if n > 1:
            for i in range(n):
                percent = ((1.0 + i) / (n + 1.0))
                position = snap_object.object_matrix @ va_co.lerp(vb_co, percent)

                self._increment_snap_points.append(position)

                if n % 2 != 0 and isclose(percent, 0.5):
                    self.draw_mid_point = snap_object.object_matrix @ va_co.lerp(
                        vb_co, 0.5)
                else:
                    self.draw_snap_points.append(position)
        else:
            position = snap_object.object_matrix @ va_co.lerp(vb_co, self._snap_factor)
            self._increment_snap_points.append(position)
            self.draw_snap_points.append(position)


    def _cb_snap_edge(self, index):
        current_object = list(self.snap_objects.values())[0]
        bm = current_object.bm
        bm.edges.ensure_lookup_table()
        edge: BMEdge = bm.edges[index]
        va_co = edge.verts[0].co
        vb_co = edge.other_vert(edge.verts[0]).co

        nearest_co = self._test_projected_edge_dist(
            (va_co, vb_co), *self.current_ray)
        if nearest_co is not None:
            _, perc = intersect_point_line(nearest_co, va_co, vb_co)
            if perc < 0.0:
                return va_co, 0.0
            elif perc > 1.0:
                return vb_co, 1.0
            elif 0.0 < perc < 1.0:
                return va_co.lerp(vb_co, perc), perc

        return None, None


    def _test_projected_edge_dist(self, verts_co, ray_origin, ray_direction):
        current_object = list(self.snap_objects.values())[0]
        va_co = verts_co[0]
        vb_co = verts_co[1]

        intersects, lambda_ = snap_math.isect_ray_line_v3(
            va_co, vb_co, ray_direction, ray_origin)
        near_co = Vector()

        if not intersects:
            near_co = va_co.copy()
        else:
            if lambda_ <= 0.0:
                near_co = va_co.copy()
            elif lambda_ >= 1.0:
                near_co = vb_co.copy()
            else:
                near_co = va_co.lerp(vb_co, lambda_)

            if self._test_projected_vert_dist(near_co, self.radius):
                return near_co
        return None


    def _test_projected_vert_dist(self, co, dist_px_sq):

        win_half = self.win_size * 0.5
        mvals = self.mval - win_half
        current_object = list(self.snap_objects.values())[0]
        co = current_object.object_matrix @ co

        proj_mat = self.proj_matrix.copy()

        for i in range(4):

            proj_mat.col[i][0] *= win_half[0]
            proj_mat.col[i][1] *= win_half[1]

        pro_mat = proj_mat.to_3x3()

        row_x = pro_mat.row[0]
        row_y = pro_mat.row[1]

        co_2d = Vector((
            row_x.dot(co) + proj_mat.col[3][0],
            row_y.dot(co) + proj_mat.col[3][1]
        ))

        if self.is_perpective:
            w = (proj_mat.col[0][3] * co[0]) + (proj_mat.col[1][3] *
                                                co[1]) + (proj_mat.col[2][3] * co[2]) + proj_mat.col[3][3]
            co_2d /= w
        dist_sq = (mvals - co_2d).length

        if dist_sq < dist_px_sq:
            return True
        return False
