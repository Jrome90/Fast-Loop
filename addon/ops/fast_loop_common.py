from collections import defaultdict

import bpy, bmesh
from bmesh.types import *
from mathutils import Matrix
from mathutils.geometry import intersect_point_line
from .. import utils

from enum import Enum
class Mode(Enum):
    MIRRORED = 2
    SINGLE = 4
    MULTI_LOOP = 8
    REMOVE_LOOP = 16
    SELECT_LOOP = 32
    EDGE_SLIDE = 64
  

enum_to_str = {Mode.SINGLE: 'SINGLE', Mode.MIRRORED: 'MIRRORED', Mode.MULTI_LOOP: 'MULTI_LOOP', Mode.REMOVE_LOOP: 'REMOVE_LOOP',  Mode.SELECT_LOOP: 'SELECT_LOOP', Mode.EDGE_SLIDE: 'EDGE_SLIDE'}
str_to_enum = {v: k for k, v in enum_to_str.items()}

def get_active_mode():
    return str_to_enum[utils.ops.options().mode]

def mode_enabled(mode) -> bool:
    active_mode = get_active_mode()
    if mode in enum_to_str:
        return active_mode == mode
    return False

def set_mode(mode):
    utils.ops.set_option('mode', enum_to_str[mode])


def get_options():
    return utils.ops.options()
    
def set_option(option, value):
    return utils.ops.set_option(option, value)


class FastLoopCommon():

    flipped = False
    @property
    def flipped(self):
        return utils.ops.options().flipped

    @flipped.setter
    def flipped(self, value):
        set_option('flipped', value)

    use_even = False
    @property
    def use_even(self):
        return utils.ops.options().use_even
    
    @use_even.setter
    def use_even(self, value):
        set_option('use_even', value)
    
    cancelled = False
    @property
    def cancelled(self):
        return utils.ops.options().cancel
    
    @cancelled.setter
    def cancelled(self, value):
        set_option('cancel', value)


    is_classic = False
    is_running = False
    active_object = None
    bm: BMesh = None
    dirty_mesh = False
    current_edge = None
    current_edge_index = None
    current_position = None
    # Todo: Consolidate into single attribute
    edge_start_position = None
    edge_end_position = None
    shortest_edge_len = float('INF')
    current_ring = None
    is_loop = False
    loop_draw_points = []
    remove_loop_draw_points = []
    edge_data = [] 
    ring_loops = {}

    world_mat: Matrix = None
    world_inv: Matrix = None
    snap_context = None

    offset = 0.0
    distance= 0.0
    start_mouse_pos_x = None

    @classmethod
    def poll(cls, context):
       return (context.space_data.type == 'VIEW_3D'
                and context.active_object
                and context.active_object.type == "MESH"
                and context.active_object.mode == 'EDIT'
                
              )


    def setup(self, context):
        self.active_object = context.active_object
        self.world_mat = context.object.matrix_world
        self.world_inv = context.object.matrix_world.inverted_safe()
        self.ensure_bmesh()
        utils.mesh.ensure(self.bm)

        self.is_loop = False
        self.edge_data.clear()
        self.ring_loops.clear()
        self.loop_draw_points.clear()
        
        self.bm.select_mode = {'EDGE'}
        self.bm.select_flush_mode()


    def cancel(self, context):
        self.report({'INFO'}, 'Cancelled')
        self.cleanup(context)
        if self.invoked_by_tool:
            bpy.ops.wm.tool_set_by_id(name = "builtin.select_box")
        return {'CANCELLED'}


    def cleanup(self, context):
        self.is_running = False
        self.edge_data.clear()
        self.ring_loops.clear()
        self.loop_draw_points.clear()
        
        context.workspace.status_text_set(None)
        context.area.header_text_set(None)

        self.cancelled = False

        if self.dirty_mesh:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            self.dirty_mesh = False

        if getattr(self, 'draw_handler_2d', None):
            self.draw_handler_2d = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler_2d, 'WINDOW')

        if getattr(self, 'draw_handler_3d', None):
            self.draw_handler_3d = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler_3d, 'WINDOW')

        context.area.tag_redraw()


    def create_geometry(self, context, edges, points, edge_verts_co, num_segments, set_edge_flow=False):
        def divide_chunks(l, n):
            for i in range(0, len(l), n): 
                yield set(l[i:i + n])

        def distance_sq(p1, p2):
            return (p1 - p2).length_squared

        bm: BMesh = self.ensure_bmesh()

        ret = bmesh.ops.subdivide_edges(bm, edges=edges, cuts=num_segments, use_grid_fill=False, use_only_quads=True)
        geom_inner = ret["geom_inner"]
        bm.verts.ensure_lookup_table()

        inner_verts = []
        if not set_edge_flow:
            inner_verts = [vert.index for vert in geom_inner if isinstance(vert, BMVert)]
        else:
            for elem in geom_inner:
                if isinstance(elem, BMVert):
                    inner_verts.append(elem.index)

                elif isinstance(elem, BMEdge):
                    elem.select_set(True)

        chunks = list(divide_chunks(inner_verts, num_segments))        
        edge_splits = defaultdict(list)
        moved_verts = set()
        for g, (vec_a, vec_b) in enumerate(edge_verts_co):
            
            found_at = None
            vert_set: set = set()
            for i, vert_indices in enumerate(chunks):
                vert_set = vert_indices.copy()
                for vert_index in vert_indices:
                    vert = bm.verts[vert_index]
                    if utils.math.is_point_on_line_segment(vert.co, vec_a, vec_b):
                        edge_splits[g].append(vert.index)
                        vert_set.difference_update(set([vert.index]))
                        found_at = i
                        break
                if found_at is not None:
                    break
                
            if found_at is not None:
                for vert_index in vert_set:
                    edge_splits[g].append(vert_index)
                del chunks[found_at]

            vert_indices = edge_splits[g]
            vert_indices.sort(key=lambda p :distance_sq(vec_a, bm.verts[p].co))

            if g == 0 and num_segments >= 2 and edges[g].is_boundary:
                vert_indices.reverse()

            for i, vert_index in enumerate(vert_indices):
                vert: BMVert = bm.verts[vert_index]

                points_along_edge = points[g]
                if i < len(points_along_edge) and vert.index not in moved_verts:
                    vert.co = self.world_inv @ points_along_edge[i]
                    moved_verts.add(vert.index)

        mesh = context.active_object.data
        bmesh.update_edit_mesh(mesh)


    def compute_remove_loop_draw_points(self):

        if self.current_edge is None:
            return 

        points = []

        world_mat = self.world_mat
        loop_edges  = []
        edge: BMEdge = self.current_edge
        for i, loop_edge in enumerate(utils.mesh.bmesh_edge_loop_walker(edge)):

            if i >= 1:
                vert = utils.mesh.get_vertex_shared_by_edges([loop_edge, loop_edges[i-1]])
                points.append(world_mat @ vert.co)
                
            loop_edges.append(loop_edge)

        # Add the missing points that need to be drawn
        if len(loop_edges) > 1:
            
            last_vert = utils.mesh.get_vertex_shared_by_edges([loop_edges[0], loop_edges[-1]])
            # A loop was found
            if last_vert is not None:
                points.append(world_mat @ last_vert.co)
                points.append(world_mat @ loop_edges[0].other_vert(last_vert).co)

                connecting_vert = utils.mesh.get_vertex_shared_by_edges([loop_edges[0], loop_edges[1]])
                points.append(world_mat @ connecting_vert.co)
                points.append(world_mat @ loop_edges[1].other_vert(connecting_vert).co)
            # It's not a loop
            else:
                connecting_vert = utils.mesh.get_vertex_shared_by_edges([loop_edges[0], loop_edges[1]])
                points.insert(0, world_mat @ loop_edges[0].other_vert(connecting_vert).co)
                points.insert(0, world_mat @ connecting_vert.co)

                connecting_vert2 = utils.mesh.get_vertex_shared_by_edges([loop_edges[-2], loop_edges[-1]])
                points.append(world_mat @ connecting_vert2.co)
                points.append(world_mat @ loop_edges[-1].other_vert(connecting_vert2).co)

        else:
                points.clear()
                points.extend([world_mat @ loop_edges[0].verts[0].co, world_mat @ loop_edges[0].verts[1].co])
                
        return points


    def draw_3d(self, context):
        if not (mode_enabled(Mode.REMOVE_LOOP) or mode_enabled(Mode.SELECT_LOOP) or mode_enabled(Mode.EDGE_SLIDE)) and self.current_edge is not None and self.loop_draw_points:
            
            transposed_array = list(map(list, zip(*self.loop_draw_points)))
            for loop in transposed_array:
                if self.is_loop:
                    utils.drawing.draw_line_loop(loop)
                else:
                    utils.drawing.draw_line(loop)

            if self.use_even:
                utils.drawing.draw_point(self.world_mat @ self.edge_start_position, color=(1.0, 0.0, 0.0, 0.4))

        elif mode_enabled(Mode.REMOVE_LOOP) and self.remove_loop_draw_points:
            utils.drawing.draw_line_loop(self.remove_loop_draw_points, line_color=(1.0, 0.0, 0.0, 0.4))


        self.remove_loop_draw_points.clear()


    def calc_edge_directions(self):
        edge = self.current_edge

        ring_loops = {}
        edge_ring = self.current_ring
        flipped = self.flipped

        found_loop = False
        first_ring_edge = edge_ring[0]
        self.shortest_edge_len = float('INF')

        for loop in edge_ring:
        
            vert = loop.vert
            vert_other = loop.edge.other_vert(vert)

            dir_len = (vert_other.co - vert.co).length_squared

            if dir_len < self.shortest_edge_len:
                self.shortest_edge_len = dir_len
            
            vert_coords = None
            if loop.edge.index == edge.index:
                vert_coords = [vert.co.copy(), vert_other.co.copy()]
          
            if vert_coords is not None:
                if flipped:
                    vert_coords.reverse()
                
                self.edge_start_position = vert_coords[0]
                self.edge_end_position = vert_coords[1]

                _, percent = intersect_point_line(self.current_position, vert_coords[0], vert_coords[1])

                if self.is_classic or not self.insert_at_midpoint:
                    self.offset = percent
                else:
                    self.offset = 0.5

            ring_loops[loop] = None

            if (loop.link_loop_radial_next.link_loop_next.link_loop_next.index == first_ring_edge.index) and not loop.edge.is_boundary:
                found_loop = True
            else:
                found_loop = False

        self.distance = (self.current_position - self.edge_start_position).length
        self.shortest_edge_len = self.shortest_edge_len ** 0.5
        self.is_loop = found_loop
        return ring_loops

    
    def select_edge_loop(self, context):
        bpy.ops.mesh.select_all(action='DESELECT')

        bm = self.ensure_bmesh()
        bm.edges.ensure_lookup_table()
        current_edge = bm.edges[self.current_edge_index]
        for edge in utils.mesh.bmesh_edge_loop_walker(current_edge):
            edge.select_set(True)

        mesh = context.active_object.data
        bmesh.update_edit_mesh(mesh)

    
    def remove_edge_loop(self, context):

        bm = self.ensure_bmesh()
        bm.edges.ensure_lookup_table()
        current_edge = bm.edges[self.current_edge_index]
        dissolve_edges = list(utils.mesh.bmesh_edge_loop_walker(current_edge))

        bmesh.ops.dissolve_edges(bm, edges=dissolve_edges, use_verts=True)
        self.dirty_mesh = True
        mesh = context.active_object.data
        bmesh.update_edit_mesh(mesh)
        
    @staticmethod
    def set_flow():
        prefs = utils.common.prefs()
        tension = prefs.tension
        iterations = prefs.iterations
        min_angle = prefs.min_angle

        bpy.ops.mesh.set_edge_flow('INVOKE_DEFAULT', tension=tension, iterations=iterations, min_angle=min_angle)
        bpy.ops.mesh.select_all(action='DESELECT')
   

    def ensure_bmesh(self):
        if self.bm is None or not self.bm.is_valid:
            bpy.context.active_object.update_from_editmode()
            mesh = bpy.context.active_object.data
            
            self.bm: bmesh = bmesh.from_edit_mesh(mesh)

        return self.bm
        
