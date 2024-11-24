from __future__ import annotations
from traceback import print_exc
from collections import namedtuple
from typing import List, Set, TYPE_CHECKING
if TYPE_CHECKING:
    from bmesh.types import BMEdge

import bpy, bmesh
from bpy.types import Object

from .. utils import common, draw_3d, mesh, math, ops
from .. props import addon
from ..props.fl_properties import CommonProps
from .. snapping.snapping import SnapContext

from . fast_loop_helpers import (get_options, get_props, set_prop)
from .fast_loop_actions import Actions
from .multi_object_edit import MultiObjectEditing

from .edge_ring import LoopCollection
from .edge_data import EdgeData
     
CurrentPos = namedtuple('CurrentPos','world local')
class FastLoopCommon(Actions, MultiObjectEditing):
    common_props: CommonProps = CommonProps()
#region -Properties
    @property
    def fast_loop_options(self)-> addon.FL_Options:
        return get_options()

    @property
    def is_running(self):
        return get_props().is_running

    @is_running.setter
    def is_running(self, value):
        set_prop('is_running', value)

    @property
    def flipped(self):
        return self.fast_loop_options.flipped

    @flipped.setter
    def flipped(self, value):
        self.fast_loop_options.flipped = value

    @property
    def use_even(self):
        return self.fast_loop_options.use_even
    
    @use_even.setter
    def use_even(self, value):
        self.fast_loop_options.use_even = value
    
    @property
    def cancelled(self):
        return self.fast_loop_options.cancel
    
    @cancelled.setter
    def cancelled(self, value):
       self.fast_loop_options.cancel = value

#endregion
    edge_pos_algorithm = None

    dirty_mesh = False
    current_edge = None
    current_face_index = None
    current_face_index = None
    current_edge_index = None

    current_position = None 
    
    loop_data: LoopCollection  = None
    edge_data: EdgeData = None

    is_loop = False
    is_single_edge = False
    is_single_edge = False
    loop_draw_points = []

    is_snapping = False # Used to be True if actively snapping to an element before 4.0 
    snap_position = None
    snap_context = None

    area_invoked = None

    # Debug 
    points_3d: List = []
    points_3d_colors: List = []

    def add_debug_point(self, point, color=(0.0, 1.0, 0.0, 1.0)):
        self.points_3d.append(point)
        self.points_3d_colors.append(color)


    @classmethod
    def poll(cls, context):
       return (context.space_data.type == 'VIEW_3D'
                and context.active_object
                and context.active_object.type == "MESH"
                and context.active_object.mode == 'EDIT'
              )

    
    def event_raised(self, event, value, context=None):
        pass

    
    def setup(self, context):
        # For blender 4.0
        context.tool_settings.snap_elements_tool = 'DEFAULT'

        addon.FL_Options.register_listener(self, self.event_raised)

        self.add_selected_editable_objects(context)
        #TODO Sometimes the index is out of range. Need to find out why
        if not list(self.selected_editable_objects.values()):
            self.report({'ERROR'}, "Something went wrong. Toggle edit mode, make sure you have at least one object selected, and try again")
            ops.set_fl_prop('is_running', False)
            return self.cancel(context)
        
        self.active_object = list(self.selected_editable_objects.values())[0]
        self.ensure_bmesh_(self.active_object)
        mesh.ensure(self.active_object.bm)

        self.is_loop = False
        self.loop_draw_points.clear()
        
        self.active_object.bm.select_mode = {'EDGE'}
        self.active_object.bm.select_flush_mode()


    def invoke(self, context, event):
        self.setup(context)
        self.area_invoked = context.area
        self.draw_handler_3d = bpy.types.SpaceView3D.draw_handler_add(self.draw_3d, (context, ), 'WINDOW', 'POST_VIEW')
        self.draw_handler_2d = bpy.types.SpaceView3D.draw_handler_add(self.draw_2d, (context, ), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


    def cancel(self, context):
        self.report({'INFO'}, 'Cancelled')
        self.cleanup(context)
        if self.invoked_by_tool:
            if context.area is not None:
                bpy.ops.wm.tool_set_by_id(name = "builtin.select_box")
        return {'CANCELLED'}


    def cleanup(self, context):
        self.points_3d_colors.clear()
        self.points_3d.clear()
        self.selected_editable_objects.clear()
        self.loop_draw_points.clear()
        self.cancelled = False

        if self.dirty_mesh:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            self.dirty_mesh = False

        if getattr(self, 'draw_handler_2d', None):
            self.draw_handler_2d = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler_2d, 'WINDOW')

        if getattr(self, 'draw_handler_3d', None):
            self.draw_handler_3d = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler_3d, 'WINDOW')
        
        SnapContext.remove(self)

        # To prevent an error when the area is None. It does happen :/
        if context.area is not None:
            context.area.tag_redraw()


    def draw_3d(self, context):
        self.current_action.draw_3d(context)
        # Debug points
        if self.points_3d and not self.points_3d_colors:
            draw_3d.draw_points(self.points_3d, size=5)
        self.points_3d.clear()
        # elif self.points_3d and self.points_3d_colors:
        #     draw_3d.draw_debug_points(self.points_3d, self.points_3d_colors, size=5.0)
            
    
    def draw_2d(self, context):
        self.current_action.draw_ui(context)
    

    def modal(self, context, event):
        handled = self.current_action.handle_input(context, event)
        return handled

    
    def create_geometry(self, edges, points, edge_verts, num_segments, select_new_edges=False)-> None | Set[BMEdge]:
        bm = self.ensure_bmesh_(self.active_object)

        all_verts = set()
        split_verts_start = []
        split_verts_end = []
        prev_cut_edge_verts = []
        selected_edges = set()
        for i, (edge, pos, (vert_a, vert_b)) in enumerate(zip(edges, points, edge_verts)):
            
            all_verts.add(vert_a)
            all_verts.add(vert_b)
            #TODO: Investigate ReferenceError: BMesh data of type BMEdge has been removed can happen with mirror mod when undoing
            try:
                if i == 0 and num_segments >= 2 and edge.is_boundary:
                    pos.reverse()
            except ReferenceError:
               return self.exception_occured(bpy.context)

            new_verts = []
        
            for p in pos:
                percent = math.inv_lerp(self.world_mat @ vert_a.co, self.world_mat @ vert_b.co, p)
                try:
                    _, new_vert = bmesh.utils.edge_split(edge, vert_a, percent)
                    new_verts.append(new_vert)
                    vert_a = new_vert
                except ValueError:
                   pass

            if prev_cut_edge_verts:
                for vert_a, vert_b in zip(new_verts, prev_cut_edge_verts):
                    face = mesh.get_face_with_verts([vert_a, vert_b])
                    
                    if face is not None:
                        bmesh.utils.face_split(face, vert_a, vert_b)
                        if select_new_edges:
                            e = bm.edges.get([vert_a, vert_b])
                            if e is not None:
                                e.select = True
                                selected_edges.add(e)
            prev_cut_edge_verts = new_verts.copy()

            if i == 0 and num_segments >= 2 and edge.is_boundary:
                prev_cut_edge_verts.reverse()

            if self.is_loop:
                if i == 0:
                    split_verts_start = prev_cut_edge_verts.copy()
                elif i == len(edges)-1:
                    split_verts_end = prev_cut_edge_verts.copy()
            
            all_verts.update(prev_cut_edge_verts)

        if self.is_loop:
            for vert_a, vert_b in zip(split_verts_start, split_verts_end):
                face = mesh.get_face_with_verts([vert_a, vert_b])
                if face is not None:
                    bmesh.utils.face_split(face, vert_a, vert_b)
                    if select_new_edges:
                        e = bm.edges.get([vert_a, vert_b])
                        if e is not None:
                            e.select = True
                            selected_edges.add(e)

        if bpy.context.tool_settings.use_mesh_automerge:
            threshold = bpy.context.tool_settings.double_threshold
            bmesh.ops.remove_doubles(bm, verts=list(all_verts), dist=threshold)

        bm.select_flush_mode()
        mesh_data = self.active_object.data
        bmesh.update_edit_mesh(mesh_data)

        return selected_edges if selected_edges else None


    def update_loops(self):
        if not self.active_object.bm.is_valid or self.loop_data is None:
            return False
        self.is_loop = self.loop_data.get_is_loop()
        return True


    def exception_occured(self, context):
        self.report({'ERROR'}, "Something went wrong. See console for more info.")
        print_exc()
        return self.cancel(context)
    

    @staticmethod
    def set_flow_enabled():
        return common.prefs().set_edge_flow_enabled


    @staticmethod
    def set_flow():
        prefs = common.prefs()
        tension = prefs.tension
        iterations = prefs.iterations
        min_angle = prefs.min_angle

        bpy.ops.mesh.set_edge_flow('INVOKE_DEFAULT', tension=tension, iterations=iterations, min_angle=min_angle)
   
   
    @staticmethod
    def ensure_bmesh_(edit_object_data):
        obj: Object = edit_object_data.get_bl_object

        bm = edit_object_data.bm
        if bm is None or not bm.is_valid and (obj is not None):
            obj.update_from_editmode()
            mesh = obj.data
            edit_object_data.bm = bmesh.from_edit_mesh(mesh)
        return edit_object_data.bm