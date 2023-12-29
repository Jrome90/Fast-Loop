from __future__ import annotations
from typing import *
from dataclasses import dataclass
from collections import namedtuple
from enum import IntFlag
from math import fabs

import bpy
from bpy.types import Object
import bmesh
from bmesh.types import *
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

from .. import utils
from . import snap_math
from .snap_points import SnapPointsMixin
from .snapping_utils import SnapEdgeParams, cb_snap_edge, do_raycast


""" A partial adaptation of the object/mesh snapping code found in Blender's source code.
    Currently ony supports snapping to edges in edit mode (single object or multiple objects). Object mode is not supported.
    TODO: This has devolved into something more specific to Fast Loop's required functionality. 
    Correct this laziness.
"""


class GlobalSnapContext():
    snap_context = None
    @classmethod
    def del_snap_context(cls):
        if cls.snap_context is not None:
            cls.snap_context._free()
            cls.snap_context = None

@dataclass
class SnapObjectEditMeshData():
    min: int
    max: int
    bl_object: Object = None
    is_dirty: bool = False
    bvh_tree: BVHTree = None
    object_matrix: Matrix = None
    object_matrix_inv: Matrix = None
    bm: BMesh = None
    name: str = ''
   

class SNAPMODE(IntFlag):
    FACE = 1
    EDGE = 2
    VERTEX = 4
    INCREMENT = 8

@dataclass()
class Nearest_2d():
    face:BMFace = None
    vert:BMVert = None
    edge:BMEdge = None
    vert_co: Vector = None
    edge_co: Vector = None
    edge_center_co = None

@dataclass()
class Isect_Data():
    isect_co: Vector = None
    isect_normal: Vector = None
    distance:float = None
    face_index: int = None

Ray = namedtuple("Ray", "origin direction")
SnapResults = namedtuple("SnapResults", "face_index element_index nearest_point")

class SnapContext(SnapPointsMixin):

    def __init__(self, context, depsgraph, owner, rv3d=None, region=None):
        self.context = context
        self.owning_object = owner
        self.depsgraph = depsgraph
        self.rv3d = rv3d
        self.region = region
        self.is_perpective = True
        self.snap_objects: dict[str, SnapObjectEditMeshData] = {}
        self.mvals = Vector((0.0, 0.0, 0.0))
        self.mvals_win = None
        self.proj_matrix = None
        self.MVP = None
        self.ray: Ray = None

        self.points_2d = []

        self.win_size = Vector((region.width, region.height))
        self._preselect_vertex_co = None
        # Hard code this to edge for now
        self.snap_flags = SNAPMODE.EDGE
        self.nearest_2d = None
        self._isect_data: Isect_Data = Isect_Data()

        self._draw_handler_3d = bpy.types.SpaceView3D.draw_handler_add(self._draw_callback_3d, (context, ), 'WINDOW', 'POST_VIEW')
        self._draw_handler_2d = bpy.types.SpaceView3D.draw_handler_add(self._draw_callback_2d, (context, ), 'WINDOW', 'POST_PIXEL')
        bpy.app.handlers.depsgraph_update_post.append(self._handler)

        SnapPointsMixin.__init__(self)

    @staticmethod
    def get(context, depsgraph, caller_object, space, region):
        if not getattr(GlobalSnapContext, 'snap_context', None):
            GlobalSnapContext.snap_context = SnapContext(
                context, depsgraph, caller_object, space.region_3d, region)

        return GlobalSnapContext.snap_context

    @staticmethod
    def remove(caller_object):
        if getattr(GlobalSnapContext, 'snap_context', None):
            if GlobalSnapContext.snap_context.owning_object is caller_object:
                GlobalSnapContext.del_snap_context()
                return True
        return False

    def _free(self):
        handler = object.__getattribute__(self, '_handler')
        bpy.app.handlers.depsgraph_update_post.remove(handler)

        if getattr(self, '_draw_handler_3d', False):
            self.draw_handler_3d = bpy.types.SpaceView3D.draw_handler_remove(
                self._draw_handler_3d, 'WINDOW')

        if getattr(self, '_draw_handler_2d', False):
            self._draw_handler_2d = bpy.types.SpaceView3D.draw_handler_remove(
                self._draw_handler_2d, 'WINDOW')

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
            self._increment_snap_points.clear()
            return True
        return False

    def enable_vertex_sel_mode(self):
        if not self.snap_flags & SNAPMODE.VERTEX:
            self.snap_flags |= SNAPMODE.VERTEX
            return True
        return False

    def disable_vertex_sel_mode(self):
        if self.snap_flags & SNAPMODE.VERTEX:
            self.snap_flags &= ~SNAPMODE.VERTEX
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
    def use_distance(self):
        return self._use_distance
        
    @use_distance.setter
    def use_distance(self, value):
        self._use_distance = value

    def set_snap_distance(self, distance: float):
        self._snap_distance = fabs(distance)

    @property
    def auto_calc_snap_points(self):
        return self._auto_calc_snap_points
    @auto_calc_snap_points.setter
    def auto_calc_snap_points(self, value):
        self._auto_calc_snap_points = value
      

    @property
    def is_snap_points_locked(self):
        return self._is_snap_points_locked

    # def get_intersection_data(self) -> Isect_Data:
    #     return self._isect_data

    def lock_snap_points(self):
        self._is_snap_points_locked = True

    def unlock_snap_points(self):
        self._is_snap_points_locked = False
        self._locked_snap_edge_points = None
        self._locked_snap_edge_idx = None
        self.draw_snap_points = []
        self.draw_mid_point = None


    def _handler(self, scene, depsgraph):
        updated = depsgraph.id_type_updated('MESH') or \
            depsgraph.id_type_updated('OBJECT')

        if updated:
            for update in depsgraph.updates:
                if update.id.name in self.snap_objects:
                    self.snap_objects[update.id.name].is_dirty = True


    def add_object(self, bl_object: Object):

        if bl_object.name not in self.snap_objects:
            object_data = SnapObjectEditMeshData(
                bl_object.bound_box[0], bl_object.bound_box[6], bl_object, name=bl_object.data.name)
            object_data.object_matrix = bl_object.matrix_world
            object_data.object_matrix_inv = bl_object.matrix_world.inverted_safe()
            self.snap_objects[bl_object.name] = object_data
            

            if bl_object.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(bl_object.data)
                object_data.bm = bm
                object_data.bvh_tree = BVHTree.FromBMesh(bm)


    def _update_snap_object(self, snap_object_data: SnapObjectEditMeshData):
            bl_object = snap_object_data.bl_object
            snap_object_data.object_matrix = bl_object.matrix_world

            if bl_object.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(bl_object.data)
                snap_object_data.bm = bm
                snap_object_data.bvh_tree = BVHTree.FromBMesh(
                    bm)
    
    def _get_snap_object_by_name(self, name) -> SnapObjectEditMeshData:
        if name in self.snap_objects:
            return self.snap_objects[name]
        return None
    
    def do_snap_objects(self, bl_objects, mvals, mvals_win=None) -> None | Tuple :
        # inside_toolbar = utils.ui.inside_toolbar(mvals)
        # inside_npanel = utils.ui.inside_npanel(mvals)
        # inside_gizmo = utils.ui.inside_navigation_gizmo(mvals)
        # if inside_toolbar or inside_npanel or inside_gizmo:
        #     return None, None, None
        if not bl_objects:
            pass
        else:
            try:
                snap_objects = []
                for bl_object in bl_objects:

                    snap_object_data = self._get_snap_object_by_name(bl_object.name)
                    if snap_object_data is None:
                        continue

                    if self._update_internal_data_for_object(snap_object_data):
                        snap_objects.append(snap_object_data)

                if self.update_screen_data(mvals_win):
                    return self._snap_objects(snap_objects)
            # Something changed in Blender, so now we need to handle the case when the object we are referencing may no longer exist.
            except ReferenceError:
                raise

        return None

    def do_snap_object(self,bl_object: Object, mvals, mvals_win=None):
        # inside_toolbar = utils.ui.inside_toolbar(mvals)
        # inside_npanel = utils.ui.inside_npanel(mvals)
        # inside_gizmo = utils.ui.inside_navigation_gizmo(mvals)
        # if inside_toolbar or inside_npanel or inside_gizmo:
        #     return None, None, None

        if bl_object is None:
            pass
        else:
            try:
                snap_object_data = self._get_snap_object_by_name(bl_object.name)
                if snap_object_data is not None and self._update_internal_data_for_object(snap_object_data):
                    if self.update_screen_data(mvals_win):
                        snap_object = snap_object_data
                        return self._snap_object(snap_object)
            # Something changed in Blender 4.x. Now we need to handle the case when the object we are referencing may no longer exist.
            except ReferenceError:
                raise

        return None, None, None


    def update_screen_data(self, mvals_win)-> bool:
        self.region, self.win_size, self.rv3d, self.is_perpective = utils.ui.get_screen_data_for_3d_view(self.context, mvals_win)
        if not all((self.region, self.win_size, self.rv3d)):
            return False
        
        self.mvals = Vector((mvals_win[0] - self.region.x , mvals_win[1] - self.region.y)) if self.region is not None else Vector((0.0, 0.0))
        self.mvals_win = mvals_win
        self.proj_matrix = self.rv3d.perspective_matrix.copy() if self.rv3d is not None else None
        return True
    

    def _update_internal_data_for_object(self, snap_object_data: SnapObjectEditMeshData)-> bool:
        if snap_object_data.bm is None or snap_object_data.bvh_tree is None:
            #TODO Remove from snap objects
            return False

        if snap_object_data.is_dirty:
            self._update_snap_object(snap_object_data)
            snap_object_data.is_dirty = False
        return True
    

    def _draw_callback_3d(self, context):
        SnapPointsMixin.draw_callback_3d(self, context)
    

    def _draw_callback_2d(self, context):
        # def box_intersect(a, b, size_a, size_b):
        #     a_width, a_height = size_a
        #     b_width, b_height = size_b

        #     return (abs(a.x - b.x) * 2 < (a_width + b_width)) and (abs(a.y - b.y) * 2 < (a_height + b_height))
        if self.points_2d:
            utils.draw_2d.draw_points(self.points_2d)
            self.points_2d.clear()
            
        SnapPointsMixin.draw_callback_2d(self, context)
    

    def _snap_object(self, snap_object:SnapObjectEditMeshData):

        ray_origin, ray_vector = utils.raycast.get_ray(
            self.region, self.rv3d, self.mvals)
        
        # for snap_object in snap_objects:

        mat_inv = snap_object.object_matrix_inv
        self.ray = Ray(mat_inv @ ray_origin, mat_inv.to_3x3() @ ray_vector)
        self.MVP = self.proj_matrix @ snap_object.object_matrix

        isect_co = None
        face = None

        if snap_math.snap_bound_box_check_dist(snap_object.min, snap_object.max, self.MVP, self.win_size, self.mvals, self.radius, self.ray):
            ray_cast_results = do_raycast(snap_object, self.ray.origin, self.ray.direction)

            #------
            if ray_cast_results is not None and snap_object.bm.is_valid:
                return self.do_some_stuff(snap_object, face, isect_co)
            else:
                # TODO: Remove 
                self._preselect_vertex_co = None
                self.draw_snap_indicator = False
            
        return None

    def _snap_objects(self, snap_objects) -> None | Tuple:

        ray_origin, ray_vector = utils.raycast.get_ray(
            self.region, self.rv3d, self.mvals)
        
        shortest_dist = float('INF')
        closest_ray_cast_result: None | Tuple = None
        for snap_object in snap_objects:
            mat_inv = snap_object.object_matrix_inv
            ray = Ray(mat_inv @ ray_origin, mat_inv.to_3x3() @ ray_vector)
            MVP = self.proj_matrix @ snap_object.object_matrix

            if snap_math.snap_bound_box_check_dist(snap_object.min, snap_object.max, MVP, self.win_size, self.mvals, self.radius, ray):
                ray_cast_results = do_raycast(snap_object, ray.origin, ray.direction)
                
                if ray_cast_results is not None and ray_cast_results[2] < shortest_dist:
                    distance = ray_cast_results[2]
                    shortest_dist = distance
                    isect_co = ray_cast_results[0]
                    face = ray_cast_results[1]
                    closest_ray_cast_result = (snap_object, face, isect_co)
                    self.ray = Ray(mat_inv @ ray_origin, mat_inv.to_3x3() @ ray_vector)
                    self.MVP = self.proj_matrix @ snap_object.object_matrix

        if closest_ray_cast_result is not None and snap_object.bm.is_valid:
            snap_results = self.do_some_stuff(*closest_ray_cast_result)
            return None if snap_results is None else (*snap_results, closest_ray_cast_result[0].bl_object)
        else:
            # TODO: Remove
            self._preselect_vertex_co = None
            self.draw_snap_indicator = False
            
        return None

    
    #TODO: Use a better name
    # What does this function do?
    # Gets the nearest element (in this case edge) and then calls 
    # method to deal with snap points if snapping is enabled, otherwise 
    # just use the nearest location 
    def do_some_stuff(self, snap_object, face, isect_co) -> None| Tuple:

        if self.snap_flags & SNAPMODE.EDGE:
            nearest_2d: Nearest_2d = Nearest_2d()
            nearest_2d.face = face
            if self.get_nearest_element(snap_object, isect_co, face, self.snap_flags, nearest_2d):
                self.nearest_2d = nearest_2d
                nearest_point = nearest_2d.edge_co
                element_index = nearest_2d.edge.index
                   
                if self.snap_flags & SNAPMODE.INCREMENT:
                    element_index, nearest_point = self.get_nearest_snap_point(snap_object, nearest_2d)

                return SnapResults(face.index, element_index, nearest_point)

        self.nearest_2d = None
        return None

    def get_nearest_element(self, snap_object, ray_co, face, snap_elements_flag, nearest_2d):
        shortest_dist_edge = float('INF')
        ray_coo = snap_object.object_matrix @ ray_co
        for loop in utils.mesh.bmesh_face_loop_walker(face):
            nearest_co = None
            edge = loop.edge
            if snap_elements_flag & SNAPMODE.EDGE:
                edge_params = SnapEdgeParams()
                edge_params.is_perpective = self.is_perpective
                edge_params.snap_object = snap_object
                edge_params.edge_index =  edge.index
                edge_params.ray_origin = self.ray.origin
                edge_params.ray_direction = self.ray.direction
                edge_params.radius = self.radius
                edge_params.proj_matrix = self.proj_matrix.copy()
                edge_params.win_size = self.win_size
                edge_params.mval = self.mvals

                results = cb_snap_edge(edge_params)

                if results is not None:
                    nearest_co, _ = results
                    nearest_co = snap_object.object_matrix @ nearest_co
                    dist = (nearest_co - ray_coo).length_squared

                    if dist < shortest_dist_edge:
                        shortest_dist_edge = dist
                        nearest_2d.edge = edge
                        nearest_2d.edge_co = nearest_co

        if nearest_2d.edge is not None:
            shortest_dist_vert = float('INF')
            for vert in nearest_2d.edge.verts:
                nearest_co = snap_object.object_matrix @ vert.co
                dist = (nearest_co - ray_coo).length_squared

                if dist < shortest_dist_vert:
                    shortest_dist_vert = dist
                    nearest_2d.vert = vert
                    nearest_2d.vert_co = nearest_co
                
        return True if (nearest_2d.vert is not None and nearest_2d.edge is not None) else False


    def force_display_update(self, object_):
        nearest_2d = self.nearest_2d
        if nearest_2d is not None:
            snap_object_data = self._get_snap_object_by_name(object_.name)
            self._increment_snap_points, self._increment_snap_point_dist = self.calc_snap_edge_increments(snap_object_data, nearest_2d, self.region, self.rv3d)
            self.draw_snap_points = self.calculate_incremental_lines(snap_object_data, self._increment_snap_points, nearest_2d.edge, nearest_2d.face)
