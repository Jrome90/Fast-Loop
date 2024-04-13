# from typing import TYPE_CHECKING
# if TYPE_CHECKING:

from contextlib import suppress

import bpy, bmesh
from bmesh.types import BMEdge, BMLoop
from mathutils import Vector

from ...utils.common import prefs
from ...utils.ops import (get_m_button_map as btn)
from ...utils import draw_3d, draw_2d

from ..fast_loop_helpers import (Mode)

from ..edge_ring import EdgeDataFactory
from ..edge_data import EdgeData


from ..fast_loop_algorithms import ComputeEdgePostitonsSingleAlgorithm
from ..fast_loop_helpers import Mode

from ..actions.insert_loop_base import InsertAction

from ...utils.mesh import (bmesh_edge_loop_walker, get_vertex_shared_by_edges, get_face_loop_for_edge, get_face_from_index)

from ..fast_loop_common import CurrentPos


class AbsoluteInsertLoopAction(InsertAction):
    Mode = Mode.SINGLE
    edge_loop_draw_points = []
    def __init__(self, context) -> None:
        context.segments = 1
        context.edge_pos_algorithm = ComputeEdgePostitonsSingleAlgorithm()
        super().__init__(context)

    def enter(self):
        self.context.event_handler.numeric_input_begin(None, self.on_numeric_input_changed)
        self.context.event_handler.should_consume_mouse_input = False
        self.context.event_handler._numeric_value = self.context.distance_str
        self.context.use_even = True
        super().enter()

    def exit(self):
        self.context.use_even = False
        super().exit()


    @staticmethod
    def calc_dir_vec_for_face_corner(face_corner: BMLoop)-> Vector:
        return (face_corner.edge.other_vert(face_corner.vert).co - face_corner.vert.co).normalized()


    def update(self):
        current_edge: BMEdge = self.context.current_edge
        if current_edge is None or not current_edge.is_valid or self.context.current_face_index is None:
            return

        self.edge_loop_draw_points = self.compute_edge_loop_draw_points()

        # Generate the edge ring collection.
        face = get_face_from_index(self.context.active_object.bm, self.context.current_face_index)
        
        face_corner: None
        dir_vec = None
        distance = self.context.distance_from_loop
        if face is not None:
            face_corner: BMLoop = get_face_loop_for_edge(face, current_edge)
            current_edge = face_corner.edge

            dir_vec = self.calc_dir_vec_for_face_corner(face_corner)
            self.context.current_position = CurrentPos(face_corner.vert.co + (dir_vec * distance), self.context.current_position.local)

        edge_ring_data = EdgeDataFactory.create(current_edge, self.context)
        if edge_ring_data is not None:
            self.context.loop_data = edge_ring_data
            v = []
            for vert in face_corner.link_loop_prev.edge.verts:
                if vert == edge_ring_data.get_active_loop().vert:
                    v.append(vert)
            if not v:
                self.context.common_props.flipped = True
                # face_corner = get_face_loop_for_edge(face, current_edge)
                # dir_vec = self.calc_dir_vec_for_face_corner(face_corner)
                # self.context.current_position = CurrentPos(face_corner.vert.co + (dir_vec * distance), self.context.current_position.local)

                # self.context.points_3d.append(face_corner.vert.co + (dir_vec * distance))
                # self.current_edge = face_corner.edge
                # self.current_edge_index = face_corner.edge.index
                
            else:
                self.context.common_props.flipped = False

            if self.context.update_loops():
                props = self.context.get_all_props_no_snap()
                # Generate the point data used to construct the edges later using create_geometry()
                if not edge_ring_data.is_single_loop():
                    self.context.edge_data = EdgeData().populate_data(edge_ring_data, props)
                else:
                    self.context.do_inset(edge_ring_data, props)
                    self.context.is_single_edge = edge_ring_data.is_single_loop()
                return True

        return False


    def handle_input(self, bl_context, bl_event):
        handled = False
        event = bl_event

        if event.type in {'RIGHTMOUSE', 'LEFTMOUSE'}:
            if self.context.current_edge is not None and event.type in {btn('LEFTMOUSE')} and (event.value == 'CLICK'):
                if prefs().use_spacebar and event.alt:
                    return False

                if (not event.shift and not self.context.set_flow_enabled()) or (event.shift and self.context.set_flow_enabled()):
                    self.context.create_geometry(select_new_edges=False)
                    bpy.ops.ed.undo_push(message="Insert Loop")

                elif event.shift or self.context.set_flow_enabled():
                    selected_edges = self.context.create_geometry(select_new_edges=True)
                    try:
                        self.context.set_flow()
                        active_object = self.context.active_object
                        if prefs().get_edge_flow_version() == (0,8):
                            if active_object.bm.is_valid:
                                for edge in selected_edges:
                                    edge.select = False

                                active_object.bm.select_flush_mode()
                                mesh_data = active_object.data
                                bmesh.update_edit_mesh(mesh_data)

                        self.context.ensure_bmesh_(active_object)
                        bpy.ops.ed.undo_push(message="Insert Loop With Set Flow")
                        
                    except AttributeError:
                        self.context.report({'ERROR'}, 'Edge Flow addon was not found. Please install and activate it.')

                handled = True

            elif event.type == btn('RIGHTMOUSE') and event.value == 'PRESS':
                if prefs().use_spacebar and event.alt:
                    return False
                
                self.context.cancelled = True
                handled = True
      
        return handled
    
    def compute_edge_loop_draw_points(self):
        if self.context.highlighted_edge is None:
            self.edge_loop_draw_points.clear()
            return

        points = []

        world_mat = self.context.world_mat
        loop_edges  = []
        edge: BMEdge = self.context.highlighted_edge
        for i, loop_edge in enumerate(bmesh_edge_loop_walker(edge)):

            if i >= 1:
                vert = get_vertex_shared_by_edges([loop_edge, loop_edges[i-1]])
                #TODO Errors when the vert only has one edge
                if vert is not None:  
                    points.append(world_mat @ vert.co)
                
            loop_edges.append(loop_edge)

        # Add the missing points that need to be drawn
        if len(loop_edges) > 1:
            
            last_vert = get_vertex_shared_by_edges([loop_edges[0], loop_edges[-1]])
            # A loop was found
            if last_vert is not None:
                points.append(world_mat @ last_vert.co)
                points.append(world_mat @ loop_edges[0].other_vert(last_vert).co)

                connecting_vert = get_vertex_shared_by_edges([loop_edges[0], loop_edges[1]])
                if connecting_vert is not None:
                    points.append(world_mat @ connecting_vert.co)
                    points.append(world_mat @ loop_edges[1].other_vert(connecting_vert).co)
            # It's not a loop
            else:
                connecting_vert = get_vertex_shared_by_edges([loop_edges[0], loop_edges[1]])
                if connecting_vert is not None:
                    points.insert(0, world_mat @ loop_edges[0].other_vert(connecting_vert).co)
                    points.insert(0, world_mat @ connecting_vert.co)

                connecting_vert2 = get_vertex_shared_by_edges([loop_edges[-2], loop_edges[-1]])
                if connecting_vert2 is not None:
                    points.append(world_mat @ connecting_vert2.co)
                    points.append(world_mat @ loop_edges[-1].other_vert(connecting_vert2).co)
        else:
                points.clear()
                points.extend([world_mat @ loop_edges[0].verts[0].co, world_mat @ loop_edges[0].verts[1].co])

        return points
    
    def handle_modal_event(self, bl_context, modal_event, bl_event):
       ...
        

    def draw_ui(self, bl_context):
        if self.context.distance_str is not None:
            draw_2d.draw_text_on_screen(self.context.distance_str, [100, 50], 50)
    

    def draw_3d(self, bl_context):
        self.draw_highlight_edge_loop()
        self.draw_preview_loop()


    def draw_highlight_edge_loop(self):
        if self.edge_loop_draw_points:
            draw_3d.draw_lines(self.edge_loop_draw_points, line_color=(1.0, 0.749, 0.0, 0.9), line_width=2.0)


    def draw_preview_loop(self):
        color = prefs().loop_color
        line_width = prefs().line_width
        if not self.context.is_inset():
            transposed_array = list(map(list, zip(*self.context.loop_draw_points)))
            for loop in transposed_array:
                if self.context.is_loop:
                    draw_3d.draw_line_loop(loop, color, line_width, depth_test=prefs().occlude_lines)
                else:
                    # TODO find out and fix the cause of a value exception after placing loops while used selected edges is enabled.
                    with suppress(ValueError):
                        draw_3d.draw_line(loop, color, line_width, depth_test=prefs().occlude_lines)
            
        elif self.context.is_inset() and self.context.inset_preview_coords:
            for edge in self.context.inset_preview_coords:
                draw_3d.draw_line(edge, color, line_width, depth_test=prefs().occlude_lines)


    def on_numeric_input_changed(self, results):        
        if results.value is None:
            return
        self.context.distance_str = results.input_string
        self.context.distance_from_loop = results.value
        if self.context.update_loops():
            self.update()
            self.context.ensure_bmesh_(self.context.active_object)
        