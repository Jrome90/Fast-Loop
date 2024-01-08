from abc import ABCMeta
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fast_loop import FastLoopOperator

import bpy, bmesh

from ...utils.common import prefs
from ...utils.ops import (get_m_button_map as btn, options)

from ..fast_loop_actions import (DrawLoopsMixin, DrawDirectionArrowMixin, BaseAction)
from ..fast_loop_helpers import (set_mode, Mode)

from .remove_loop import RemoveLoopAction
from .right_click import RightClickAction
from .activate_edge_slide import EdgeSlideAction

from ..edge_ring import EdgeDataFactory
from ..edge_data import EdgeData

class InsertAction(DrawLoopsMixin, DrawDirectionArrowMixin, BaseAction, metaclass=ABCMeta):
    Mode = Mode.NONE
    def __init__(self, context) -> None:
        self.context: FastLoopOperator = context
    

    def enter(self):
        set_mode(self.Mode)


    def exit(self):
        pass


    def update(self):
        current_edge = self.context.current_edge
        if current_edge is None or not current_edge.is_valid or self.context.current_face_index is None:
            return
        self.context.scale = self.context.calculate_scale_value()
        self.context.is_single_edge = False
        data = EdgeDataFactory.create(current_edge, self.context)
        if data is not None:
            self.context.loop_data = data

            if self.context.update_loops():
                props = self.context.get_all_props_no_snap()
                self.context.edge_data = EdgeData(data, props)
                self.context.is_single_edge = self.context.loop_data.is_single_loop()
                self.context.update_arrows()
                return True

        return False
    

    def handle_input(self, bl_context, bl_event):
        handled = False
        event = bl_event

        if self.context.slider_widget.handle_event(event):
            return True

        if event.type in {'RIGHTMOUSE', 'LEFTMOUSE'}:
            if self.context.current_edge is not None and event.type in {btn('LEFTMOUSE')} and (event.value == 'CLICK' \
                # I cannot get the click event value when snap is enabled. I have to use press :/
            or (self.context.snap_enabled and event.value == 'PRESS')):
                if prefs().use_spacebar and event.alt:
                    return False
                
                if not self.context.is_snapping:
                    self.context.freeze_edge = False

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
                
                self.context.push_action(RightClickAction(self.context))
                handled = True
        
        if event.shift and event.ctrl:
            self.context.push_action(RemoveLoopAction(self.context))
            
            bl_context.area.tag_redraw()
            handled = True

        if not prefs().use_spacebar:

            if event.alt:
                self.context.push_action(EdgeSlideAction(self.context, False))   
                handled = True
        else:
            if event.type == 'SPACE' and event.value == 'PRESS':
                self.context.push_action(EdgeSlideAction(self.context, True))
                handled = True
            
        if event.type in {"P"} and event.value == 'PRESS':
            self.context.loop_position_override = not self.context.loop_position_override
            self.context.freeze_edge = self.context.loop_position_override
            if self.context.freeze_edge:
                self.context.frozen_edge = self.context.current_edge
                self.context.frozen_edge_index = self.context.current_edge_index
                self.context.frozen_face_index = self.context.current_face_index
            
            # if self.context.loop_position_override:
            #     self.context.slider_widget.is_static = False
            #     self.context.slider_widget.on_thumb_moved.connect(Slot(self.context.on_thumb_move))
            # else:
            #     self.context.slider_widget.on_thumb_moved.disconnect(self.context.on_thumb_move)
            #     self.context.slider_widget.is_static = True
            handled = True
         
        elif event.type in {"SEMI_COLON"} and event.value == 'PRESS':
            bpy.ops.ui.distance_display_settings_operator('INVOKE_DEFAULT')
        
        elif event.type in {"RIGHT_BRACKET"} and event.value == 'RELEASE':
            options().use_opposite_snap_dist = not options().use_opposite_snap_dist
            self.context.snap_context.force_display_update(self.context.active_object)
            handled = True

        if self.context.main_panel_hud.handle_event(bl_event):
            handled = True
      
        return handled
    

    def handle_modal_event(self, bl_context, modal_event, bl_event):
        handled = False

        if modal_event in {"Insert Verts"}:
            self.context.insert_verts = not self.context.insert_verts

            if self.context.insert_verts:
                bl_context.tool_settings.mesh_select_mode = (True, False, False)
                self.context.active_object.bm.select_mode = {'VERT'}
            else:
                bl_context.tool_settings.mesh_select_mode = (False, True, False)
                self.context.active_object.bm.select_mode = {'EDGE'}

            handled = True
        elif modal_event in {"Use Selected Edges"}:
            self.context.insert_on_selected_edges = not self.context.insert_on_selected_edges
            handled = True
        
        elif modal_event in {"Mirrored"}:
            self.context.mirrored = not self.context.mirrored
            handled = True

        elif modal_event in {"Even"}:
            self.context.use_even = not self.context.use_even
            handled = True

        elif modal_event in {"Flip"}:
            self.context.flipped = not self.context.flipped
            handled = True

        elif modal_event in {"Snap Points"}:
            self.context.use_snap_points = not self.context.use_snap_points
            handled = True

        elif modal_event in {"Lock Snap Points"}:
            self.context.lock_snap_points = not self.context.lock_snap_points
            handled = True

        elif modal_event in {"Perpendicular"}:
            self.context.perpendicular = not self.context.perpendicular
            handled = True
        
        elif modal_event in {"Freeze Edge"}:
            self.context.freeze_edge = not self.context.freeze_edge
            if self.context.freeze_edge:
                self.context.frozen_edge = self.context.current_edge
                self.context.frozen_edge_index = self.context.current_edge_index
                self.context.frozen_face_index = self.context.current_face_index

                handled = True
        
        elif modal_event in {"Insert Loop At Midpoint"}:
            if self.context.current_edge is not None and self.context.update_loops():
                self.context.force_offset_value = 0.5
                props = self.context.get_all_props_no_snap()
                self.context.edge_data = EdgeData(self.context.loop_data, props)
                self.context.create_geometry(select_new_edges=False)
                bpy.ops.ed.undo_push(message="Insert Loop At Center")
                handled = True
                
        return handled


    def draw_ui(self, bl_context):
        if self.context.area_invoked == bl_context.area:
            if self.context.slider_widget is not None:
                # Need to update the slider coords in case the area is resized
                self.context.slider_widget._update_slider_coords()
                self.context.slider_widget.draw()

            self.context.main_panel_hud.draw()

        if prefs().draw_distance_segment:
            DrawDirectionArrowMixin.draw_ui(self, bl_context)

    def draw_3d(self, bl_context):
        DrawLoopsMixin.draw_3d(self, bl_context)
        if prefs().draw_distance_segment:
            DrawDirectionArrowMixin.draw_3d(self, bl_context)

