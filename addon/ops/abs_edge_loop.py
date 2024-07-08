from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..props.fl_properties import AllPropsNoSnap
    from bmesh.types import BMFace, BMEdge

from contextlib import suppress

import bpy

import bmesh
from bmesh.ops import inset_individual
from bmesh.types import BMesh, BMFace, BMEdge

from .. props import addon
from .edge_ring import EdgeRing
from ..utils import ops, ui
from ..props.fl_properties import MultiLoopProps, SubProps, SnapProps, AllPropsNoSnap

from .fast_loop_common import FastLoopCommon, CurrentPos
from .fast_loop_helpers import (Mode, mode_enabled, get_options)


from .actions.abs_insert_loop import AbsoluteInsertLoopAction

from ..snapping.snapping  import SnapContext

from . fast_loop_algorithms import ComputeEdgePostitonsSingleAlgorithm

from ..keymaps.event_handler import Event_Handler, NumericInputResults
from ..keymaps.modal_keymapping import ModalOperatorKeymapCache as km_cache

from ..utils.mesh import (get_face_loop_for_edge, get_face_from_index)


class OT_Absolute_Edge_Loop(bpy.types.Operator, FastLoopCommon):
    bl_idname = 'fl.absolute_edge_loop'
    bl_label = 'Absolute Edge Loop Insert'
    bl_options = {'REGISTER'}

    invoked_by_tool: bpy.props.BoolProperty(
    name='tool invoked',
    description='Do not change. This is meant to be hidden',
    default=False,
    options={'HIDDEN', 'SKIP_SAVE'}
    )

    multi_loop_props = MultiLoopProps()
    sub_props = SubProps()
    snap_props = SnapProps()

    multi_loop_props = MultiLoopProps()
    sub_props = SubProps()
    snap_props = SnapProps()

    highlighted_edge: BMEdge = None
    inset_preview_coords = None

    undo_was_called = False
    force_offset_value = -1
    
    main_panel_hud = None

    event_handler = None
    last_numeric_input_results: NumericInputResults = None
    last_numeric_dist_value = None


    # Some code depends on these properties.
    scale = 0.0
    insert_on_selected_edges = False
    insert_verts = False

    @property
    def operator_options(self)-> addon.FL_Options:
        return get_options()

    @property
    def distance_from_loop(self):
        return self.operator_options.distance_from_loop
    
    @distance_from_loop.setter
    def distance_from_loop(self, value):
        self.operator_options.distance_from_loop = value

    @property
    def distance_str(self):
        return self.operator_options.distance_str
    
    @distance_str.setter
    def distance_str(self, value):
        self.operator_options.distance_str = value

    # TODO: Dont use props shared with the fast loop operator.
    def get_all_props_no_snap(self):
        return AllPropsNoSnap(self.common_props, self.multi_loop_props, self.sub_props)


    def draw(self, context):
        pass


    def execute(self, context):                
        return {'FINISHED'}


    def setup(self, context):
        super().setup(context)
        # Clear undo_history_keymap everytime we run setup so we can get the latest keymap from settings.
        ops.clear_undo_history_keymap()
        if ops.get_undo_keymapping() is None:
            ops.set_undo_history_keymap()

        self.edge_pos_algorithm = self.get_edge_pos_algorithm()
        self.event_handler = Event_Handler(km_cache.get_keymap('FL_OT_fast_loop'))
        self.push_action(AbsoluteInsertLoopAction(self))


    def invoke(self, context, event):
        result = super().invoke(context, event)
        if result != {'CANCELLED'}:
            if self.undo_was_called:
                self.undo_was_called = False

        return result


    def cleanup(self, context):
        super().cleanup(context)
    

    def get_edge_pos_algorithm(self):
        return ComputeEdgePostitonsSingleAlgorithm()

    
    def event_raised(self, event, value, context=None):
        ...

    
    def update(self, element_index, nearest_co=None):
        # self.force_offset_value = -1
        bm = self.ensure_bmesh_(self.active_object)
        
        bm.edges.ensure_lookup_table()
        with suppress(IndexError, AttributeError):
            edge = bm.edges[element_index]
            if edge.is_valid:
                self.highlighted_edge = edge
                face = get_face_from_index(self.active_object.bm, self.current_face_index)
                if face is not None:
                    # The current edge will be used to find the edge ring.
                    edge = get_face_loop_for_edge(face, edge).link_loop_next.edge
                    self.current_edge = edge
                    self.current_edge_index = edge.index

                    if nearest_co is not None:
                        self.current_position = CurrentPos(nearest_co, self.world_inv @ nearest_co)

                    self.current_action.update()
        

    def calculate_scale_value(self):
        return self.scale 


    # @utils.safety.decorator
    def modal(self, context, event):
        if context.mode != 'EDIT_MESH' or self.cancelled:
            return self.cancel(context)
        
        if event.type in {'TIMER'}:
            return {'RUNNING_MODAL'}
        
        mouse_coords_win = (event.mouse_x, event.mouse_y)
        area = ui.get_active_area(mouse_coords_win, context)
        mouse_coords = (event.mouse_region_x, event.mouse_region_y)
        # inside_toolbar = utils.ui.inside_toolbar(mouse_coords)
        inside_npanel = ui.inside_npanel(mouse_coords_win, area)
        inside_gizmo = ui.inside_navigation_gizmo(mouse_coords, mouse_coords_win, area)

        if inside_gizmo or inside_npanel or area is None:
            return {'PASS_THROUGH'}
        
        if mode_enabled(Mode.EDGE_SLIDE):
            return {'PASS_THROUGH'}
        
        if ops.match_event_to_keymap(event, ops.get_undo_keymapping()):
            self.undo_was_called = True
            return {'PASS_THROUGH'}

        handled = False
        modal_event = self.event_handler.handle_event(event)
        if modal_event is not None:
            if modal_event in km_cache.get_keymap('FL_OT_fast_loop').get_valid_keymap_actions(): 
                self.current_action.handle_modal_event(context, modal_event, event)
                handled = True

            # Use this to consume events for now
            elif modal_event in {"numeric_input"}:
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}

        if self.snap_context is None:
            self.snap_context: SnapContext = SnapContext.get(context, context.evaluated_depsgraph_get(), self, context.space_data, context.region,)
            
            for editable_object_data in self.selected_editable_objects.values():
                self.snap_context.add_object(editable_object_data.get_bl_object)

        if self.snap_context is not None:  
            self.update_snap_context()

            mouse_coords = (event.mouse_region_x, event.mouse_region_y)
            try:
                self.current_face_index, element_index, nearest_co = None, None, None
                snap_results = self.snap_context.do_snap_objects([obj.get_bl_object for obj in self.selected_editable_objects.values()], mouse_coords, mouse_coords_win)
                if snap_results is not None:
                    self.current_face_index, element_index, nearest_co, bl_object = snap_results
                    self.active_object = self.selected_editable_objects[bl_object.name]

                    self.current_position = CurrentPos(nearest_co, self.world_inv @ nearest_co)
                    self.update(element_index)
                   
            except (ReferenceError, KeyError):
                self.active_object = self.selected_editable_objects[context.active_object.name]
            except Exception as e:
                return self.exception_occured(context)

        if event.type in {'MOUSEMOVE'}:
            self.current_action.on_mouse_move(event)
            
        if not handled:
            if super().modal(context, event):
                handled = True
         
        if not handled and event.type in {'ESC'} and event.value == 'PRESS':
            self.cancelled = True
            handled = True

        if area is not None:
            area.tag_redraw()

        if handled:
            return {'RUNNING_MODAL'}
        else:
            return {'PASS_THROUGH'}

    
    def draw_3d(self, context):
        super().draw_3d(context)


    def update_snap_context(self):
            ...
            

    def create_geometry(self, select_new_edges=False):
        if not self.is_inset():
            num_segments = len(self.loop_data.get_loops())
            edge_verts = self.edge_data.edge_verts
            points = self.edge_data.points 
            edges = self.edge_data.edges

            selected_edges = super().create_geometry(edges, points, edge_verts, num_segments, select_new_edges=select_new_edges)
            # Clear the draw points to hide a visual bug. :(
            self.loop_draw_points.clear()

            return selected_edges
        else:
            bm = self.active_object.bm
            inset_individual(bm, faces=[self.loop_data.get_active_face()], thickness=self.distance_from_loop, use_even_offset=True)
            bm.select_flush_mode()
            mesh_data = self.active_object.data
            bmesh.update_edit_mesh(mesh_data)
            return None

    
    def is_inset(self):
        return self.loop_data.is_single_loop() if self.loop_data is not None else False


    def do_inset_for_preview(self, edge_ring_data: EdgeRing):
        face: BMFace = edge_ring_data.get_active_face()
        bm: BMesh = bmesh.new()
        verts = [bm.verts.new(vert.co) for vert in face.verts]
        copy_face: BMFace = bm.faces.new(verts)

        for edge in copy_face.edges:
            edge.tag = True

        inner_outer_edges = {edge for edge in copy_face.edges}

        copy_face.normal_update()
        ret = inset_individual(bm, faces=[copy_face], thickness=self.distance_from_loop, use_even_offset=True)

        new_edges = {edge for face in ret["faces"] for edge in face.edges}

        outer_edges = {edge for edge in new_edges if edge.tag}
        rail_edges = new_edges.difference(outer_edges)
        # rail edges + inner outer edges == preview edges we want 
        preview_edges = rail_edges.union(inner_outer_edges)

        self.inset_preview_coords = [[self.world_mat @ vert.co for vert in edge.verts] for edge in preview_edges]
        bm.free()