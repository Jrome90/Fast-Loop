from itertools import tee
from math import floor
from statistics import mode
from typing import *
from collections import defaultdict

import bpy, bmesh
from bmesh.types import *
from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Vector, Matrix, kdtree

from ...signalslot.signalslot import Slot

from ..props import addon
from ..import utils
from ..ui.widgets import BL_UI_SliderMulti

from .edge_slide import (EdgeVertexSlideData as evsd, 
                            EdgeSlideOperator as eso)


class EdgeRingData():
    """All associated data with a single edge ring. 
    Including the new edge loops created on the edge ring.

    Attributes:
        loop: The loop for this edge.
    """
    def __init__(self, edges, edge_vert_cos, loops):
        self.edges = edges
        self.edge_vert_cos = edge_vert_cos
        self.loops = loops

        self.new_edge_loop_verts = []
        self.new_edge_loop_edges = []
        self.new_edge_loop_loops = []

        #Used when using gaps. Created immediately after geometry
        self.vert_index_to_edge_cos = {}
        self.vert_index_to_co_lookup = {}
        self.vertices_on_boundary_edge = set()

        #Gap Data
        self.vert_index_to_dir_vec_lookup:dict[int, tuple[Vector]] = {}
        self.gap_loop_vert_pairs = {}
  
    
    def init_new_geom_data(self, bm, vertices, vert_index_to_edge_cos, vertices_on_boundary_edge):
        self.new_edge_loop_verts = list(map(list, zip(*vertices)))
        self.new_edge_loop_verts.reverse()
        
        for edge_loop in self.new_edge_loop_verts:
            edge_loop_edges = []
            for i in range(len(edge_loop)):
                bm_vert = bm.verts[edge_loop[i]]
                next_vert_index = edge_loop[(i + 1) % len(edge_loop)]
                bm_next_vert = bm.verts[next_vert_index]
                bm_edge = utils.mesh.get_shared_edge_for_verts(bm_vert, bm_next_vert)
                if bm_edge is not None:
                    edge_loop_edges.append(bm_edge)
                    break
                # self.vert_index_to_co_lookup[bm_vert.index] = bm_vert.co.copy()
        
            self.new_edge_loop_edges.append(edge_loop_edges)

        # for edge_loop_edges in self.new_edge_loop_edges:
            utils.mesh.bmesh_loop_index_update(bm)
            self.new_edge_loop_loops.append([loop for loop in utils.mesh.bmesh_edge_loop_walker(edge_loop_edges[0], selected_edges_only=True , yield_loop=True) if loop is not None])
            # for loop in utils.mesh.bmesh_edge_loop_walker(edge_loop_edges[0]):
            #     print(loop.index if loop is not None else None)

        self.vert_index_to_edge_cos = vert_index_to_edge_cos
        self.vertices_on_boundary_edge = vertices_on_boundary_edge
    
    def init_gap_data(self, loop_vert_pairs, vert_index_to_dir_vec_lookup):
        self.gap_loop_vert_pairs = loop_vert_pairs
        self.vert_index_to_dir_vec_lookup = vert_index_to_dir_vec_lookup
        # self.gap_loops_a = gap_loops
       
    
    def update_loops(self):
        self.new_edge_loop_loops.clear()
        for edge_loop_edges in self.new_edge_loop_edges:
            self.new_edge_loop_loops.append([loop for loop in utils.mesh.bmesh_edge_loop_walker(edge_loop_edges[0], selected_edges_only=True, yield_loop=True) if loop is not None])


def get_options():
    return utils.ops.ls_options()
    
def set_option(option, value):
    return utils.ops.set_ls_option(option, value)


class OT_LoopSlice(bpy.types.Operator):
    bl_idname = 'fl.loop_slice'
    bl_label = 'loop_slice operator'
    bl_options = {'REGISTER'}

    active_object = None
    # Unmodifed bmesh data used to initialize
    initial_bm = None
    bm: BMesh = None
    selected_edge_set = None
    from_ui = True
    dirty_mesh = False
    current_edge = None
    current_face_index = None
    current_edge_index = None
    current_position = None

    edge_start_position = None
    edge_end_position = None
    shortest_edge_len = float('INF')
    current_ring = []
    edge_rings: List[EdgeRingData] = []

    world_mat: Matrix = None
    world_inv: Matrix = None

    start_mouse_pos_x = None

    slider_widget: BL_UI_SliderMulti = None

    # Debug 
    points_3d = []

    @property
    def loop_slice_props(self)-> addon.LoopSlice_Options:
        return get_options()

    active_thumb_index = 0
    @property
    def active_thumb_index(self):
        return self.loop_slice_props.active_index
    
    @active_thumb_index.setter
    def active_thumb_index(self, index):
        self.loop_slice_props.active_index = index

    active_thumb_position = 0.0
    @property
    def active_thumb_position(self):
        return self.loop_slice_props.active_position
    
    @active_thumb_position.setter
    def active_thumb_position(self, value):
        self.loop_slice_props.active_position = value * 100

    use_split_loops = False
    @property
    def use_split_loops(self):
        return self.loop_slice_props.use_split
    
    @use_split_loops.setter
    def use_split_loops(self, value):
        set_option('use_split', value)
    
    cap_sections = False
    @property
    def cap_sections(self):
        return get_options().cap_sections
    
    @cap_sections.setter
    def cap_sections(self, value):
        set_option('cap_sections', value)


    gap_distance = 0.0
    @property
    def gap_distance(self):
        return self.loop_slice_props.gap_distance
    
    @gap_distance.setter
    def gap_distance(self, value):
        set_option('gap_distance', value)

    edit_mode = 0
    @property
    def edit_mode(self):
        return self.loop_slice_props.edit_mode
    
    @edit_mode.setter
    def edit_mode(self, value):
        set_option('edit_mode', value)

    
    mode = 0
    @property
    def mode(self):
        return self.loop_slice_props.mode
    
    @mode.setter
    def mode(self, value):
        set_option('mode', value)


    _positions = [0.1, 0.9]
    @property
    def positions(self):
        return OT_LoopSlice._positions
    
    @positions.setter
    def positions(self, value):
        OT_LoopSlice._positions = value

    
    slice_count = 0
    @property
    def slice_count(self):
        return len(OT_LoopSlice._positions)
        # return get_options().slice_count
    
    # @slice_count.setter
    # def slice_count(self, value):
    #     self.slice_count = value
        # set_option('slice_count', value)

    def draw(self, context):
        pass

    def execute(self, context):
        self.init_edge_ring_data()

        for edge_ring in self.edge_rings:
            self.create_geometry(context, edge_ring, self.slice_count)

        utils.mesh.ensure(self.bm)

        if self.use_split_loops:
            self.split_loops()
        
        self.restore_vert_positions(context)

        context = bpy.context
        mesh = context.active_object.data
        bmesh.update_edit_mesh(mesh)

        return self.finished(context)


    @classmethod
    def init_bmesh_setup(cls, context):
        context.active_object.update_from_editmode()
        mesh = context.active_object.data
        cls.initial_bm = bmesh.new()
        cls.initial_bm.from_mesh(mesh)

    def setup_slider_widget(self, context):
        max_thumb_count = self.slice_count
        width = utils.ui.get_slider_width()
        x_pos, y_pos = utils.ui.get_slider_position()
        self.slider_widget = BL_UI_SliderMulti(context, x_pos, y_pos, width, 30, text_format="{:0." + str(2) + "f}%")
        self.slider_widget.thumb_color= (0.619, 1, 0.733, 0.8)
        self.slider_widget.hover_color = (1, 0.792, 0.058, 1.0)
        self.slider_widget.select_color = (1, 0.956, 0.058, 1.0)
        self.slider_widget.min = 0.0
        self.slider_widget.max = 100.0
        # self.slider_widget.set_value(50.0)
        self.slider_widget.decimals = 2
        self.slider_widget.show_min_max = True
        self.slider_widget.text_size = 10
        # self.slider_widget.set_on_thumb_add_callback(self.on_slider_thumb_add)
        # self.slider_widget.set_on_thumb_remove_callback(self.on_slider_thumb_remove)
        # self.slider_widget.change_mode(0)
        self.slider_widget.on_click.connect(Slot(self.on_slider_click))
        self.slider_widget.on_thumb_click.connect(Slot(self.on_thumb_click))
        self.slider_widget.on_thumb_moved.connect(Slot(self.on_thumb_move))
    
    def on_slider_click(self, **kwargs):
            context = kwargs["context"]
            value = kwargs["value"]
            # print(f"Clicked on the slider at: {value}")
            if self.edit_mode == 'ADD':
                thumb_index = self.on_slider_thumb_add(context, value)
                self.slider_widget.set_slider_pos(self.positions[:])
                self.slider_widget.set_active_thumb(thumb_index)
                self.active_thumb_position = self.positions[thumb_index]
                self.active_thumb_index = thumb_index

    def on_thumb_click(self, **kwargs):
        context = kwargs["context"]
        index = kwargs["index"]
        value = kwargs["value"]

        self.active_thumb_index = index
        self.active_thumb_position = value
        # print(f"Clicked on the slider thumb {index} at: {value}")

        if self.edit_mode == 'REMOVE':
            self.on_slider_thumb_remove(context, index)
            self.slider_widget.set_slider_pos(self.positions[:])
        

    def on_thumb_move(self, **kwargs):
        context = kwargs["context"]
        index = kwargs["index"]
        value = kwargs["value"]
        self.active_thumb_index = index
        self.active_thumb_position = value[index]
        self.on_slider_value_change(context, value)
        if self.mode == 'SYMMETRY':
            self.slider_widget.set_slider_pos(self.positions[:])


    def on_mode_changed(self, **kwargs):
        mode = kwargs["mode"]
        # print(f"Mode changed to {mode}")

        if mode == "SYMMETRY":
            self.symmetrize()
            self.slider_widget.set_slider_pos(self.positions[:])
        elif mode == "UNIFORM":
            self.make_uniform()
            self.slider_widget.set_slider_pos(self.positions[:])

        self.active_thumb_position = self.positions[self.active_thumb_index]


    def setup(self, context):
        self.setup_slider_widget(context)
        self.active_object = context.active_object
        self.world_mat = context.object.matrix_world
        self.world_inv = context.object.matrix_world.inverted_safe()

        self.loop_slice_props.on_mode_changed.connect(Slot(self.on_mode_changed))

        #self.init_ordered_percents() # Do this one time., Used for initial syncing with slider
        # if not self.positions:
        #     self.positions = [0.1, 0.9]
        #     self.current_thumb_index = 0
        self.slider_widget.set_slider_pos(self.positions[:])
        self.slider_widget.set_active_thumb(0)
        self.active_thumb_index = 0
        self.active_thumb_position = self.positions[0]
        # self.ordered_perc_vals = {index: pos for index, pos in enumerate(self.positions)}

        self.ensure_bmesh()
        self.bm.select_mode = {'EDGE'}
        self.bm.select_flush_mode()

        self.init_edge_ring_data()
        
        for edge_ring in self.edge_rings:
            self.create_geometry(context, edge_ring, self.slice_count)

        utils.mesh.ensure(self.bm)

        if self.use_split_loops:
            self.split_loops()

        self.restore_vert_positions(context)

        context = bpy.context
        mesh = context.active_object.data
        bmesh.update_edit_mesh(mesh)

        # self.set_flow()

    def init_edge_ring_data(self):
        self.edge_rings.clear()

        if self.selected_edge_set is None:
            # select_history = self.bm.select_history
            # if not len(select_history) > 2:
            self.selected_edge_set = {edge.index for edge in self.bm.edges if edge.select}
            # else:
            #     self.selected_edge_set = {edge.index for edge in select_history}

        edges_set = self.selected_edge_set.copy()
        #Loop until edges set is empty
        test_condition = True
        while test_condition:
            edge = None
            for first in edges_set:  
                edge = first  
                break

            bm_edge = self.bm.edges[edge]
            loops = []
            edges = []
            edge_vert_cos = {}
            prev_loop = None
            for loop in utils.mesh.bmesh_edge_ring_walker_sel_only(bm_edge, sentinel=-1):

                if prev_loop is not None and loop is None or (loop == -1 and len(edges) > 0):
                    if len(edges) > 0:
                        self.edge_rings.append(EdgeRingData(edges.copy(), edge_vert_cos.copy(), loops.copy()))
                        prev_loop = loop

                        loops.clear()
                        edges.clear()
                        edge_vert_cos.clear()
                        continue

                elif loop == -1 or len(edges_set) == 0:
                    break
                    
                if loop is not None and loop.edge.index in edges_set:
                    loops.append(loop)
                    edges.append(loop.edge)
                    loop.edge.select = False
                    edge_vert_cos[loop.edge.index]= (loop.vert.co.copy(), loop.edge.other_vert(loop.vert).co.copy())
                    edges_set.discard(loop.edge.index)
                    
                prev_loop = loop

            test_condition = len(edges_set) > 0


    def invoke(self, context, event):
        self.init_bmesh_setup(context)
        self.setup(context)
        addon.LoopSlice_Options.register_listener(self, self.on_loop_slice_prop_changed)
        self.draw_handler_3d = bpy.types.SpaceView3D.draw_handler_add(self.draw_3d, (context, ), 'WINDOW', 'POST_VIEW')
        self.draw_handler_2d = bpy.types.SpaceView3D.draw_handler_add(self.draw_2d, (context, ), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    
    def cancel(self, context):
        self.report({'INFO'}, 'Cancelled')
        self.revert_bmesh(context)
        self.cleanup(context)
        context.area.tag_redraw()

        return {'CANCELLED'}

    
    def finished(self, context):
        self.report({'INFO'}, 'Finished')
        self.cleanup(context)
        context.area.tag_redraw()

        return {'FINISHED'}
    
    def cleanup(self, context):
        self.selected_edge_set = None
        self.points_3d.clear()

        if getattr(self, 'draw_handler_2d', None):
            self.draw_handler_2d = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler_2d, 'WINDOW')

        if getattr(self, 'draw_handler_3d', None):
            self.draw_handler_3d = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler_3d, 'WINDOW')
        
        addon.LoopSlice_Options.unregister_listener(self)

        self.loop_slice_props.on_mode_changed.disconnect(self.on_mode_changed)

        
    def on_loop_slice_prop_changed(self, event, value, context=None):
        # print(f"Prop Changed: {event}; Value: {value}")

        if event == "use_split":
            self.split_loops(update=True)            
        elif event == "gap_distance":
            self.split_loops(update=True)
        elif event == "cap_sections":
            self.split_loops(update=True)
        elif event == "slice_count":
            self.init_ordered_percents()
            self.split_loops(update=True)
            # self.revert_bmesh(bpy.context)
            # utils.mesh.ensure(self.bm)
            # self.init_edge_ring_data()
        

            # for edge_ring in self.edge_rings:
            #     self.create_geometry(context, edge_ring, self.slice_count)

            # utils.mesh.ensure(self.bm)

            # if self.use_split_loops:
            #     self.split_loops()

            # self.restore_vert_positions(context)

            # context = bpy.context
            # mesh = context.active_object.data
            # bmesh.update_edit_mesh(mesh)
            
            # self.set_flow()

   
    def on_slider_value_change(self, context, thumb_values):
        if self.mode == 'SYMMETRY':
            thumb_index = self.active_thumb_index
            other_thumb_index = (-(thumb_index + 1)) % self.slice_count
            if thumb_index != other_thumb_index:
                thumb_values[other_thumb_index] = 1 - thumb_values[thumb_index] 

        # for thumb_index, value in enumerate(thumb_values):
        #         self.ordered_perc_vals[thumb_index] = value

        self.positions = thumb_values
        self.ensure_bmesh()
        self.update_vert_positions(context, None, None)

        mesh = context.active_object.data
        bmesh.update_edit_mesh(mesh)    


    def on_slider_thumb_add(self, context, value):
        self.revert_bmesh(context)

        self.positions.append(value)
        if self.mode == 'SYMMETRY':
            self.positions.append(1 - value)
        
        self.positions.sort()
        thumb_index = self.positions.index(value)
        # self.ordered_perc_vals = {index: pos for index, pos in enumerate(self.positions)}

        # for i, value in enumerate(thumb_values):
        #     self.ordered_perc_vals[-(i+1)] = value

        utils.mesh.ensure(self.bm)
        self.init_edge_ring_data()
       
        for edge_ring in self.edge_rings:
            self.create_geometry(context, edge_ring, self.slice_count)

            utils.mesh.ensure(self.bm, update_loops=True, loops=[loop for loops in edge_ring.new_edge_loop_loops for loop in loops])

        # self.reorder_index_to_perc_lookup()

        if self.use_split_loops:
            self.split_loops()

        self.restore_vert_positions(context)

        mesh = context.active_object.data
        bmesh.update_edit_mesh(mesh)

        return thumb_index


    def on_slider_thumb_remove(self, context, index):
        self.revert_bmesh(context)
        del self.positions[index]

        if self.slice_count >= 3 and self.mode == 'SYMMETRY':
            del self.positions[-(index + 1) % self.slice_count]

        
        # self.ordered_perc_vals = {index: pos for index, pos in enumerate(self.positions)}

        # for thumb_index in thumb_indices:
        #     if thumb_index in self.ordered_perc_vals:
        #         del self.ordered_perc_vals[thumb_index]
        if self.slice_count != 0:
            utils.mesh.ensure(self.bm)
            self.init_edge_ring_data()
            for edge_ring in self.edge_rings:
                self.create_geometry(context, edge_ring, self.slice_count)

            utils.mesh.ensure(self.bm)

            # self.reorder_index_to_perc_lookup()

            if self.use_split_loops:
                self.split_loops()
        
            self.restore_vert_positions(context)

            mesh = context.active_object.data
            bmesh.update_edit_mesh(mesh)

    
    def symmetrize(self):
        for thumb_index in range(floor(self.slice_count/2)):
            other_thumb_index = (-(thumb_index + 1)) % self.slice_count
            if thumb_index != other_thumb_index:
                self.positions[other_thumb_index] = 1 - self.positions[thumb_index]

        self.positions.sort()

        context = bpy.context
        self.update_vert_positions(context, None, None)
        mesh = context.active_object.data
        bmesh.update_edit_mesh(mesh)    

    
    def make_uniform(self):
        for thumb_index in range(self.slice_count):
            percent = (1.0 + thumb_index) / ( (self.slice_count) + 1.0)
            self.positions[thumb_index] = percent

        self.positions.sort()

        context = bpy.context
        self.update_vert_positions(context, None, None)
        mesh = context.active_object.data
        bmesh.update_edit_mesh(mesh)    

    # def reorder_index_to_perc_lookup(self):
    #     sorted_dict = {key:value for key, value in enumerate(sorted(self.ordered_perc_vals.values()))}
    #     self.ordered_perc_vals = sorted_dict
    

    def revert_bmesh(self, context):
        # Restore the initial state of the mesh data
        mesh = context.active_object.data
        bpy.ops.object.mode_set(mode='OBJECT')
        self.initial_bm.to_mesh(mesh)
        bpy.ops.object.mode_set(mode='EDIT')

        self.bm = bmesh.from_edit_mesh(mesh)
        

    def modal(self, context, event):
        handled = False

        if event.type == 'ESC':
            return self.cancel(context)
        elif event.type =='SPACE':
            return self.finished(context)
        
        context.area.tag_redraw()
        # print(f"Event Type: {event.type}  Event Value: {event.value} is repeate: {event.is_repeat}")
        if self.slider_widget.handle_event(event):
            handled = True

        if event.type in {'A', 'M', 'R', 'X'}:
            
            if event.type == 'M':
                self.edit_mode = "MOVE"
                self.report({'INFO'}, 'Move')

            if event.type == 'A':
                self.edit_mode = "ADD"
                self.report({'INFO'}, 'Add')
        
            if event.type == 'X':
                self.edit_mode = "REMOVE"
                self.report({'INFO'}, 'Remove')

            handled = True

        if handled:
            return {'RUNNING_MODAL'}
        else:
            return {'PASS_THROUGH'}
    

    def draw_3d(self, context):
        if self.points_3d:
            utils.draw_3d.draw_points(self.points_3d)
        self.points_3d.clear()

    
    def draw_2d(self, context):
        if self.slider_widget is not None:
            self.slider_widget.draw()

    
    def create_geometry(self, context, edge_ring, slice_count):
        def divide_chunks(l, n):
            for i in range(0, len(l), n): 
                yield set(l[i:i + n])

        def distance_sq(p1, p2):
            return (p1 - p2).length_squared

        def add_edge_data(vert_index):
            vert_index_to_edge_cos[vert_index] = (vec_a, vec_b)
            if edges[g].is_boundary:
                vertices_on_boundary_edge.add(vert_index)

        # bpy.ops.mesh.select_all(action='DESELECT')
        bm: BMesh = self.ensure_bmesh()
        edges = edge_ring.edges
        ret = bmesh.ops.subdivide_edges(bm, edges=edges, cuts=slice_count, use_grid_fill=False)
        geom_inner = ret["geom_inner"]
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        inner_verts = []
        inner_edges = []
        new_verts_sorted = []
        vert_index_to_edge_cos = {}
        vertices_on_boundary_edge = set()

        for elem in geom_inner:
            if isinstance(elem, BMVert):
                inner_verts.append(elem.index)

            elif isinstance(elem, BMEdge):
                inner_edges.append(elem.index)
                elem.select = True
                for loop in elem.link_loops:
                    loop.index = next(utils.mesh.global_loop_index_counter)

        chunks = list(divide_chunks(inner_verts, slice_count))
       
        edge_splits = defaultdict(list)
        for g, edge_vert_co in enumerate(edge_ring.edge_vert_cos.values()):
            vec_a, vec_b = edge_vert_co
            found_at = None
            vert_set: set = set()
            for i, vert_indices in enumerate(chunks):
                vert_set = vert_indices.copy()
                for vert_index in vert_indices:
                    vert = bm.verts[vert_index]
                    if utils.math.is_point_on_line_segment(vert.co, vec_a, vec_b):
                        edge_splits[g].append(vert.index)
                        vert_set.discard(vert.index) #difference_update(set([vert.index]))
                        add_edge_data(vert_index)
                        found_at = i
                        break
                if found_at is not None:
                    break
                
            if found_at is not None:
                for vert_index in vert_set:
                    edge_splits[g].append(vert_index)
                    add_edge_data(vert_index)
                del chunks[found_at]

            vert_indices = edge_splits[g]
            vert_indices.sort(key=lambda p :distance_sq(vec_a, bm.verts[p].co))

            if g == 0 and slice_count >= 2 and edges[g].is_boundary:
                vert_indices.reverse()

            new_verts_sorted.append(vert_indices)

        edge_ring.init_new_geom_data(bm, new_verts_sorted, vert_index_to_edge_cos, vertices_on_boundary_edge)

    
    # def init_ordered_percents(self):
    #     self.ordered_perc_vals.clear()
    #     n = self.slice_count
    #     for i in range(n):
    #       percent = ((1.0 + i) / ( (n) + 1.0))
    #       self.ordered_perc_vals[i] = percent

    
    def restore_vert_positions(self, context):
      
        # for index, value in self.ordered_perc_vals.items():
            # self.update_vert_positions(context, [value], [index])
            self.update_vert_positions(context, None, None)

    # def vert_edge_index_gen(self, thumb_indices, edge_ring):
    #     for thumb_index in thumb_indices:

    #         edge_loop_verts = edge_ring.new_edge_loop_verts[thumb_index]
    #         for i in range(len(edge_ring.edges)):
    #             edge_index = -1
    #             if edge_ring.edges[i].is_valid:
    #                edge_index = edge_ring.edges[i].index

    #             yield edge_loop_verts[i], edge_index, thumb_index


    def update_vert(self, vert: BMVert, value, start_co, end_co):
        vert.co = start_co.lerp(end_co, value)



    def update_vert_positions(self, context, thumb_values, thumb_indices):
        use_gaps = self.use_split_loops
        bm: BMesh = self.bm
        moved_verts = set()

        for index, value in enumerate(self.positions): #thumb_indices:
            for edge_ring in self.edge_rings:
                verts = edge_ring.new_edge_loop_verts

                edge_loop = verts[index]
                for i in range(len(edge_ring.edges)):
                    start_co = None
                    end_co = None

                    vert_index = edge_loop[i]
                    if not use_gaps:
                        end_co, start_co = edge_ring.edge_vert_cos[edge_ring.edges[i].index]
                  
                    self.bm.verts.ensure_lookup_table()
                    vert: BMVert = bm.verts[vert_index]
                    if vert.index not in moved_verts:
                        # value = self.ordered_perc_vals[index]
                        if not use_gaps:
                            bm_edge = edge_ring.edges[i] 
                            if i != 0 or not bm_edge.is_boundary:
                                vert.co = start_co.lerp(end_co, value)
                            else:
                                vert.co = end_co.lerp(start_co, value)
        
                        else:
                            flip = False
                            if vert_index not in edge_ring.vertices_on_boundary_edge or i == len(edge_ring.edges)-1:
                                flip = True
                            self.update_split_verts(edge_ring, vert, value, flip)

                        moved_verts.add(vert_index)


    def update_split_verts(self, edge_ring, vert, value, flip):
        vert_index = vert.index
        start_co =  edge_ring.vert_index_to_edge_cos[vert_index][0]
        end_co = edge_ring.vert_index_to_edge_cos[vert_index][1]

        positions = {}
        if vert_index not in edge_ring.vertices_on_boundary_edge or flip:
            positions[vert_index] = end_co.lerp(start_co, value)
        else:
            positions[vert_index] = start_co.lerp(end_co, value)

        bm_vert_a = vert
        position = positions[vert_index]
        distance = self.gap_distance * 0.5

      
        self.points_3d.append(position)
        if bm_vert_a.index in edge_ring.vert_index_to_dir_vec_lookup:
            gap_dir_vec_a = edge_ring.vert_index_to_dir_vec_lookup[bm_vert_a.index][0].normalized()
            bm_vert_a.co = position + (gap_dir_vec_a * distance)
        else:
             bm_vert_a.co = position

        if bm_vert_a.index in edge_ring.gap_loop_vert_pairs:
            bm_vert_b = self.bm.verts[edge_ring.gap_loop_vert_pairs[bm_vert_a.index]]
            gap_dir_vec_b = edge_ring.vert_index_to_dir_vec_lookup[bm_vert_a.index][1].normalized()
            bm_vert_b.co = position + (gap_dir_vec_b * distance)


    def split_edge_loops(self):
        def cap_section(verts):
            self.bm.faces.new([self.bm.verts[vert_index] for vert_index in verts]).normal_update()
        
        for edge_ring in self.edge_rings:
            loop_vert_pairs = {}
            vert_index_to_dir_vec_lookup = {}
            for edge_loop in edge_ring.new_edge_loop_loops:
                # if len(edge_loop) < 2:
                #      continue
                try:
                    loop_a, loop_b, vert_index_to_dir_vec = utils.mesh.clone_edges(self.bm, side=1, loops=[loop.edge.index for loop in edge_loop if loop.edge.select])
                    self.bm.edges.index_update()
                    utils.mesh.bmesh_loop_index_update(self.bm)
                    edge_ring.update_loops()

                   
                    # https://stackoverflow.com/a/21303303
                    def pairwise(iterable):
                        a, b = tee(iterable)
                        next(b, None)
                        return zip(a, b)

                    loop_a.append(loop_a[0])
                    loop_b.append(loop_b[0])
                    # for loop_a_pair, loop_b_pair in zip(pairwise(loop_a), pairwise(loop_b)):
                    #     # print(loop_a_pair, loop_b_pair)
                    #     verts = [self.bm.verts[vert] for vert in [loop_a_pair[0], loop_a_pair[1], loop_b_pair[0], loop_b_pair[1]]]
                    #     face = utils.mesh.get_face_with_verts(verts)
                    #     if face is not None:
                    #         self.bm.faces.remove(face)
                    #         for i in range(2):
                    #             edge = self.bm.edges.get([verts[i], verts[i+2]])
                    #             if edge is not None and edge.is_wire:
                    #                 self.bm.edges.remove(edge)

                    # if self.cap_sections:
                    #     cap_section(loop_a[:-1])
                    #     cap_section(loop_b[:-1])
                        
                        #bmesh.ops.contextual_create(self.bm, geom=[self.bm.verts[vert_index] for vert_index in loop_a])
                        #bmesh.ops.contextual_create(self.bm, geom=[self.bm.verts[vert_index] for vert_index in loop_b])

                    vert_index_to_dir_vec_lookup.update(vert_index_to_dir_vec)
                    loop_vert_pairs.update({vert_a: vert_b for (vert_a, vert_b) in zip(loop_a, loop_b)})

                except:
                    pass
            edge_ring.init_gap_data(loop_vert_pairs, vert_index_to_dir_vec_lookup)
        # self.bm.select_flush_mode()
       

    def split_loops(self, update=False):
        context = bpy.context
        if update:
            self.revert_bmesh(context)

            utils.mesh.ensure(self.bm)
            self.init_edge_ring_data()
        
            for edge_ring in self.edge_rings:
                self.create_geometry(context, edge_ring, self.slice_count)

            utils.mesh.ensure(self.bm)

        if self.use_split_loops:
            self.split_edge_loops()


        if update:
            self.restore_vert_positions(context)

            context = bpy.context
            mesh = context.active_object.data
            bmesh.update_edit_mesh(mesh)

            # self.set_flow()


    def ensure_bmesh(self):
        if self.bm is None or not self.bm.is_valid:
            bpy.context.active_object.update_from_editmode()
            mesh = bpy.context.active_object.data
            
            self.bm: bmesh = bmesh.from_edit_mesh(mesh)

        return self.bm

    
    @staticmethod
    def set_flow():
        # prefs = utils.common.prefs()
        # tension = prefs.tension
        # iterations = prefs.iterations
        # min_angle = prefs.min_angle

        bpy.ops.mesh.set_edge_flow('INVOKE_DEFAULT') # tension=tension, iterations=iterations, min_angle=min_angle