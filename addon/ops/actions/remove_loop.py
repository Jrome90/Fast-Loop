from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..fast_loop_common import FastLoopCommon

import bpy
from bmesh.types import BMEdge
from bmesh import ops, update_edit_mesh

from ...ops.fast_loop_actions import BaseAction
from ...utils.ops import (get_m_button_map as btn)
from ...utils import draw_3d, common
from ...utils.mesh import (bmesh_edge_loop_walker, get_vertex_shared_by_edges)

from ..fast_loop_helpers import (set_mode, Mode)


class RemoveLoopAction(BaseAction):
    Mode = Mode.REMOVE_LOOP
    remove_loop_draw_points = []

    def __init__(self, context) -> None:
        self.context: FastLoopCommon  = context

    
    def enter(self):
        set_mode(self.Mode)

    
    def exit(self):
       if self.context.dirty_mesh:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            self.context.dirty_mesh = False
    

    def update(self):
        current_edge = self.context.current_edge
        if current_edge is None or not current_edge.is_valid: #or self.context.current_face_index is None:
            return
        self.remove_loop_draw_points = self.compute_remove_loop_draw_points()

    
    def handle_input(self, bl_context, bl_event):
        handled = False
        if bl_event.type in {'RIGHTMOUSE', 'LEFTMOUSE'}:
            if self.context.current_edge is not None and bl_event.type in {btn('LEFTMOUSE')} and bl_event.value == 'CLICK':
                self.context.freeze_edge = False
                self.remove_edge_loop()
                bpy.ops.ed.undo_push(message="Remove Edge Loop")
                handled = True
                
        if not bl_event.ctrl and (bl_event.type in {'RIGHT_SHIFT', 'LEFT_SHIFT'} and bl_event.value == 'RELEASE'):
            self.context.pop_action()
            handled = True
        elif not bl_event.shift and (bl_event.type in {'RIGHT_CTRL', 'LEFT_CTRL'} and bl_event.value == 'RELEASE'):
            self.context.pop_action()
            handled = True

        return handled
    

    def on_mouse_move(self, bl_event):
        pass

    
    def draw_3d(self, bl_context):
        if self.remove_loop_draw_points:
            draw_3d.draw_lines(self.remove_loop_draw_points, line_color=(1.0, 0.0, 0.0, 0.9), depth_test=common.prefs().occlude_lines)
            self.remove_loop_draw_points.clear()


    def remove_edge_loop(self):
        bm = self.context.ensure_bmesh_(self.context.active_object)
        bm.edges.ensure_lookup_table()
        current_edge = self.context.current_edge
        dissolve_edges = list(bmesh_edge_loop_walker(current_edge))

        ops.dissolve_edges(bm, edges=dissolve_edges, use_verts=True)
        self.context.dirty_mesh = True
        mesh = self.context.active_object.data
        update_edit_mesh(mesh)

    
    def compute_remove_loop_draw_points(self):

        if self.context.current_edge is None:
            return

        points = []

        world_mat = self.context.world_mat
        loop_edges  = []
        edge: BMEdge = self.context.current_edge
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