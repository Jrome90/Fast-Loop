from __future__ import annotations
from typing import Dict, List
   
from math import isclose

import bpy, bmesh
from bmesh.types import BMEdge, BMVert
from mathutils import Vector

from .multi_object_edit import MultiObjectEditing
from .. import utils
from .. utils.observer import Subject
from .. utils.ops import get_m_button_map as btn, get_undo_keymapping, match_event_to_keymap
from .. utils.edge_slide import EdgeVertexSlideData, VertSlideType, calculate_edge_slide_directions
from .. snapping.snapping import SnapContext

from ..ui.widgets import (VLayoutPanel, VLayoutDragPanel, make_hotkey_label)


from enum import Enum
class Mode(Enum):
    EDGE_SLIDE = 1
    EDGE_CONSTRAINT = 2
    PASS_THROUGH = 3


class EdgeSlideOperator(bpy.types.Operator, Subject, MultiObjectEditing):
    bl_idname = 'fl.edge_slide'
    bl_label = 'edge slide'
    bl_options = {'REGISTER'}

    _listeners  = {}

    restricted: bpy.props.BoolProperty(
        name='restricted',
        description='Do not change. This is meant to be hidden',
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'}
    )

    invoked_by_fla: bpy.props.BoolProperty(
        name='Invoked by Fast Loop Advanced',
    _listeners  = {}
    )
    restricted: bpy.props.BoolProperty(
        name='restricted',
        description='Do not change. This is meant to be hidden',
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'}
    )  

    invoked_by_fla: bpy.props.BoolProperty(
        name='Invoked by Fast Loop Advanced',
        description='Do not change. This is meant to be hidden',
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'}
    )  

    mode = Mode.EDGE_SLIDE
    is_sliding = False
    slide_value = 0.0
    active_object = None
    initial_bm = None
    # bm: BMesh = None
    # bm_store: BMesh = None
    nearest_vert = None
    nearest_vert_co = None
    nearest_vert_co_2d = None

    # world_mat: Matrix = None
    # world_inv: Matrix = None

    draw_handler_2d = None

    # For Debug
    points_2d = []
    points_3d = []

    slide_verts: Dict[int, EdgeVertexSlideData] = {}
    ss_slide_directions: List[Vector] = []

    # Edge Clone
    split_edges = set()
    loop_vert_pairs = {}
    edge_clones = {}
    loops: Dict[BMVert, BMEdge] = {}
    cloned_side = 0
    cloned = False
    clone_edge = False

    snap_context = None
    current_edge = None
    current_edge_index = None

    selected_edges = []

    main_panel_hud = None
    edge_slide_hud = None


    @classmethod
    def poll(cls, context):
       return (context.space_data.type == 'VIEW_3D'
                and context.active_object
                and context.active_object.type == "MESH"
                and context.active_object.mode == 'EDIT'                
              )


    @classmethod
    def init_setup(cls, context):
        """ This method is used to revert the mesh when cloning edges.
        """
        context.active_object.update_from_editmode()
        mesh = context.active_object.data
        cls.initial_bm = bmesh.new()
        cls.initial_bm.from_mesh(mesh)


    def setup(self, context):
        self.add_selected_editable_objects(context)
        #TODO Sometimes the index is out of range. Need to find out why
        if not list(self.selected_editable_objects.values()):
            return {"CANCELLED"}
        
        self.active_object = list(self.selected_editable_objects.values())[0]
        self.ensure_bmesh_(self.active_object)
        # self.active_object = context.active_object
        # self.world_mat = context.object.matrix_world.normalized()
        # self.world_inv = context.object.matrix_world.inverted_safe()

        self.slide_verts.clear()
        self.loop_vert_pairs.clear()
        self.edge_clones.clear()
        self.split_edges.clear()

        self.mode = Mode.EDGE_SLIDE
        self.is_sliding = False
        # self.ensure_bmesh()
        utils.mesh.ensure(self.active_object.bm)
        
        self.active_object.bm.select_mode = {'EDGE'}
        self.active_object.bm.select_flush_mode()

        main_panel_hud_x = utils.common.prefs().operator_panel_x
        main_panel_hud_y = utils.common.prefs().operator_panel_y

        self.main_panel_hud = VLayoutDragPanel(context, 200, 100, (main_panel_hud_x, main_panel_hud_y), 1, "Edge Slide")
        self.main_panel_hud.bg_color = (0.8, 0.8, 0.8, 0.0)
        self.main_panel_hud.ignore_child_widget_focus = True

        self.edge_slide_hud =  self.create_edge_slide_panel(context)
        self.edge_slide_hud.bg_color = (0.8, 0.8, 0.8, 0.0)

        self.main_panel_hud.add_child_widget("EDGE_SLIDE", self.edge_slide_hud)

        self.main_panel_hud.set_location(main_panel_hud_x,main_panel_hud_y)
        self.edge_slide_hud.set_location(main_panel_hud_x,main_panel_hud_y)

        

    def invoke(self, context, event):
        # self.report({'INFO'}, 'Edge Slide Started')
        # self.set_status(context)
        # self.init_setup(context)
        self.setup(context)
        self.draw_handler_2d = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, (context, ), 'WINDOW', 'POST_PIXEL')
        self.draw_handler_3d = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_3d, (context, ), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self)
        bpy.context.window.cursor_modal_set("CROSSHAIR")
        return {'RUNNING_MODAL'}
    

    def cancel(self, context):
        self.report({'INFO'}, 'Cancelled')
        self.finished(context)
        return {'CANCELLED'}


    def finished(self, context):
        # super().finished(context)
        # self.clear_draw()

        SnapContext.remove(self)

        bpy.context.window.cursor_modal_restore()
        context.workspace.status_text_set(None)

        context.area.tag_redraw()
        self.report({'INFO'}, 'Edge Slide Finished')

        if getattr(self, 'draw_handler_2d', None):
            self.draw_handler_2d = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler_2d, 'WINDOW')

        if getattr(self, 'draw_handler_3d', None):
            self.draw_handler_3d = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler_3d, 'WINDOW')
        
        try:
            self.notify_listeners()
        except:
            pass
        finally:
            return {'FINISHED'}

    
    def revert_bmesh(self, context):
        # Restore the initial state of the mesh data
        mesh = self.active_object.data
        bpy.ops.object.mode_set(mode='OBJECT')
        self.initial_bm.to_mesh(mesh)
        bpy.ops.object.mode_set(mode='EDIT')

        self.active_object.bm = bmesh.from_edit_mesh(mesh)

    
    def switch_modes(self, context, event):
        # super().finished(context)
        # self.clear_draw()
        bpy.context.window.cursor_modal_restore()
        # context.workspace.status_text_set(None)

        context.area.tag_redraw()

        if getattr(self, 'draw_handler_2d', None):
            self.draw_handler_2d = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler_2d, 'WINDOW')

        if getattr(self, 'draw_handler_3d', None):
            self.draw_handler_3d = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler_3d, 'WINDOW')

        self.notify_listeners(message="switch_modes", data=event)
        return {'FINISHED'}
    

    # def clear_draw(self):
    #     # self.axis_draw_points.clear()
    #     # self.axis_draw_colors.clear()
    #     self.slide_edge_draw_lines.clear()


    @utils.safety.decorator
    def modal(self, context, event):
        
        if context.mode != 'EDIT_MESH':
                return self.cancel(context)

        # if not self.restricted and event.ctrl and event.type == 'Z' and event.value == 'PRESS':
        #     if self.is_sliding and self.mode == Mode.EDGE_CONSTRAINT:
        #         self.is_sliding = False
        #         self.mode = Mode.EDGE_SLIDE
                
        #     return {'PASS_THROUGH'}

        # self.set_status(context)
        if utils.common.prefs().use_spacebar and event.alt and self.invoked_by_fla:
            return {'PASS_THROUGH'}


        handled = False
        if not self.restricted and not event.ctrl and event.type in {'S', 'D'} and event.value == 'PRESS':
            if event.type in {'S'}:
                if not self.mode == Mode.PASS_THROUGH:
                    self.mode = Mode.PASS_THROUGH
                    self.is_sliding = False
                    context.area.tag_redraw()
                    return {'RUNNING_MODAL'}
                else:
                    self.mode = Mode.EDGE_SLIDE

                handled = True

            # TODO: DISABLED until updated to work with mulitple object editing
            # elif event.type in {'D'}:
            #     self.clone_edge = not self.clone_edge
            #     self.edge_slide_hud.update_widget("clone_edge", self.clone_edge)
            #     self.edge_slide_hud.layout_widgets()
            #     handled = True

        if self.main_panel_hud.handle_event(event):
            return {'RUNNING_MODAL'}

        if match_event_to_keymap(event, get_undo_keymapping()):
            bpy.ops.ed.undo()
            # self.init_setup(context)
            handled = True
            
        if self.mode == Mode.PASS_THROUGH:
            return {'PASS_THROUGH'}

        if not utils.common.prefs().use_spacebar:
            if not event.alt and self.restricted:
                return self.finished(context)
        else:
            if event.type == 'SPACE' and event.value == 'PRESS':
                return self.finished(context)
                
        if not self.restricted and event.type == btn('RIGHTMOUSE') and event.value == 'PRESS':
            return self.finished(context)


        if event.type in {'LEFTMOUSE', 'RIGHTMOUSE', 'MOUSEMOVE'}:
            element_index = None
            if not self.is_sliding:
                mouse_coords = (event.mouse_region_x, event.mouse_region_y)
                mouse_coords_win = (event.mouse_x, event.mouse_y)

                if self.snap_context is None:
                    self.snap_context: SnapContext = SnapContext.get(context, context.evaluated_depsgraph_get(), self, context.space_data, context.region,)
                    for editable_object_data in self.selected_editable_objects.values():
                        self.snap_context.add_object(editable_object_data.get_bl_object)


                if self.snap_context is not None:
                    snap_results = self.snap_context.do_snap_objects([obj.get_bl_object for obj in self.selected_editable_objects.values()], mouse_coords, mouse_coords_win)
                    
                    if snap_results is not None:
                        self.current_face_index, element_index, _, bl_object = snap_results
                    
                        self.active_object = self.selected_editable_objects[bl_object.name]
                        self.ensure_bmesh_(self.active_object)
                        self.current_edge = self.active_object.bm.edges[element_index]
                        self.current_edge_index = element_index
                    else:
                        self.current_edge = None

            if not self.restricted:
                if element_index is None and event.type == btn('LEFTMOUSE') and not self.is_sliding:
                    return {'PASS_THROUGH'}
                elif (event.shift or event.ctrl or event.alt) and not self.is_sliding :
                    return {'PASS_THROUGH'}

            if  event.type == btn('LEFTMOUSE') and event.value == 'PRESS' and not self.is_sliding:
                mouse_coords = (event.mouse_region_x, event.mouse_region_y)
                if element_index is not None:
                    self.selected_edges = [edge.index for edge in self.active_object.bm.edges if edge.select]
                    if not self.selected_edges:
                        for edge in utils.mesh.bmesh_edge_loop_walker(self.current_edge):
                            edge.select = True
                            self.selected_edges.append(edge.index)
                            self.active_object.bm.select_flush(True)
                    else:
                        if not self.current_edge.select:
                            for edge in self.selected_edges:
                                bm_edge = self.active_object.bm.edges[edge]
                                bm_edge.select = False

                            self.selected_edges.clear()
                            for edge in utils.mesh.bmesh_edge_loop_walker(self.current_edge):
                                edge.select = True
                                self.selected_edges.append(edge.index)

                            self.active_object.bm.select_flush(True)

                    edge = self.current_edge
                    vert = self.get_nearest_vert_for_edge(mouse_coords, edge)
                    if vert is not None and edge is not None:

                        nearest_vert_co_world = self.world_mat @ vert.co
                        self.nearest_vert_co_2d = utils.math.location_3d_to_2d(nearest_vert_co_world)
                        self.nearest_vert = vert.index
                        
                        self.slide_verts, self.loops = calculate_edge_slide_directions(self.active_object.bm, edge, self.selected_edges, return_edges=True)
                        self.is_sliding = True
                    else:
                        self.report({'INFO'}, 'At least one edge must be highlighted before using.')
                    return {'RUNNING_MODAL'}
                handled = True

            if event.type == 'MOUSEMOVE' and self.is_sliding:

                if self.is_sliding:
                    mouse_coords = (event.mouse_region_x, event.mouse_region_y)
                    if self.mode == Mode.EDGE_SLIDE:
                        # self.revert_bmesh(context)
                        self.ensure_bmesh_(self.active_object)
                        utils.mesh.ensure(self.active_object.bm)
                        even = event.ctrl and not event.shift
                        keep_shape = event.shift and not event.ctrl
                        self.edge_slide(context, mouse_coords, even, keep_shape)
                           
                    handled = True

            if event.type == btn('LEFTMOUSE') and event.value == 'RELEASE' and self.is_sliding:

                utils.mesh.ensure(self.active_object.bm)
                mesh = self.active_object.data
                bmesh.update_edit_mesh(mesh)

                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.mode_set(mode='EDIT')
                
                self.slide_verts.clear()
                self.loop_vert_pairs.clear()
               
                self.is_sliding = False

                self.edge_clones.clear()
                self.cloned =False

                # Deselect the edges before we save a copy of the bmesh
                
                # for index in self.selected_edges:
                #     self.bm.edges[index].select = False

                #TODO: Commented out because cloning doesnt work yet see above.
                # self.init_setup(context) #Clone
                #------------------------------------------

                # utils.mesh.ensure(self.bm)
                # self.bm.edges.index_update()

                # for index in self.selected_edges:
                #     self.bm.edges[index].select = True

                # if not self.restricted:
                self.mode = Mode.EDGE_SLIDE
                bpy.ops.ed.undo_push()

        if self.invoked_by_fla:
            if event.type in {'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE'} and event.value == 'PRESS':
                return self.switch_modes(context, event)

        context.area.tag_redraw()
        if handled:
            return {'RUNNING_MODAL'}
        else:
            return {'PASS_THROUGH'}

    
    def draw_callback_3d(self, context):

        if self.points_3d:
            utils.draw_3d.draw_points(self.points_3d, size=5)
        self.points_3d.clear()

        if self.current_edge is not None and self.current_edge.is_valid:
            color = (1.0,0.0,1.0, 0.5)#utils.common.prefs().loop_color
            line_width = 1.0 #utils.common.prefs().line_width
            
            utils.draw_3d.draw_line([self.world_mat @ vert.co for vert in self.current_edge.verts], color, line_width)


    def draw_callback_px(self, context):
        if self.points_2d:
            utils.draw_2d.draw_points(self.points_2d)
        self.points_2d.clear()

        if  self.mode == Mode.EDGE_SLIDE and self.is_sliding and self.nearest_vert_co_2d is not None:
            utils.draw_2d.draw_circle((self.nearest_vert_co_2d), 2.5)

        elif self.mode == Mode.PASS_THROUGH:
            utils.draw_2d.draw_region_border(context)
        
        if self.main_panel_hud is not None:
            self.main_panel_hud.draw()
    
    
    def get_nearest_vert_for_edge(self, mouse_coords, edge):
        mouse_co: Vector = Vector(mouse_coords)
        min_dist_sq = float('INF')
        visited_verts = set()
        nearest_vert = None

        if edge is not None and edge.select:
            for vert in [edge.verts[0], edge.other_vert(edge.verts[0])]:
                if vert.index not in visited_verts:
                    vert_co_world = self.world_mat @ vert.co
                    vert_2d = utils.math.location_3d_to_2d(vert_co_world)
                    if vert_2d is not None:
                        dist_sq = (mouse_co - vert_2d).length_squared
                        if dist_sq < min_dist_sq:
                            nearest_vert = vert
                            min_dist_sq = dist_sq

                    visited_verts.add(vert.index)

        if nearest_vert is not None:
            return nearest_vert

        return None


    # TODO: Use a better method to do this.
    def get_nearest_vert_and_edge(self, mouse_coords):
        bm = self.ensure_bmesh_(self.active_object)
        mouse_co: Vector = Vector(mouse_coords)
        min_dist_sq = float('INF')
        min_angle = float('INF')
        visited_verts = set()
        nearest_vert = None
        nearest_edge = None
        nearest_vert_2d = None
        fallback_edge = None
        for edge in self.active_object.bm.edges:
            if edge.select:
                for vert in [edge.verts[0], edge.other_vert(edge.verts[0])]:
                    if vert.index not in visited_verts:
                        vert_co_world = self.world_mat @ vert.co
                        vert_2d = utils.math.location_3d_to_2d(vert_co_world)
                        if vert_2d is not None:
                            dist_sq = (mouse_co - vert_2d).length_squared
                            if dist_sq < min_dist_sq:
                                nearest_vert = vert
                                nearest_vert_2d = vert_2d
                                min_dist_sq = dist_sq

                        visited_verts.add(vert.index)

        if nearest_vert is not None:
            for vert_edge in nearest_vert.link_edges:
                if vert_edge.select:
                    other_vert_co_2d = utils.math.location_3d_to_2d(self.world_mat @ vert_edge.other_vert(nearest_vert).co)
                    if other_vert_co_2d is not None:
                        edge_2d = (other_vert_co_2d - nearest_vert_2d)
                        if not isclose(edge_2d.length, 0.0):
                            angle = (nearest_vert_2d - mouse_co).angle(edge_2d)
                    if other_vert_co_2d is not None:
                        edge_2d = (other_vert_co_2d - nearest_vert_2d)
                        if not isclose(edge_2d.length, 0.0):
                            angle = (nearest_vert_2d - mouse_co).angle(edge_2d)

                            if angle < min_angle:
                                nearest_edge = vert_edge
                                min_angle = angle
                        else:
                            fallback_edge = vert_edge
        

        if nearest_vert is not None and nearest_edge is not None:
            return nearest_vert, nearest_edge

        if nearest_vert is not None and nearest_edge is None and fallback_edge is not None:
            return nearest_vert, fallback_edge

        return None, None

    def edge_slide(self, context, mouse_coords, even, keep_shape):
        face_slide = False
        mouse_co = Vector(mouse_coords)
        side = 0
        max_cos_theta = float('-inf')
        
        nearest_vert_slide_data = self.slide_verts.get(self.nearest_vert, None)
        if nearest_vert_slide_data is None:
            return

        fac = 0.0
        slide_point = None
        slide_vec = None
        vert_orig_co_world = self.world_mat @ nearest_vert_slide_data.vert_orig_co
        if nearest_vert_slide_data is not None:
            for i, slide_type in enumerate(nearest_vert_slide_data.slide_type):
                if slide_type is not None:
                    if self.clone_edge:
                        if slide_type == VertSlideType.FACE_NGON or slide_type == VertSlideType.FACE_INSET or slide_type == VertSlideType.FACE_OUTSET:
                            return

                    v = nearest_vert_slide_data.vert_side[i]
                    if v is not None:
                        vert_other = self.active_object.bm.verts[v]
                        vert_other_co_world = self.world_mat @ vert_other.co
                        slide_v = vert_other_co_world if not \
                        (slide_type == VertSlideType.FACE_NGON or slide_type == VertSlideType.FACE_INSET or slide_type == VertSlideType.FACE_OUTSET) \
                        else vert_orig_co_world + nearest_vert_slide_data.dir_side[i] * 100
                      
                        other, isect_point = utils.raycast.get_mouse_line_isect(context, mouse_co, vert_orig_co_world, slide_v)
                        if other is not None:
                            factor = utils.math.inv_lerp(vert_orig_co_world, slide_v, other)
                                
                            slide_dir_vec = ((vert_orig_co_world + slide_v) - vert_orig_co_world).normalized()
                            test_dir_vec = (isect_point - vert_orig_co_world).normalized()
                            cos_theta = slide_dir_vec.dot(test_dir_vec)
                            if cos_theta > max_cos_theta and 1.0 >= factor >= 0.0:
                                max_cos_theta = cos_theta
                                
                                slide_vec = slide_v
                                side = i
                                slide_point = other
                                fac = factor

        if slide_vec is not None:
            if self.clone_edge:
                if not self.cloned:
                    self.cloned_side = side
                    loop_a, loop_b, _, = utils.mesh.clone_edges(self.bm, side, self.slide_verts, self.loops, True) #Clone
                    self.loop_vert_pairs.update({vert_a: vert_b for (vert_a, vert_b) in zip(loop_a, loop_b)}) #Clone
                    self.cloned = True
                else:
                    if self.cloned_side != side:
                        self.cloned_side = side
                        self.revert_bmesh(context)
                        self.bm.edges.ensure_lookup_table()
                        current_edge = self.bm.edges[self.current_edge_index]
                        
                        for index in self.selected_edges:
                            self.bm.edges[index].select = True

                        self.slide_verts, self.loops = calculate_edge_slide_directions(self.bm, current_edge, self.selected_edges, return_edges=True)
                        loop_a, loop_b, _ = utils.mesh.clone_edges(self.bm, side, self.slide_verts, self.loops, True) #Clone
                        self.loop_vert_pairs.update({vert_a: vert_b for (vert_a, vert_b) in zip(loop_a, loop_b)}) #Clone

            edge_len = nearest_vert_slide_data.edge_len[side]

            if slide_point is not None:
                
                d = (slide_point - vert_orig_co_world).length
                for data in self.slide_verts.values():
                    if data is None:
                        continue

                    vert_index = data.vert # if not clone edge

                    if self.clone_edge:
                        if data.slide_type[side] == VertSlideType.FACE_INSET or data.slide_type[side] == VertSlideType.FACE_OUTSET or data.slide_type[side] == VertSlideType.FACE_NGON:
                            continue

                        if data.vert not in self.loop_vert_pairs: #Clone
                            continue #Clone
                    
                        vert_index = self.loop_vert_pairs[data.vert] #Clone
                    try:
                        vert = self.active_object.bm.verts[vert_index] 
                    except IndexError:
                        continue
                    o_co = data.vert_orig_co # world_mat
                    if data.dir_side[side] is None:
                        continue
                   
                    face_slide = data.slide_type[side] == VertSlideType.FACE_INSET or data.slide_type[side] == VertSlideType.FACE_OUTSET or data.slide_type[side] == VertSlideType.FACE_NGON

                    vec_len = data.edge_len[side]
                    dir_vec_norm = data.dir_side[side]
                    vert_side_index = data.vert_side[side]
                    vert_other_side = self.active_object.bm.verts[vert_side_index]
                    dir = vert_other_side.co # world_mat
                    if face_slide or keep_shape:
                     
                        dir = o_co + (dir_vec_norm * d)
                        #dir =  o_co + (((dir_vec_norm * d))/ edge_len) previous

                    if even:
                        l2 = utils.math.remap(0.0, vec_len, 0.0, edge_len, 1)
                        shifted_point = dir.lerp(o_co, l2)
                        vert.co = shifted_point + (dir-o_co).normalized() * d

                    elif keep_shape:
                        if not face_slide:
                            vert.co = o_co + (dir_vec_norm.normalized() * d)
                            # offset = o_co + (dir - o_co).normalized() * d
                            # self.points_3d.append(offset)
                            # plane_isect = intersect_line_plane(o_co, dir, offset, dir_vec_norm)
                            # if plane_isect is not None:
                            #     vert.co = plane_isect
                        else:
                            vert.co = dir
                        
                    else:
                        if not face_slide:
                            if not self.clone_edge:
                                # factor = utils.math.inv_lerp(o_co, dir, slide_point)
                                vert.co = o_co.lerp(dir, fac) # Previous prolly for better results when sliding actual percentage
                            else:
                                vert.co = o_co + (dir_vec_norm.normalized() * d) # better results when cloning
                        else:
                            # if not self.clone_edge:
                            # vert.co = o_co.lerp(o_co + dir_vec_norm, 0.3)
                            # else:
                            vert.co = dir

        self.active_object.bm.faces.index_update()
        utils.mesh.bmesh_loop_index_update(self.active_object.bm)
        self.active_object.bm.select_mode = {'EDGE'}
        self.active_object.bm.select_flush_mode()

        mesh = self.active_object.data
        bmesh.update_edit_mesh(mesh)
    
    @staticmethod
    def ensure_bmesh_(edit_object_data):
        obj = edit_object_data.get_bl_object
        bm = edit_object_data.bm
        if bm is None or not bm.is_valid:
            obj.update_from_editmode()
            mesh = obj.data
            edit_object_data.bm = bmesh.from_edit_mesh(mesh)
        return edit_object_data.bm


    def create_edge_slide_panel(self, context):
        panel = VLayoutPanel(context, 100, 100, (70,300), 1, "Edge Slide")
        panel.bg_color = (0.8, 0.8, 0.8, 0.1)
        panel.visible = True

        hotkeys = {"Even": "Hold Ctrl", "Keep Shape ": "Hold Shift"}

        self.populate_panel(context, panel, hotkeys)

        return panel

    
    def populate_panel(self, context, panel, hotkeys):

        # prop_label = make_property_label(self, context, "Clone", "clone_edge", "D")
        # panel.add_child_widget("clone_edge", prop_label)

        for action_name, hotkey in hotkeys.items():
            hotkey_label = make_hotkey_label(self, context, action_name, hotkey)
            panel.add_child_widget(action_name, hotkey_label)
