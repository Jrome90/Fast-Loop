from __future__ import annotations
from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from ..props.fl_properties import AllPropsNoSnap
    from bmesh.types import BMFace, BMLoop


from contextlib import suppress
import time

import bpy
from mathutils import geometry, Vector 

from ..utils import draw_3d, mesh, ops, common, ui, math
from ..props.fl_properties import MultiLoopProps, SubProps, SnapProps, AllPropsNoSnap

from .fast_loop_common import FastLoopCommon, CurrentPos
from .fast_loop_helpers import (Mode, get_active_mode, mode_enabled)

from .actions.insert_single_loop import InsertSingleLoopAction

from ..snapping.snapping  import SnapContext

from . fast_loop_algorithms import (ComputeEdgePostitonsMultiAlgorithm, 
                                    ComputeEdgePostitonsSingleAlgorithm, 
                                    ComputeEdgePostitonsOverrideAlgorithm)

from ..keymaps.event_handler import Event_Handler, NumericInputResults
from ..keymaps.modal_keymapping import ModalOperatorKeymapCache as km_cache

from ..ui.gizmos.gizmo_snapping import RP_GGT_SnapGizmoGroup

from ..ui.widgets import (VLayoutPanel, VLayoutDragPanel, make_hotkey_label, make_property_label, 
                            BL_UI_SliderMulti, make_property_label, make_hotkey_label)

class FastLoopOperator(bpy.types.Operator, FastLoopCommon):
    bl_idname = 'fl.fast_loop'
    bl_label = 'fast_loop operator'
    bl_options = {'REGISTER', 'INTERNAL'}

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

    is_scaling = False
    snap_enabled = False
    force_offset_value = -1
    frozen_edge = None
    frozen_edge_index = None
    frozen_face_index = None

    main_panel_hud = None
    single_loop_panel: VLayoutPanel = None
    multi_loop_panel: VLayoutPanel = None
    extras_panel = None

    event_handler = None
    last_numeric_input_results: NumericInputResults = None
    last_numeric_dist_value = None

    slider_widget: BL_UI_SliderMulti = None

    draw_direction_arrow_lines: List = []
   
#region -Properties
    @property
    def segments(self):
        return self.fast_loop_options.segments

    @segments.setter
    def segments(self, value):
        self.fast_loop_options.segments = value

    @property
    def scale(self):
        return self.fast_loop_options.scale
    
    @scale.setter
    def scale(self, value):
        self.fast_loop_options.scale = value

    # Used to display either distance values or scale in the HUD. 
    @property
    def loop_space_value(self):
        return self.fast_loop_options.loop_space_value
    
    @loop_space_value.setter
    def loop_space_value(self, value):
        self.fast_loop_options.loop_space_value = str(value)
    
    @property
    def use_multi_loop_offset(self):
        return self.fast_loop_options.use_multi_loop_offset
    
    @use_multi_loop_offset.setter
    def use_multi_loop_offset(self, value):
        self.fast_loop_options.use_multi_loop_offset = value

    @property
    def loop_position_override(self):
        return self.fast_loop_options.loop_position_override
    
    @loop_position_override.setter
    def loop_position_override(self, value):
        self.fast_loop_options.loop_position_override = value
    
    @property
    def mirrored(self):
        return self.fast_loop_options.mirrored
    
    @mirrored.setter
    def mirrored(self, value):
        self.fast_loop_options.mirrored = value

    @property
    def perpendicular(self):
        return self.fast_loop_options.perpendicular
    
    @perpendicular.setter
    def perpendicular(self, value):
        self.fast_loop_options.perpendicular = value

    @property
    def insert_verts(self):
        return self.fast_loop_options.insert_verts

    @insert_verts.setter
    def insert_verts(self, value):
        self.fast_loop_options.insert_verts = value

    @property
    def insert_on_selected_edges(self):
        return self.fast_loop_options.insert_on_selected_edges

    @insert_on_selected_edges.setter
    def insert_on_selected_edges(self, value):
        self.fast_loop_options.insert_on_selected_edges = value

    @property
    def freeze_edge(self):
        return self.fast_loop_options.freeze_edge

    @freeze_edge.setter
    def freeze_edge(self, value):
        self.fast_loop_options.freeze_edge = value

    @property
    def use_snap_points(self):
        return self.fast_loop_options.use_snap_points
    
    @use_snap_points.setter
    def use_snap_points(self, value):
        self.fast_loop_options.use_snap_points = value

    @property
    def snap_divisions(self):
        return self.fast_loop_options.snap_divisions
    
    @snap_divisions.setter
    def snap_divisions(self, value):
       self.fast_loop_options.snap_distance = value
    
    @property
    def lock_snap_points(self):
        return self.fast_loop_options.lock_snap_points

    @lock_snap_points.setter
    def lock_snap_points(self, value):
        self.fast_loop_options.lock_snap_points = value

    @property
    def use_distance(self):
        return self.fast_loop_options.use_distance
 
    @property
    def auto_segment_count(self):
        return self.fast_loop_options.auto_segment_count

    @auto_segment_count.setter
    def auto_segment_count(self, value):
        self.fast_loop_options.auto_segment_count = value

    @property
    def snap_distance(self):
        return self.fast_loop_options.snap_distance
    
    @snap_distance.setter
    def snap_distance(self, value):
        self.fast_loop_options.snap_distance = value
    
    @property
    def snap_select_vertex(self):
        return self._snap_select_vertex
        
    @snap_select_vertex.setter
    def snap_select_vertex(self, value):
        self._snap_select_vertex = value
     
    @property
    def auto_segment_count(self):
        return self.fast_loop_options.auto_segment_count
#endregion

    def get_all_props_no_snap(self):
        return AllPropsNoSnap(self.common_props, self.multi_loop_props, self.sub_props)


    def draw(self, context):
        pass


    def execute(self, context):                
        return {'FINISHED'}


    def setup(self, context):
        super().setup(context)
        window_manager = context.window_manager
        window_manager.Loop_Cut_Slots.setup(context)
                    
        self.edge_pos_algorithm = self.get_edge_pos_algorithm()

        self.multi_loop_props.loop_space_value = self.scale

        main_panel_hud_x = common.prefs().operator_panel_x
        main_panel_hud_y = common.prefs().operator_panel_y
        self.main_panel_hud = VLayoutDragPanel(context, 200, 100, (main_panel_hud_x, main_panel_hud_y), 1, "Single")
        self.main_panel_hud.bg_color = (0.8, 0.8, 0.8, 0.0)
        self.main_panel_hud.ignore_child_widget_focus = True

        self.single_loop_panel =  self.create_single_loop_panel(context)
        self.single_loop_panel.bg_color = (0.8, 0.8, 0.8, 0.0)
        self.multi_loop_panel = self.create_multi_loop_panel(context)
        self.multi_loop_panel.bg_color = (0.8, 0.8, 0.8, 0.0)
        self.extras_panel = self.create_extras_panel(context)
        self.extras_panel.bg_color = (0.8, 0.8, 0.8, 0.0)

        self.main_panel_hud.add_child_widget("Single", self.single_loop_panel)
        self.main_panel_hud.add_child_widget("Multi", self.multi_loop_panel)
        self.main_panel_hud.add_child_widget("Extras", self.extras_panel)
        self.main_panel_hud.set_child_visibility_by_name("Extras", not common.prefs().panel_minimized)

        self.main_panel_hud.set_location(main_panel_hud_x,main_panel_hud_y)
        self.single_loop_panel.set_location(main_panel_hud_x,main_panel_hud_y)
        self.multi_loop_panel.set_location(main_panel_hud_x,main_panel_hud_y)

        width = ui.get_slider_width()
        x_pos, y_pos = ui.get_slider_position()
        self.slider_widget = BL_UI_SliderMulti(context, x_pos, y_pos, width, 30, text_format="{:0." + str(1) + "f}%")
        self.slider_widget.is_static = True
        self.slider_widget.color = (0.5, 0.5, 0.5, 1.0)
        self.slider_widget.thumb_color= (1.0, 1.0, 1.0, 1.0)
        self.slider_widget.select_color = (1.0, 1.0, 1.0, 1.0)
        self.slider_widget.min = 0.0
        self.slider_widget.max = 100.0
        self.slider_widget.decimals = 2
        self.slider_widget.show_min_max = False
        self.slider_widget.text_size = 10

        self.push_action(InsertSingleLoopAction(self))


    def invoke(self, context, event):
        result = super().invoke(context, event)
        if result != {'CANCELLED'}:
            if not ops.match_event_to_keymap(event, ops.get_undo_keymapping()):
                self.fast_loop_options.reset_to_defaults()

            self.event_handler = Event_Handler(km_cache.get_keymap(self.bl_idname))
        return result


    def cleanup(self, context):
        super().cleanup(context)

        if self.snap_context is not None:
            props = self.snap_props
            if props.use_snap_points:
                props.use_snap_points = False
                self.snap_context.disable_increment_mode()
                
        if self.snap_enabled:
            self.disable_snapping(context)
    

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

    
    def event_raised(self, event, value, context=None):
        if event == "loopcut_value_changed":
            self.update(self.current_edge_index, None)
        
        elif event == "snap_gizmo_update":
            if value is not None and self.snap_enabled:
                start_pos, end_pos = self.loop_data.get_active_loop_endpoints()
                snap_point, _= geometry.intersect_point_line(value, start_pos, end_pos)
                self.snap_position = snap_point
                self.is_snapping = True

                self.update(self.current_edge_index, snap_point)
            else:
                self.is_snapping = False
        else:
            self.single_loop_panel.update_widget(event, value)
            self.single_loop_panel.layout_widgets()
            self.multi_loop_panel.update_widget(event, value)
            self.multi_loop_panel.layout_widgets()
            self.extras_panel.update_widget(event, value)

        self.edge_pos_algorithm = self.get_edge_pos_algorithm()

    #TODO Get this working properly
    # def on_thumb_move(self, **kwargs):
    #     context = kwargs["context"]
    #     index = kwargs["index"]
    #     value = kwargs["value"]

    #     window_manager = context.window_manager
    #     slot = window_manager.Loop_Cut_Slots.loop_cut_slots[self.segments-1]

    #     #TODO: If mirrored get the smallest index if index > len(slot.loop_cut_slot)
    #     if slot.loop_cut_slot[index].get_method() == 'PERCENT':
    #         loop_cut_value = slot.loop_cut_slot[index].percent

    #         slot.loop_cut_slot[index].percent = value[index] *100
    #         self.slider_widget.set_slider_pos([lc.percent*0.01 for lc in slot.loop_cut_slot.values()])
    #     else:
    #         start_pos, end_pos = self.loop_data.get_active_loop_endpoints()

    #         position = start_pos.lerp(end_pos, value[index])
    #         slot.loop_cut_slot[index].distance = (start_pos - position).length
    #         edge_len = (end_pos - start_pos).length
    #         self.slider_widget.set_slider_pos([slot.distance / edge_len for slot in slot.loop_cut_slot.values()])

    
    def update(self, element_index, nearest_co=None):
        self.force_offset_value = -1
        bm = self.ensure_bmesh_(self.active_object)
        
        bm.edges.ensure_lookup_table()
        with suppress(IndexError, AttributeError):
            edge = bm.edges[element_index]
            if edge.is_valid: 
                if not self.freeze_edge:
                    self.current_edge = edge
                    self.current_edge_index = edge.index
                else:
                    if self.frozen_edge is not None and not self.frozen_edge.is_valid:
                        self.freeze_edge = False
                        return

                    self.current_edge = self.frozen_edge
                    self.current_edge_index = self.frozen_edge_index
                    self.current_face_index = self.frozen_face_index

                if nearest_co is not None:
                    self.current_position = CurrentPos(nearest_co, self.world_inv @ nearest_co)

                self.current_action.update()
                self.update_slider()
        


    def calculate_scale_value(self):

        last_numeric_results = self.last_numeric_input_results

        if last_numeric_results is not None:
            value  = last_numeric_results.value
            edge_len = 0.0
            if last_numeric_results.is_distance:
                if self.common_props.use_even or self.multi_loop_props.use_multi_loop_offset:
                    edge_len = self.loop_data.get_shortest_edge_len()
                else:
                    edge_len = self.current_edge.calc_length()
                edge_len = (value / edge_len) * (self.common_props.segments - 1.0) if edge_len != 0 else 0
                return edge_len
            else:
                return value * 0.01
        else:
            return self.multi_loop_props.scale

    # @utils.safety.decorator
    def modal(self, context, event):
        if context.mode != 'EDIT_MESH' or (self.invoked_by_tool and not \
        any(tool_name in {'fl.fast_loop_tool'} \
            for tool_name in [tool.idname for tool in context.workspace.tools])) or self.cancelled:
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
            return {'PASS_THROUGH'}

        handled = False
        modal_event = self.event_handler.handle_event(event)
        if modal_event is not None:
            if modal_event in km_cache.get_keymap(self.bl_idname).get_valid_keymap_actions(): 
                self.current_action.handle_modal_event(context, modal_event, event)
                handled = True

            # Use this to consume events for now
            elif modal_event in {"numeric_input"}:
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}
        # Prevent an update if snapping (holding ctrl) and user then pressed z to undo.
        # Otherwise the object data is invalid, and it will raise an exception.
        if self.snap_enabled and self.is_snapping and not ops.match_event_to_keymap(event, ops.get_undo_keymapping()):
            try:
                self.update(self.frozen_edge_index, self.snap_position)
            except ReferenceError:
               return self.exception_occured(context)
            
        if not event.shift and event.ctrl and event.value in {'PRESS'} and not self.snap_enabled:
            self.snap_enabled = True
            self.freeze_edge = not self.freeze_edge
            if self.freeze_edge:
                self.frozen_edge = self.current_edge
                self.frozen_edge_index = self.current_edge_index
                self.frozen_face_index = self.current_face_index

                context.window_manager.gizmo_group_type_ensure(RP_GGT_SnapGizmoGroup.bl_idname)                   

            handled = True

        elif event.shift and event.ctrl and event.value in {'PRESS'} and self.snap_enabled:
            handled = True
            self.disable_snapping(context)
        
        elif not event.ctrl and event.value in {'RELEASE'} and self.snap_enabled:
            handled = True
            self.disable_snapping(context)

        if self.snap_context is None:
            self.snap_context: SnapContext = SnapContext.get(context, context.evaluated_depsgraph_get(), self, context.space_data, context.region,)
            
            for editable_object_data in self.selected_editable_objects.values():
                self.snap_context.add_object(editable_object_data.get_bl_object)

        if self.snap_context is not None and (not self.is_scaling and not mode_enabled(Mode.EDGE_SLIDE) or mode_enabled(Mode.REMOVE_LOOP)):  
            self.update_snap_context()

            mouse_coords = (event.mouse_region_x, event.mouse_region_y)
            try:
                self.current_face_index, element_index, nearest_co = None, None, None
                snap_results = self.snap_context.do_snap_objects([obj.get_bl_object for obj in self.selected_editable_objects.values()], mouse_coords, mouse_coords_win)
                if snap_results is not None:
                    self.current_face_index, element_index, nearest_co, bl_object = snap_results
                    if not self.is_snapping:
                        self.active_object = self.selected_editable_objects[bl_object.name]

                        if not (self.is_snapping and self.snap_enabled):
                            self.current_position = CurrentPos(nearest_co, self.world_inv @ nearest_co)
                            self.update(element_index)

                    elif self.freeze_edge and nearest_co is not None:
                        self.update(self.frozen_edge_index, nearest_co)
                
                elif not self.freeze_edge and snap_results is None:
                    self.current_edge = None
                    self.loop_draw_points.clear()
                    self.update_arrows()
                    self.slider_widget.remove_all_thumbs()
                 
            except (ReferenceError, KeyError):
                self.active_object = self.selected_editable_objects[context.active_object.name]
            except Exception as e:
                return self.exception_occured(context)
                
        elif self.is_scaling:
            self.current_action.update()

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


    def disable_snapping(self, context):
        context.window_manager.gizmo_group_type_unlink_delayed(RP_GGT_SnapGizmoGroup.bl_idname)
        bpy.context.scene.tool_settings.use_snap = False
        self.snap_enabled = False
        self.is_snapping = False
        self.freeze_edge = False
        self.snap_position = None

    
    def draw_3d(self, context):
        super().draw_3d(context)

        if not (mode_enabled(Mode.REMOVE_LOOP) or mode_enabled(Mode.EDGE_SLIDE)) and self.current_edge is not None and self.edge_data.points:
            start_pos = self.loop_data.get_active_loop_endpoints().start if self.loop_data is not None else None
            if (self.use_even or self.loop_position_override) and start_pos is not None:
                draw_3d.draw_point(start_pos, color=(1.0, 0.0, 0.0, 0.4), size=10.0)
  
    
    def update_arrows(self):
        self.draw_direction_arrow_lines.clear()
        if self.current_position is None or self.current_edge is None or self.is_single_edge:
            return
                    
        face: BMFace = mesh.get_face_from_index(self.active_object.bm, self.current_face_index)
        loop_a: BMLoop = mesh.get_face_loop_for_edge(face, self.current_edge)
        if loop_a is None:
            return
        vec_a = (mesh.get_loop_other_edge_loop(loop_a, loop_a.vert).vert.co - loop_a.vert.co)

        loop_b = mesh.get_face_loop_for_vert(face, loop_a.edge.other_vert(loop_a.vert))
        vec_b =  mesh.get_loop_other_edge_loop(loop_b, loop_a.vert).vert.co - loop_b.vert.co

        distance_along_edge = 0.09
        min_len = min(vec_a.length, vec_b.length)
        if (min_len * 0.5) <= distance_along_edge:
            distance_along_edge = min_len * 0.5

        hud_scale = common.prefs().hud_scale
        edge_dir_vec = lambda vec: vec.normalized() * distance_along_edge * hud_scale
        vert_b: Vector = (loop_a.vert.co + edge_dir_vec(vec_a)) 
        vert_b2 = loop_a.edge.other_vert(loop_a.vert).co + edge_dir_vec(vec_b)

        position_local = self.current_position.local

        vert_c, _ = geometry.intersect_point_line(position_local, vert_b, vert_b2)
                
        vert_b_world = self.world_mat @ vert_b
        vert_c_world = self.world_mat @ vert_c

        isect_points = None
        if self.edge_data is not None and self.edge_data.points:

            first_edge_points = self.edge_data.first_edge.points
            other_edge_points = self.edge_data.other_edge.points

            line1 = (first_edge_points[0], other_edge_points[0])
            line2 = (vert_b_world, vert_c_world)

            isect_points = geometry.intersect_line_line(*line1, *line2)

        if isect_points is None or isect_points[1] is None:
            return
        
        vert_c_world = isect_points[1]
        
        edge_offset = 0.0
        start = vert_c_world - (vert_c_world - vert_b_world).normalized() * 0.00
        end = vert_b_world - (vert_b_world - vert_c_world).normalized() * edge_offset
        
        vert_b2_world = self.world_mat @ vert_b2
        end_2 = vert_b2_world - (vert_b2_world - vert_c_world).normalized() * edge_offset
        start = math.constrain_point_to_line_seg(end_2, start, end)
        
        normal = math.rotate_direction_vec(face.normal, self.world_mat)
        
        arrow_a = draw_3d.Arrow(start, end, normal, math.rotate_direction_vec(vec_a.normalized(), self.world_mat), chevron_length=distance_along_edge*0.25)
        
        start = vert_c_world - (vert_c_world - vert_b2_world).normalized() * 0.00
        start = math.constrain_point_to_line_seg(end_2, start, end)

        arrow_b = draw_3d.Arrow(start,  vert_b2_world - (vert_b2_world - vert_c_world).normalized() * edge_offset, -normal, math.rotate_direction_vec(vec_b.normalized(), self.world_mat), distance_along_edge*0.25)

        distance = (loop_a.vert.co - position_local).length
        distance_str = ui.format_distance2(distance)

        arrow_a.label_text = distance_str
        self.draw_direction_arrow_lines.append(arrow_a)

        distance = (loop_a.edge.other_vert(loop_a.vert).co - position_local).length
        distance_str = ui.format_distance2(distance)
        arrow_b.label_text = distance_str
        self.draw_direction_arrow_lines.append(arrow_b)


    def update_snap_context(self):
            if self.snap_props.use_snap_points:
                self.snap_context.enable_increment_mode()
                self.snap_context.set_snap_increment_divisions(self.snap_props.snap_divisions) 
            else:
                self.snap_context.disable_increment_mode()

            if self.snap_props.lock_snap_points:
                self.snap_context.lock_snap_points()
            else:
                self.snap_context.unlock_snap_points()
            
            self.snap_context.use_distance = self.snap_props.use_distance
            self.snap_context.auto_calc_snap_points = self.snap_props.auto_segment_count
            self.snap_context.set_snap_distance(self.snap_props.snap_distance)
            

    def create_geometry(self, select_new_edges=False):

        num_segments = len(self.loop_data.get_loops())
        edge_verts = self.edge_data.edge_verts
        points = self.edge_data.points 
        edges = self.edge_data.edges

        # t1 = time.perf_counter(), time.process_time()
        selected_edges = super().create_geometry(edges, points, edge_verts, num_segments, select_new_edges=select_new_edges)

        # t2 = time.perf_counter(), time.process_time()
        # print(f" time: {t2[0] - t1[0]:.2f} seconds")
        # print(f" CPU time: {t2[1] - t1[1]:.2f} seconds")

        # Clear the draw points to hide a visual bug. :(
        self.loop_draw_points.clear()

        return selected_edges

    # TODO: Refactor. This should not be in this class.
    def update_slider(self):
        static_slider = not self.loop_position_override
        start_pos, end_pos = self.loop_data.get_active_loop_endpoints()

        if (self.flipped and not self.loop_position_override):
            start_pos, end_pos = end_pos, start_pos

        if self.edge_data is not None and self.edge_data.first_edge.points:
            points_on_edge = self.edge_data.first_edge.points
            percents = [math.inv_lerp(start_pos, end_pos, point) for point in points_on_edge]
            
            self.slider_widget.set_display_values([position * 100 for position in percents])   
            if static_slider:
                segment_count = self.segments if not self.mirrored else self.segments * 2
                percents = [(1.0 + i) / (segment_count + 1.0) for i in range(segment_count)]
        
            self.slider_widget.set_slider_pos(percents)
        
            index_a = 0 #if not self.flipped else -1 #if not self.loop_position_override else -1
            index_b = -1 #if not self.flipped else 0 #if not self.loop_position_override else 0
            
            # TODO: Move into a function and further refactor
            distance_values = []
            if not common.prefs().is_len_unit_enabled():
                self.slider_widget.set_distance_values([])
                return
            
            percent = math.inv_lerp(start_pos, end_pos, self.edge_data.first_edge.points[0])

            if percent > 0.5 and not self.loop_position_override:
                start_pos, end_pos = end_pos, start_pos

            distance_values = [(points_on_edge[index_a] - start_pos).length]
            for i, _ in enumerate(points_on_edge):
                if i == len(points_on_edge) - 1:
                    continue
                distance = (points_on_edge[i] - points_on_edge[i+1]).length
                distance_values.append(distance)
            
            distance_values.append((points_on_edge[index_b] - end_pos).length)
            self.slider_widget.set_distance_values(distance_values)
        else:
           self.slider_widget.remove_all_thumbs()
    
    # TODO: Move all the code below out of the class
    def create_single_loop_panel(self, context):
        panel = VLayoutPanel(context, 100, 100, (70, 300), 1, "Single")
        panel.bg_color = (0.8, 0.8, 0.8, 0.1)
        panel.visible = False
        ignore = {"use_multi_loop_offset", "loop_space_value",
                "insert_verts", "insert_on_selected_edges", "freeze_edge", "use_snap_points", "lock_snap_points", 
                "increase_loop_count", "decrease_loop_count", "insert_midpoint"}

        self.populate_panel(context, panel, ignore)
        return panel

    
    def create_multi_loop_panel(self, context):
        panel = VLayoutPanel(context, 100, 100, (70,100), 1, "Multi")
        panel.bg_color = (0.8, 0.8, 0.8, 0.1)
        panel.visible = False
        ignore = {"insert_verts", "insert_on_selected_edges", "freeze_edge", "use_snap_points", "lock_snap_points", 
                "increase_loop_count", "decrease_loop_count", "insert_midpoint"}

        self.populate_panel(context, panel, ignore)
        return panel
    
    def create_extras_panel(self, context):
        extras_panel = VLayoutPanel(context, 100, 100, (70,100), 1, None)
        extras_panel.bg_color = (0.8, 0.0, 0.0, 0.0)

        hotkey_only = {"increase_loop_count", "decrease_loop_count"}
        misc = {"Set Loop Count": "(1-9)", "Remove Loop": "(Ctrl+Shift)", "Slide Loop": "Alt" if not common.prefs().use_spacebar else "Spacebar"}
        ignore = {"use_even", "flipped", "mirrored", "perpendicular", "use_multi_loop_offset", "loop_space_value",
                "increase_loop_count", "decrease_loop_count", "insert_midpoint"}
        
        self.populate_panel(context, extras_panel, ignore, hotkey_only, misc)
        return extras_panel

    def populate_panel(self, context, panel, ignore, hotkey_only=None, misc=None):

        hotkey_only = {} if hotkey_only is None else hotkey_only
        misc = {} if misc is None else misc

        keymap = km_cache.get_keymap(self.bl_idname)
        for action, action_name in ui.get_ordered_fl_keymap_actions().items():
            key = keymap.get_mapping_from_action(action_name)
            hotkey = ui.append_modifier_keys(key[0].upper(), key[2], key[3], key[4])
            if action not in ignore:
                property_label = make_property_label(self, context, action_name, action, hotkey)
                panel.add_child_widget(action, property_label)
            
            elif action in hotkey_only:
                hotkey_label = make_hotkey_label(self, context, action_name, hotkey)
                panel.add_child_widget(action, hotkey_label)

        for action_name, hotkey in misc.items():
            hotkey_label = make_hotkey_label(self, context, action_name, hotkey)
            panel.add_child_widget(action_name, hotkey_label)
        
#  ["even", "flip", "mirrored", "midpoint", "perpendicular", "multi_loop_offset",
        # "scale", "insert_verts", "freeze_edge", "snap_points", "lock_snap_points", 
        # "increase_loop_count", "decrease_loop_count"]