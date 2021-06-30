import bpy
from bmesh.types import *

from .. import utils
from .. utils.ops import get_m_button_map as btn
from . fast_loop_common import (FastLoopCommon, EdgeData, Mode, get_active_mode, mode_enabled, 
                                set_mode, get_options, set_option, enum_to_mode_str, str_to_mode_enum)

from .. snapping.snapping import SnapContext

from . fast_loop_algorithms import (ComputeEdgePostitonsMultiAlgorithm, 
                                    ComputeEdgePostitonsSingleAlgorithm, 
                                    ComputeEdgePostitonsOverrideAlgorithm)

from .. keymaps.event_handler import Event_Handler
from .. keymaps.modal_keymapping import ModalOperatorKeymapCache as km_cache

class EdgeData():
    """Stores the points and starting vert for an edge.

    Attributes:
        points: Points along an edge.
        loop: The loop for this edge.
    """
    def __init__(self, points, loop):
        self.points = points
        self.edge = loop.edge
        self.first_vert = loop.vert


class FastLoopOperator(bpy.types.Operator, FastLoopCommon):
    bl_idname = 'fl.fast_loop'
    bl_label = 'fast_loop operator'
    bl_options = {'REGISTER'}

    invoked_by_tool: bpy.props.BoolProperty(
    name='tool invoked',
    description='Do not change. This is meant to be hidden',
    default=False,
    options={'HIDDEN', 'SKIP_SAVE'}
    )

    is_scaling = False
    is_selecting = False
    edge_pos_algorithm = None
    freeze_edge = False
    frozen_edge = None
    frozen_edge_index = None

    # Needed for tri fan loops
    current_face_index = None

    segments = 2

    event_handler = None

    prev_mode = Mode.NONE
    @property
    def prev_mode(self):
        mode = str_to_mode_enum(get_options().prev_mode)
        if mode != Mode.NONE:
            return mode
        return None
    
    @prev_mode.setter
    def prev_mode(self, value):
        set_option('prev_mode', enum_to_mode_str(value))

    @property
    def segments(self):
        return get_options().segments

    @segments.setter
    def segments(self, value):
        set_option('segments', value)

    scale = 0.0
    @property
    def scale(self):
        return get_options().scale
    
    @scale.setter
    def scale(self, value):
        set_option('scale', value)
    
    use_multi_loop_offset = False
    @property
    def use_multi_loop_offset(self):
        return get_options().multi_loop_offset
    
    @use_multi_loop_offset.setter
    def use_multi_loop_offset(self, value):
        set_option('multi_loop_offset', value)

    loop_position_override = False
    @property
    def loop_position_override(self):
        return get_options().loop_position_override
    

    insert_at_midpoint = False
    @property
    def insert_at_midpoint(self):
        return get_options().insert_midpoint

    @insert_at_midpoint.setter
    def insert_at_midpoint(self, value):
        set_option('insert_midpoint', value)

    mirrored = False
    @property
    def mirrored(self):
        return get_options().mirrored
    
    @mirrored.setter
    def mirrored(self, value):
        set_option('mirrored', value)

    perpendicular = False
    @property
    def perpendicular(self):
        return get_options().perpendicular
    
    @perpendicular.setter
    def perpendicular(self, value):
        return set_option('perpendicular', value)

    select_new_edges = False
    @property
    def select_new_edges(self):
        return get_options().select_new_edges

    @select_new_edges.setter
    def select_new_edges(self, value):
        set_option('select_new_edges', value)

    use_snap_points = False
    @property
    def use_snap_points(self):
        return get_options().use_snap_points
    
    @use_snap_points.setter
    def use_snap_points(self, value):
        set_option('use_snap_points', value)

    snap_divisions = 2
    @property
    def snap_divisions(self):
        return get_options().snap_divisions
    
    @snap_divisions.setter
    def snap_divisions(self, value):
        set_option('snap_divisions', value)
    
    lock_snap_points = False
    @property
    def lock_snap_points(self):
        return get_options().lock_snap_points

    @lock_snap_points.setter
    def lock_snap_points(self, value):
        set_option('lock_snap_points', value)

    snap_factor = 0.5
    @property
    def snap_factor(self):
        return get_options().snap_factor
    
    @snap_factor.setter
    def snap_factor(self, value):
        set_option('snap_factor', value)


    def set_header(self, context):
        offset_str = None
        if self.current_edge is not None and self.current_edge.is_valid:
            offset = self.offset
            offset_str =  f"Factor: {offset:04.3f}"
           
        else:
            offset_str = "Factor: None"
        scale = context.scene.unit_settings.scale_length
        header = utils.ui.header(
            offset_str,
            # * self.current_edge.calc_length() if self.current_edge is not None else 0.0
            f"Offset: {self.distance * scale:07.3f}",
            f"Scale: {self.scale * 100 :02.1f}",
            f"Even: {self.use_even}",
            f"Flipped: {self.flipped}",
            f"Loops: {self.segments}",
            f"Mirrored: {self.mirrored}",
            f"Midpoint: {self.insert_at_midpoint}",
        )

        context.area.header_text_set(header)
    
    
    def set_status(self, context):

        def status(header, context):
    
            extra_mapppings = {"Insert loop(s)": utils.ui.get_mouse_select_text(), 
                                "Pie menu" if not utils.common.prefs().disable_pie else "Exit": utils.ui.get_mouse_other_button_text(),
                                "Change loop number": "1-9 | +-",}
            keymap = km_cache.get_keymap(self.bl_idname)
            header = utils.ops.generate_status_layout_text_only(keymap, header.layout, extra_mapppings)#utils.ops.generate_status_layout(shortcuts, header.layout)       
            utils.ui.statistics(header, context)

        context.workspace.status_text_set(status)


    def draw(self, context):
        pass

    def execute(self, context):                
        return {'FINISHED'}

    def setup(self, context):
        super().setup(context)

        self.set_status(context)
        scene = context.scene
        slots = scene.Loop_Cut_Slots.loop_cut_slots
        #slots.clear()
        if len(slots.keys()) == 0:
            for i in range(9):
                slot = slots.add()
                for j in range(i+1):
                    percent = ((1.0 + j) / ( (i+1) + 1.0))
                    prop = slot.loop_cut_slot.add()
                    prop.percent = percent * 100
                    
        self.edge_pos_algorithm = self.get_edge_pos_algorithm()


    def invoke(self, context, event):
        self.event_handler = Event_Handler(km_cache.get_keymap(self.bl_idname))
        return super().invoke(context, event)

    def get_edge_pos_algorithm(self):
        active_mode = get_active_mode()
        if active_mode in {Mode.SINGLE, Mode.MULTI_LOOP} and not self.loop_position_override:
            if active_mode == Mode.SINGLE:
                return ComputeEdgePostitonsSingleAlgorithm()
            else:
                return ComputeEdgePostitonsMultiAlgorithm()
        elif active_mode in {Mode.SINGLE, Mode.MULTI_LOOP} and self.loop_position_override and self.segments < 10:
            return ComputeEdgePostitonsOverrideAlgorithm()
        else:
            return ComputeEdgePostitonsMultiAlgorithm()

    
    def event_raised(self, event, value):
        if event == "mode":
            if value == "EDGE_SLIDE":
                if self.from_ui:
                    context_override = utils.ops.get_context_overrides(self.active_object)
                    bpy.ops.fl.edge_slide(context_override, 'INVOKE_DEFAULT', invoked_by_fla=True)
                    
                    self.from_ui = True

            self.from_ui = True

        self.edge_pos_algorithm = self.get_edge_pos_algorithm()

    
    def update_current_ring(self):
        self.current_ring = list(utils.mesh.bmesh_edge_ring_walker(self.current_edge))

        if len(self.current_ring) < 2:
            self.current_ring = list(utils.mesh.bm_tri_fan_walker(self.bm, self.current_face_index, self.current_edge))
            return self.current_ring[1] is not None

        return True

    
    def update(self, element_index, nearest_co):
        bm: BMesh = self.ensure_bmesh()
        bm.edges.ensure_lookup_table()
        edge = bm.edges[element_index]

        if edge.is_valid:
            if not self.freeze_edge or (mode_enabled(Mode.REMOVE_LOOP) or mode_enabled(Mode.SELECT_LOOP)):
                self.current_edge = edge
                self.current_edge_index = edge.index


                if not (mode_enabled(Mode.REMOVE_LOOP) or mode_enabled(Mode.SELECT_LOOP)):
                    if self.update_current_ring():
                        self.update_loops(nearest_co)
                        self.update_positions_along_edges()

                elif mode_enabled(Mode.REMOVE_LOOP):
                    self.remove_loop_draw_points = self.compute_remove_loop_draw_points()

            else:
                self.current_edge = self.frozen_edge
                self.current_edge_index = self.frozen_edge_index

                if element_index == self.frozen_edge_index:
                    if self.update_current_ring():
                        self.update_loops(nearest_co)
                        self.update_positions_along_edges()
    
    def on_numeric_input_changed(self, value: str):
        if self.is_scaling:
            self.scale = float(value) * 0.01

        self.update_loops()
        self.update_positions_along_edges()


    def modal(self, context, event):

        if context.mode != 'EDIT_MESH' or (self.invoked_by_tool and not \
        any(tool_name in ['fl.fast_loop_tool'] \
            for tool_name in [tool.idname for tool in context.workspace.tools])) or self.cancelled:
            return self.cancel(context)
        
        self.set_status(context)

        if event.type == 'TIMER':
            return {'RUNNING_MODAL'}

        if mode_enabled(Mode.EDGE_SLIDE):
            return {'PASS_THROUGH'}
        
        
        if self.dirty_mesh and not mode_enabled(Mode.REMOVE_LOOP):
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            self.dirty_mesh = False

            return {'RUNNING_MODAL'}

        if self.snap_context is None:
            self.snap_context: SnapContext = SnapContext.get(context, context.evaluated_depsgraph_get(), context.space_data, context.region)
            self.snap_context.add_object(self.active_object)

        if self.snap_context is not None and (not self.is_scaling and not mode_enabled(Mode.EDGE_SLIDE) or mode_enabled(Mode.REMOVE_LOOP)):  
            self.update_snap_context()

            mouse_coords = (event.mouse_region_x, event.mouse_region_y)
            self.current_face_index, element_index, nearest_co = self.snap_context.do_snap(mouse_coords, self.active_object)

            if element_index is not None:
                self.update(element_index, nearest_co) 
            else:
                self.current_edge = None

        elif self.is_scaling:
            pass 
        
        handled = False

        modal_event = self.event_handler.handle_event(event)
        if modal_event in km_cache.get_keymap(self.bl_idname).get_valid_keymap_actions():
          
            if modal_event == "mirrored":
                self.mirrored = not self.mirrored

            elif modal_event == "even":
                self.use_even = not self.use_even

            elif modal_event == "flip":
                self.flipped = not self.flipped
                if self.use_snap_points and  self.snap_divisions == 1:
                    if self.flipped :
                        self.snap_factor = 100 - self.snap_factor
                    else:
                        self.snap_factor = 100 - self.snap_factor

            elif modal_event == "snap_points":
                self.use_snap_points = not self.use_snap_points

            elif modal_event == "lock_snap_points":
                self.lock_snap_points = not self.lock_snap_points

            elif modal_event == "scale":
                if not self.is_scaling:
                    self.start_mouse_pos_x = event.mouse_x
                    self.event_handler.numeric_input_begin(event, self.on_numeric_input_changed)
                    self.is_scaling = True
                else:
                    self.is_scaling = False
                    self.event_handler.numeric_input_end()


            elif modal_event == "midpoint":
                self.insert_at_midpoint = not self.insert_at_midpoint

            elif modal_event == "select_new_loops":
                self.select_new_edges = not self.select_new_edges
            
            elif modal_event == "perpendicular":
                self.perpendicular = not self.perpendicular

            elif modal_event == "multi_loop_offset":
                self.use_multi_loop_offset = not self.use_multi_loop_offset
            
            elif modal_event == "freeze_edge":
                self.freeze_edge = not self.freeze_edge
                if self.freeze_edge:
                    self.frozen_edge = self.current_edge
                    self.frozen_edge_index = self.current_edge_index

            handled = True

        # Use this to consume events for now
        elif modal_event == "numeric_input":
            self.set_header(context)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        elif event.type in {'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE'} and event.value == 'PRESS':
            num_lookup = {'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5, 'SIX': 6, 'SEVEN': 7, 'EIGHT': 8, 'NINE': 9}
            n = num_lookup[event.type]
            if n == 1:
                self.from_ui = False
                set_mode(Mode.SINGLE)
                self.prev_mode = Mode.SINGLE
            else:
                self.from_ui = False
                set_mode(Mode.MULTI_LOOP)
                self.prev_mode = Mode.MULTI_LOOP

            self.segments = n
            self.edge_pos_algorithm = self.get_edge_pos_algorithm()
            handled = True
        
        elif event.type in {'EQUAL', 'NUMPAD_PLUS', 'MINUS', 'NUMPAD_MINUS'} and event.value == 'PRESS':
            if event.type in {'EQUAL', 'NUMPAD_PLUS'}:
                self.segments += 1
            else:
                self.segments -= 1

            if self.segments == 1:
                self.from_ui = False
                set_mode(Mode.SINGLE)
                self.prev_mode = Mode.SINGLE
            else:
                self.from_ui = False
                set_mode(Mode.MULTI_LOOP)
                self.prev_mode = Mode.MULTI_LOOP

            self.edge_pos_algorithm = self.get_edge_pos_algorithm()
            handled = True

        elif event.type in {'ESC'}:
            set_option('cancel', True)
            handled = True

        if event.type == btn('RIGHTMOUSE') and event.value == 'PRESS':
            if not utils.common.prefs().disable_pie:
                if utils.ui.inside_view_3d((event.mouse_x, event.mouse_y)):
                    # Preemptively lock the points to prevent them from changing locations after the lock_points property is set to True.
                    # This is okay to do because they will be unlocked in update_snap_context() if the property is set to False.
                    self.snap_context.lock_snap_points
                    bpy.ops.wm.call_menu_pie(name="FL_MT_FastLoop_Pie")
            else:
                set_option('cancel', True)

            handled = True

        if event.type == 'MOUSEMOVE':

           if self.is_scaling and not event.alt and mode_enabled(Mode.MULTI_LOOP) and not mode_enabled(Mode.REMOVE_LOOP):
                utils.ops.cursor_warp(event)
                delta_x = event.mouse_x - event.mouse_prev_x
                delta_x *= 0.001 if event.shift else 0.01
                self.scale += delta_x
            
                self.update_loops()
                if self.update_positions_along_edges():
                    self.start_mouse_pos_x = event.mouse_x
                else:
                    self.ensure_bmesh()
                    self.is_scaling = False

        if super().modal(context, event):
            handled = True

        self.set_header(context)
        context.area.tag_redraw()
        if handled:
            return {'RUNNING_MODAL'}
        else:
            return {'PASS_THROUGH'}

    def edge_slide_finished(self, message=None, data=None):
        
        if message is not None and message == "switch_modes":
            event = data
            num_lookup = {'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5, 'SIX': 6, 'SEVEN': 7, 'EIGHT': 8, 'NINE': 9}
            n = num_lookup[event.type]
            if n == 1:
                self.from_ui = False
                set_mode(Mode.SINGLE)
                self.prev_mode = Mode.SINGLE
            else:
                self.from_ui = False
                set_mode(Mode.MULTI_LOOP)
                self.prev_mode = Mode.MULTI_LOOP

            self.segments = n
            self.edge_pos_algorithm = self.get_edge_pos_algorithm()

        else:
            if self.prev_mode is not None:
                set_mode(self.prev_mode)
            else:
                set_mode(Mode.SINGLE)
        
            bpy.ops.ed.undo_push()


    def modal_select_edge_loop_released(self):
        if not mode_enabled(Mode.REMOVE_LOOP):
            if self.prev_mode is not None:
                set_mode(self.prev_mode)
            else:
                set_mode(Mode.SINGLE)
           

    def modal_remove_edge_loop_released(self):
        if self.prev_mode is not None:
            set_mode(self.prev_mode)
        else:
            set_mode(Mode.SINGLE)

    
    def draw_3d(self, context):
        super().draw_3d(context)

        if not (mode_enabled(Mode.REMOVE_LOOP) or mode_enabled(Mode.SELECT_LOOP) or mode_enabled(Mode.EDGE_SLIDE)) and self.current_edge is not None and self.loop_draw_points:

            if self.use_even or self.loop_position_override:
                utils.drawing.draw_point(self.world_mat @ self.edge_start_position, color=(1.0, 0.0, 0.0, 0.4))


    def cleanup(self, context):
        super().cleanup(context)
    
        if self.snap_context is not None:
            if self.use_snap_points:
                self.use_snap_points = False
                self.snap_context.disable_increment_mode()


    def update_loops(self, nearest_co=None):

        if self.current_edge is None:
            return False

        if not self.is_scaling and nearest_co is not None:
            self.current_position = self.world_inv @ nearest_co

        if self.current_ring:
            if not self.bm.is_valid:
                return False

            if not self.is_scaling:
                self.distance, self.shortest_edge_len, self.edge_start_position, self.edge_end_position, self.is_loop = self.get_data_from_edge_ring()

    def update_positions_along_edges(self):

        self.loop_draw_points.clear()
        self.edge_data.clear()

        if mode_enabled(Mode.MULTI_LOOP) and self.segments == 1:
            self.segments = 2
            
        for i, loop in enumerate(self.current_ring):

            if not loop.is_valid:
                return False

            points_on_edge = []
            for point_on_edge in self.get_posititons_along_edge(loop, i):
                points_on_edge.append(point_on_edge)

            self.edge_data.append(EdgeData(points_on_edge, loop))
            self.loop_draw_points.append(points_on_edge)

        return True


    def update_snap_context(self):
            if self.use_snap_points:
                self.snap_context.enable_increment_mode()
                self.snap_context.set_snap_increment_divisions(self.snap_divisions)
                
            else:
                self.snap_context.disable_increment_mode()

            if self.lock_snap_points:
                self.snap_context.lock_snap_points()

            else:
                self.snap_context.unlock_snap_points()
                
            self.snap_context.set_snap_factor(self.snap_factor)

 
    def create_geometry(self, context, set_edge_flow=False):
        def order_points(edge_data):
            points = []
            if self.loop_position_override and self.segments < 10:
                points = [data.points if self.flipped else list(reversed(data.points)) for data in self.edge_data]
            else:
                if get_active_mode() == Mode.SINGLE and self.mirrored:
                    if not self.flipped:
                        points = [data.points if self.offset < 0.5 else list(reversed(data.points)) for data in self.edge_data]

                    else:
                        points = [data.points if self.offset > 0.5 else list(reversed(data.points)) for data in self.edge_data]
                
                elif get_active_mode() == Mode.MULTI_LOOP and self.mirrored:
                    points = [data.points if not self.flipped else list(reversed(data.points)) for data in self.edge_data]

                else:
                    points = [data.points if not self.flipped else list(reversed(data.points)) for data in self.edge_data]

            return points

        num_segments = self.segments
        
        if mode_enabled(Mode.SINGLE):
            num_segments = 1
        
        if self.mirrored:
            num_segments *= 2
            

        edges = [data.edge for data in self.edge_data]
      
        edge_verts_co = []
        if not self.use_multi_loop_offset and mode_enabled(Mode.MULTI_LOOP):
            edge_verts_co = [(data.edge.other_vert(data.first_vert).co, data.first_vert.co) for data in self.edge_data]
        else:
            edge_verts_co = [(data.first_vert.co, data.edge.other_vert(data.first_vert).co) for data in self.edge_data]
     
        points = order_points(self.edge_data)
        super().create_geometry(context, edges, points, edge_verts_co, num_segments, select_edges=self.select_new_edges or set_edge_flow)


    def get_posititons_along_edge(self, loop: BMLoop, i):

        flipped = self.flipped
        opposite_edge = loop.link_loop_next.link_loop_next.edge
  
        if not loop.edge.is_manifold and not opposite_edge.is_manifold and loop.edge.index != self.current_edge.index:
            flipped = not flipped

        # Edge is not manifold, being moused over,  and it's the first edge in the list
        elif not loop.edge.is_manifold and loop.edge.index == self.current_edge.index and i == 0:
            if opposite_edge.is_manifold:
                flipped = not flipped

        elif not loop.edge.is_manifold and loop.edge.index != self.current_edge.index and i == 0:
            if opposite_edge.is_manifold:
                flipped = not flipped

        start = loop.vert.co
        end = loop.edge.other_vert(loop.vert).co

        factor = self.offset

        if self.insert_at_midpoint:
            factor = 0.5

        straight = self.perpendicular
        use_even = self.use_even and not straight

        return self.edge_pos_algorithm.execute(self, start, end, factor, use_even, flipped, self.mirrored, straight)