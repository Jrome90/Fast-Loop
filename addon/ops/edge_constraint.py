from typing import *
from dataclasses import dataclass, field

import bpy, bmesh
from bmesh.types import *
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_point_line, intersect_line_plane

from .. ui.gizmos.gizmo_snapping import RP_GGT_SnapGizmoGroup
from .. props import addon
from .. import utils
from .. utils import draw_3d, draw_2d
from .. utils.ops import get_m_button_map as btn, match_event_to_keymap, get_undo_keymapping


from enum import Enum
class Mode(Enum):
    EDGE_SLIDE = 1
    EDGE_CONSTRAINT = 2
    PASS_THROUGH = 3


@dataclass
class EdgeVertexSlideData():
    
    vert: BMVert = None
    vert_orig_co: Vector = None
    vert_side: List[BMVert] = field(default_factory=lambda: [None, None])
    # Store a copy of other verts co vector here
    dir_side: List[Vector] =  field(default_factory=lambda: [None, None])

    edge_len: List[float] = field(default_factory=lambda: [None, None])    

    def __repr__(self) -> str:
        vert_side_a = self.vert_side[0].index if self.vert_side[0] is not None else None
        vert_side_b = self.vert_side[1].index if self.vert_side[1] is not None else None
        string = f"vert_side: a {vert_side_a}; b {vert_side_b} \n"
        string += f"dir_side: a {self.dir_side[0]}; b {self.dir_side[1]} \n"
        return string


class EdgeConstraintTranslationOperator(bpy.types.Operator):
    bl_idname = 'fl.edge_contraint_translation'
    bl_label = 'edge contrained translation'
    bl_options = {'REGISTER', 'UNDO'}

    active_axis = None
    axis_vec = None
    constrained_to_bounds = True
    constrained_to_bounds = True
    axis_draw_points = []
    axis_draw_colors = []
    slide_edge_draw_lines = []

    # mode = Mode.EDGE_SLIDE
    is_sliding = False
    snap_enabled = False
    snap_location = None
    #slide_value = 0.0
    bm: BMesh = None
    nearest_vert_2d = None
    nearest_vert_co_2d = None
    nearest_vert_3d = None
    nearest_vert_co_3d = None
    snap_point = None

    world_mat: Matrix = None
    world_inv: Matrix = None
    draw_handler_3d = None
    draw_handler_2d = None


    # For Debug
    # points_2d = []
    points_3d = []

    slide_verts: Dict[int ,EdgeVertexSlideData] = {}
    # ss_slide_directions: List[Vector] = []

    @classmethod
    def poll(cls, context):
       return (context.space_data.type == 'VIEW_3D'
                and context.active_object
                and context.active_object.type == "MESH"
                and context.active_object.mode == 'EDIT'                
              )
    
    def setup(self, context):
        self.world_mat = context.object.matrix_world.normalized()
        self.world_inv = context.object.matrix_world.inverted_safe()
        self.slide_verts.clear()
        self.mode = Mode.EDGE_SLIDE
        self.is_sliding = False
        self.snap_location = None
        self.ensure_bmesh()
        utils.mesh.ensure(self.bm)
        
        self.bm.select_mode = {'EDGE'}
        self.bm.select_flush_mode()

        addon.FL_Options.register_listener(self, self.event_raised)

        # For blender 4.0
        context.tool_settings.snap_elements_tool = 'DEFAULT'

    def invoke(self, context, event):
        # self.set_status(context)
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
        self.clear_draw_2d()

        if self.snap_enabled:
            self.disable_snapping(context)
            
        bpy.context.window.cursor_modal_restore()
        # context.workspace.status_text_set(None)

        context.area.tag_redraw()
        #self.report({'INFO'}, 'Edge Slide Finished')

        if getattr(self, 'draw_handler_2d', None):
            self.draw_handler_2d = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler_2d, 'WINDOW')

        if getattr(self, 'draw_handler_3d', None):
            self.draw_handler_3d = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler_3d, 'WINDOW')

        # self.notify_listeners()
        return {'FINISHED'}

    def clear_draw_2d(self):
        self.axis_draw_points.clear()
        self.axis_draw_colors.clear()
        self.slide_edge_draw_lines.clear()


    def draw_callback_3d(self, context):
        if self.slide_edge_draw_lines:
            for line in self.slide_edge_draw_lines:
                draw_3d.draw_line(line, line_width=1)

        if self.points_3d:
            draw_3d.draw_points(self.points_3d, size=3)
            self.points_3d.clear()

            
    def draw_callback_px(self, context):
        if self.nearest_vert_3d is not None and not self.is_sliding:
            self.clear_draw_2d()
            self.calculate_axis_draw_points(context, self.nearest_vert_3d, self.world_mat)

            if self.axis_draw_points:
                for points, color in zip(self.axis_draw_points, self.axis_draw_colors):
                    draw_2d.draw_line(points, line_color=color, line_width=1)

    
    def event_raised(self, event, value, context=None):
        if event == "snap_gizmo_update":
            self.snap_location = None
            if value is not None:
                self.snap_location = value
                # self.do_snap(context, value)
            else:
                self.snap_point = None


    def modal(self, context, event):
        if context.mode != 'EDIT_MESH':
                return self.cancel(context)

        if match_event_to_keymap(event, get_undo_keymapping()):
            if self.is_sliding:
                self.is_sliding = False
            self.nearest_vert_3d = None
            # self.nearest_vert_2d = None
                
            return {'PASS_THROUGH'}
        
        handled = False
        # if not self.is_sliding:
        #     bm = self.ensure_bmesh()
        #     active_vert = utils.mesh.get_active_vert(self.bm)
        #     if active_vert is not None:
        #         self.nearest_vert = active_vert
        #         self.nearest_vert_co = active_vert.co.copy()
        #         self.clear_draw()

        #         self.calculate_axis_draw_points(context, active_vert, self.world_mat)

        if self.is_sliding and event.ctrl and event.value == 'PRESS' and not self.snap_enabled:
            self.snap_enabled = not self.snap_enabled
            if self.snap_enabled:
                context.window_manager.gizmo_group_type_ensure(RP_GGT_SnapGizmoGroup.bl_idname)
                # bpy.context.scene.tool_settings.use_snap = True                  
                handled = True
        elif self.is_sliding and not event.ctrl and self.snap_enabled:
            self.disable_snapping(context)

        
        if not event.ctrl and event.type in {'X', 'Y', 'Z'} and event.value == 'PRESS':

            if not event.ctrl and get_valid_orientation() is not None and event.value == 'PRESS' :
                bm = self.ensure_bmesh()

                mouse_coords = (event.mouse_region_x, event.mouse_region_y)
                selected_verts = [vert for vert in bm.verts if vert.select]
                
                vert = self.get_nearest_vert_2d(selected_verts, mouse_coords)
                if vert is not None:
                    self.nearest_vert_3d = vert
                    self.nearest_vert_co_3d = vert.co.copy()
                    self.clear_draw_2d()
                else:
                    self.report({'INFO'}, 'Please select an edge before using.')
                    return {'RUNNING_MODAL'}

                # if not self.is_sliding:
                
                self.active_axis = event.type
                self.axis_vec = self.get_axis(event.type, self.world_mat)
                self.calculate_axis_draw_points(context, vert, self.world_mat) #, self.active_axis)
                self.slide_verts = self.get_slide_edges(selected_verts, self.axis_vec, self.world_mat)
                self.slide_edge_draw_lines =  self.calculate_slide_draw_lines(vert, self.slide_verts, self.world_mat)

                self.is_sliding = True
                self.mode = Mode.EDGE_CONSTRAINT
                bpy.ops.ed.undo_push()

                # elif self.is_sliding and self.mode == Mode.EDGE_CONSTRAINT:
                #     self.is_sliding = False

                handled = True
        # elif self.is_sliding and event.type in {'S'} and event.value == 'PRESS':
        #     self.snap_enabled = not self.snap_enabled

        #     if self.snap_enabled:
        #         context.window_manager.gizmo_group_type_ensure(RP_GGT_SnapGizmoGroup.bl_idname)
        #         bpy.context.scene.tool_settings.use_snap = True                    
        #         handled = True
        #     else:
        #         self.disable_snapping(context)
        #         handled = True

        elif event.type in {'LEFTMOUSE', 'RIGHTMOUSE', 'MOUSEMOVE'} and not self.snap_enabled:
            if event.type == btn('LEFTMOUSE') and event.value == 'PRESS' and self.is_sliding:
                self.slide_verts.clear()
                self.ensure_bmesh()
                utils.mesh.ensure(self.bm)
                self.is_sliding = False
                self.points_2d = None
                self.clear_draw_2d()
                handled = True


            # elif event.type == btn('LEFTMOUSE') and event.value == 'RELEASE' and not self.is_sliding:
                # bm = self.ensure_bmesh()

                # mouse_coords = (event.mouse_region_x, event.mouse_region_y)
                # # selected_verts = [vert for vert in bm.verts if vert.select]
                
                # # vert = self.get_nearest_vert(selected_verts, mouse_coords)
                # active_vert = utils.mesh.get_active_vert(self.bm)
                # if active_vert is not None:
                #     self.nearest_vert = active_vert
                #     self.nearest_vert_co = active_vert.co.copy()
                #     self.clear_draw()

                # # else:
                # #     self.report({'INFO'}, 'Please select an edge before using.')
                # #     return {'RUNNING_MODAL'}

                # # if not self.is_sliding:
                #     self.calculate_axis_draw_points(context, active_vert, self.world_mat)

            elif event.type == btn('RIGHTMOUSE') and event.value == 'PRESS':
                return self.finished(context)

            elif event.type == 'MOUSEMOVE' and self.is_sliding: #and not self.snap_enabled:
                # print(f"Event Type: {event.type}  Event Value: {event.value}")

                if self.is_sliding and not self.snap_enabled:
                    mouse_coords = (event.mouse_region_x, event.mouse_region_y)
                    self.edge_constraint_slide(context, mouse_coords, self.axis_vec)

                # if self.snap_enabled:
                #     self.do_snap(context, self.snap_location)


            elif event.type == 'MOUSEMOVE' and not self.is_sliding:
                bm = self.ensure_bmesh()

                mouse_coords = (event.mouse_region_x, event.mouse_region_y)
                selected_verts = [vert for vert in bm.verts if vert.select]
                
                vert = self.get_nearest_vert_2d(selected_verts, mouse_coords)
                if vert is not None:
                    self.nearest_vert_3d = vert
                    self.nearest_vert_co_3d = vert.co.copy()
                    # self.clear_draw()

                    # else:
                    #     self.report({'INFO'}, 'Please select an edge before using.')
                    #     return {'RUNNING_MODAL'}

                    # if not self.is_sliding:
                    # self.calculate_axis_draw_points(context, vert, self.world_mat)

                # handled = True
        
        elif event.type == btn('LEFTMOUSE') and event.value == 'PRESS' and self.snap_enabled:
            self.disable_snapping(context)
            self.slide_verts.clear()
            # self.ensure_bmesh()
            # utils.mesh.ensure(self.bm)
            self.is_sliding = False
            self.points_2d = None
            self.clear_draw_2d()
            handled = True

        # if self.is_sliding and event.type in {'S'} and not self.snap_enabled and event.value == 'PRESS':
        #         self.snap_enabled = True
        #         context.window_manager.gizmo_group_type_ensure(RP_GGT_SnapGizmoGroup.bl_idname)
        #         bpy.context.scene.tool_settings.use_snap = True                    
        #         handled = True

        elif self.is_sliding and self.snap_enabled and self.snap_location is not None:
           self.do_snap(context, self.snap_location)

        # if self.is_sliding and not event.ctrl and event.value == 'RELEASE' and self.snap_enabled:
        #     handled = True
        #     self.disable_snapping(context)

        if self.is_sliding and event.shift:
            self.constrained_to_bounds = False
            handled = True
        elif self.is_sliding and not event.shift:
            self.constrained_to_bounds = True
        
        context.area.tag_redraw()
        if handled:
            return {'RUNNING_MODAL'}
        else:
            return {'PASS_THROUGH'}

    def disable_snapping(self, context):
        bpy.context.scene.tool_settings.use_snap = False
        context.window_manager.gizmo_group_type_unlink_delayed(RP_GGT_SnapGizmoGroup.bl_idname)
        self.snap_enabled = False


    def calculate_axis_draw_points(self, context, nearest_vert, world_mat, current_axis=None):
        self.axis_draw_points.clear()
        axis_color = {"X": [1, 0, 0, 1], "Y": [0, 1, 0, 1], "Z":[0, 0, 1, 1]}
        for axis, color in axis_color.items():
            # Multiply by 0.001 to fix an issue caused when the vector is too far out when put into screen space.
            # Not sure how to handle this properly yet.
            axis_vec = self.get_axis(axis, world_mat)
            if axis_vec is not None:
                axis_vec = axis_vec * 0.001
                p1 = utils.math.location_3d_to_2d(world_mat @ nearest_vert.co)
                p2 = utils.math.location_3d_to_2d(world_mat @ nearest_vert.co + axis_vec)
                size_px = 50 * utils.ui.get_ui_scale()
                
                axis_2d = (p2-p1)
                axis_2d.normalize()
                axis_2d *= size_px
                self.axis_draw_points.append([p1, p1 + axis_2d])

                # if axis != current_axis:
                #     color[3] = 0.2
                self.axis_draw_colors.append(color)

    
    def calculate_slide_draw_lines(self, nearest_vert, slide_verts, world_mat):
        nearest_vert_data: EdgeVertexSlideData = slide_verts[nearest_vert.index]
        lines = []
        for side in nearest_vert_data.dir_side:
            if side is not None:
                lines.append([world_mat @ self.nearest_vert_co_3d, world_mat @ side])
        return lines


    def get_nearest_vert_2d(self, selected_verts, mouse_coords):
        self.ensure_bmesh()

        mouse_co: Vector = Vector(mouse_coords)
        min_dist_sq = float('INF')
        visited_verts = set()
        nearest_vert = None

        for vert in selected_verts:
            if vert.index not in visited_verts:
                vert_2d = utils.math.location_3d_to_2d(self.world_mat @ vert.co)
                dist_sq = (mouse_co - vert_2d).length_squared
                if dist_sq < min_dist_sq:
                    nearest_vert = vert
                    min_dist_sq = dist_sq
                visited_verts.add(vert.index)
        if nearest_vert is not None:
            return nearest_vert

        return None

    
    def get_nearest_vert_3d(self, selected_verts, point):
        self.ensure_bmesh()

        min_dist_sq = float('INF')

        for vert in selected_verts:
            vert_orig_co = self.slide_verts[vert.index].vert_orig_co
            vert_orig_co_world = self.world_mat @ vert_orig_co
            dist_sq = (point - vert_orig_co_world).length_squared
            if dist_sq < min_dist_sq:
                nearest_vert = vert
                min_dist_sq = dist_sq
        if nearest_vert is not None:
            return nearest_vert

        return None


    def get_slide_edges(self, selected_verts, axis_vec_og, world_mat):

        to_origin = Matrix.Translation(-world_mat.to_translation()) @ world_mat
        axis_vec = -axis_vec_og.copy()

        slide_verts: Dict[int ,EdgeVertexSlideData] = {}
        for v in selected_verts:

            slide_verts[v.index] = EdgeVertexSlideData()
            sv: EdgeVertexSlideData = slide_verts[v.index]
            sv.vert = v
            sv.vert_orig_co =  v.co.copy()
            
            alpha = 0.0
            beta = 0.0
            for edge in v.link_edges:
                other_vert = edge.other_vert(v)
                dir = to_origin @ (other_vert.co - v.co)
       
                dir_norm = dir.copy()
                dir_norm.normalize()
                dir_norm = dir_norm

                axis_vec *= -1
                d1 = dir_norm.dot(axis_vec)
               
                cos_theta = float('-INF')
                if dir_norm.length > 0.0:
                    cos_theta = d1 

                epsilon = 0.001
                if cos_theta >= utils.math.clamp(0.0, alpha - epsilon, 1) and not (abs(cos_theta) < 0.1):
                    
                    sv.dir_side[0] = other_vert.co.copy()
                    sv.vert_side[0] = other_vert
                    sv.edge_len[0] = dir.length
                    alpha = cos_theta

                axis_vec *= -1 
                d2 = dir_norm.dot(axis_vec)
                cos_theta = float('-INF')
                if dir_norm.length > 0.0:  
                    cos_theta = d2
               
                if cos_theta >= utils.math.clamp(0.0, beta - epsilon, 1.0) and not (abs(cos_theta) < 0.1):
                    sv.dir_side[1] = other_vert.co.copy()
                    sv.vert_side[1] = other_vert
                    sv.edge_len[1] = dir.length
                    beta = cos_theta
                

                if sv.dir_side[1] is None and sv.dir_side[0] is not None:
                    sv.dir_side[1] = sv.dir_side[0].lerp(v.co, 1.5)
                    # sv.vert_side[1] = v
                    sv.edge_len[1] = sv.edge_len[0]

        return slide_verts


    def edge_constraint_slide(self, context, mouse_coords, axis):
        world_mat = self.world_mat

        ray_origin, ray_dir_vec = utils.raycast.get_ray(context.region, context.region_data, mouse_coords)
        plane_co = world_mat @ self.nearest_vert_co_3d
        plane_n = axis

        proj_vec = utils.math.project_point_plane(plane_n, ray_dir_vec)
        proj_vec.normalize()

        factor = utils.math.ray_plane_intersection(plane_co, plane_n, ray_origin, proj_vec)

        # print(f"factor: {factor}")

        to_origin = Matrix.Translation(-world_mat.to_translation()) @ world_mat
        from_origin = to_origin.inverted_safe()
     
        for data in self.slide_verts.values():

            vert = data.vert
            if not vert.is_valid:
                return
            if not vert.is_valid:
                return

            dir_a = data.dir_side[0]
            dir_b = data.dir_side[1]
            # print(f"Side: {'A' if factor > 0 else 'B'}")

            if factor > 0 and dir_a is not None:
                other_vert_co = dir_a
                dir_edge_a = [data.vert_orig_co, other_vert_co]
                
                start: Vector = to_origin @ dir_edge_a[0]
                end: Vector = to_origin @ dir_edge_a[1]

                # if  use_indiviual_orgins:
                #     dir_vec =  ((end-start).normalized())
                #     self.axis_vec = dir_vec * self.slide_value
               
                plane_offset = axis * factor
                plane_normal = axis
                
                intersect_vec = intersect_line_plane(start, end, start + plane_offset, plane_normal)

                if intersect_vec:
                    if self.constrained_to_bounds:
                        perc = intersect_point_line(intersect_vec, start, end)[1]
                        if 1.0 >= perc >= 0.0:
                            # self.points_3d.append(world_mat @ from_origin @ intersect_vec)
                            vert.co = from_origin @ intersect_vec
                    else:
                        vert.co = from_origin @ intersect_vec

            elif factor < 0.0 and dir_b is not None:
                other_vert_co = dir_b
                dir_edge_b = [data.vert_orig_co, other_vert_co]

                axis_vec_copy = axis.copy()
                axis_vec_copy.negate()
                axis_vec_opp = axis_vec_copy

                start: Vector = to_origin @ dir_edge_b[0]
                end: Vector = to_origin @ dir_edge_b[1]

                # if  use_indiviual_orgins:
                #     dir_vec =  ((end-start).normalized())
                #     axis_vec_opp = dir_vec * -self.slide_value
               
                plane_offset = axis_vec_opp * -factor
                plane_normal = axis_vec_opp

                # self.points_3d.append(start + plane_offset)

                intersect_vec = intersect_line_plane(start, end, start + plane_offset, plane_normal)
                if intersect_vec:
                    if self.constrained_to_bounds:
                        perc = intersect_point_line(intersect_vec, start, end)[1]
                        if 1.0 >= perc >= 0.0:
                            # self.points_3d.append(world_mat @ from_origin @ intersect_vec)
                            vert.co = from_origin @ intersect_vec
                    else:
                        vert.co = from_origin @ intersect_vec
               
        bmesh.update_edit_mesh(context.active_object.data, destructive=False)

    
    def edge_constraint_slide_snap(self, context, distance, side_index, axis):
        world_mat = self.world_mat
        # HARDCODE INTO B
        # side_index = 1
        # self.constrained_to_bounds = False
        to_origin = Matrix.Translation(-world_mat.to_translation()) @ world_mat
        from_origin = to_origin.inverted_safe()
     
        for data in self.slide_verts.values():

            vert = data.vert
            if not vert.is_valid:
                return

            dir_a = data.dir_side[0]
            dir_b = data.dir_side[1]

            if side_index == 0 and dir_a is not None:
                other_vert_co = dir_a
                dir_edge_a = [data.vert_orig_co, other_vert_co]
                
                start: Vector = to_origin @ dir_edge_a[0]
                end: Vector = to_origin @ dir_edge_a[1]

                # if  use_indiviual_orgins:
                #     dir_vec =  ((end-start).normalized())
                #     self.axis_vec = dir_vec * self.slide_value
               
                plane_offset = axis * distance
                plane_normal = axis
                # self.points_3d.append(world_mat @(start + plane_offset))
                intersect_vec = intersect_line_plane(start, end, start + plane_offset, plane_normal)

                if intersect_vec:
                    if self.constrained_to_bounds:
                        # perc = intersect_point_line(intersect_vec, start, end)[1]
                        # if 1.0 >= perc >= 0.0:
                            # self.points_3d.append(world_mat @ from_origin @ intersect_vec)
                        vert.co = from_origin @ utils.math.constrain_point_to_line_seg(start, intersect_vec, end)#from_origin @ intersect_vec
                    else:
                        self.points_3d.append(from_origin @ intersect_vec)
                        vert.co = from_origin @ intersect_vec

            elif side_index == 1 and dir_b is not None:
                other_vert_co = dir_b
                dir_edge_b = [data.vert_orig_co, other_vert_co]

                axis_vec_copy = axis.copy()
                axis_vec_copy.negate()
                axis_vec_opp = axis_vec_copy

                start: Vector = to_origin @ dir_edge_b[0]
                end: Vector = to_origin @ dir_edge_b[1]

                # if  use_indiviual_orgins:
                #     dir_vec =  ((end-start).normalized())
                #     axis_vec_opp = dir_vec * -self.slide_value
               
                plane_offset = axis_vec_opp * distance
                plane_normal = axis_vec_opp
                # self.points_3d.append(world_mat @(start + plane_offset))
                intersect_vec = intersect_line_plane(start, end, start + plane_offset, plane_normal)
                if intersect_vec:
                    if self.constrained_to_bounds:
                    #     perc = intersect_point_line(intersect_vec, start, end)[1]
                    #     if 1.0 >= perc >= 0.0:
                            # self.points_3d.append(world_mat @ from_origin @ intersect_vec)
                        vert.co = from_origin @ utils.math.constrain_point_to_line_seg(start, intersect_vec, end) #@ intersect_vec
                    else:
                        # self.points_3d.append(from_origin @ intersect_vec)

                        vert.co = from_origin @ intersect_vec
        bmesh.update_edit_mesh(context.active_object.data, destructive=False)
        
    
    def get_axis(self, axis, world_mat):
        axis_lookup = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1))}
        slot = bpy.context.window.scene.transform_orientation_slots[0]
        transform_orientation = slot.type
        if transform_orientation == 'GLOBAL':
            return axis_lookup[axis]

        elif transform_orientation == 'LOCAL':
                return world_mat.to_3x3() @ axis_lookup[axis]

        elif transform_orientation == 'VIEW':
            view_mat = bpy.context.region_data.perspective_matrix.to_3x3().normalized().inverted()
            if axis != "Z":
                return view_mat @ axis_lookup[axis]
            else:
                return None

        elif transform_orientation == 'CURSOR':
            cursor_mat = bpy.context.scene.cursor.matrix
            return cursor_mat.to_3x3() @ axis_lookup[axis]

        elif transform_orientation == 'Normal':
            return None
        
        else:
            custom_mat = slot.custom_orientation.matrix
            return custom_mat.to_3x3() @ axis_lookup[axis]

    
    def do_snap(self, context, snap_target_location):
        use_axis_constraint = False
        if bpy.context.scene.tool_settings.snap_target in {'CLOSEST'}:
           self.snap_nearest_or_active(context, snap_target_location, use_axis_constraint, False)
        elif bpy.context.scene.tool_settings.snap_target in {'ACTIVE'}:
            self.snap_nearest_or_active(context, snap_target_location, use_axis_constraint, True)
    
    
    def snap_nearest_or_active(self, context, snap_target_location, use_axis_constraint, use_active):
        bm = self.ensure_bmesh()
        nearest_vert_3d = None
        if not use_active:
            selected_verts = [vert for vert in bm.verts if vert.select]
            nearest_vert_3d = self.get_nearest_vert_3d(selected_verts, snap_target_location)
        else:
            nearest_vert_3d = utils.mesh.get_active_vert(bm)

        world_mat = self.world_mat
        if nearest_vert_3d is not None:
            self.nearest_vert_3d = nearest_vert_3d
            self.nearest_vert_co_3d = world_mat @ self.nearest_vert_3d.co
           
            slide_vert = self.slide_verts[self.nearest_vert_3d.index]
            closest_side = None
            closest_side_index = -1

            # for index, dir_side in enumerate(slide_vert.dir_side):
            #     if dir_side is not None:
            #         start_vert_co = world_mat @ slide_vert.vert_orig_co

            #         end_vert_co = world_mat @ dir_side
            #         snap_point, _ = intersect_point_line(snap_target_location, start_vert_co, end_vert_co)

            #         edge_dir_vec = (end_vert_co - start_vert_co).normalized()
            #         start_vec_to_snap_point_vec = (snap_point - start_vert_co).normalized()

            start_vec_to_snap_target_vec = (snap_target_location - (world_mat @ slide_vert.vert_orig_co)).normalized()
            dot = self.axis_vec.normalized().dot(start_vec_to_snap_target_vec)

            if dot >= 0.0:
                closest_side_index = 0
                closest_side = slide_vert.dir_side[closest_side_index]
            elif dot < 0.0:
                closest_side_index = 1
                closest_side = slide_vert.dir_side[closest_side_index]
            
            # print(f"Side: {'A' if closest_side_index == 0 else 'B'}")

            #         if isclose(dot, 1.0, abs_tol=10e-5):
            #             closest_side = dir_side
            #             closest_side_index = index
                    
            if closest_side is not None:
                snap_point = None
                factor = None
                if not use_axis_constraint:
                    snap_point, factor = intersect_point_line(snap_target_location, world_mat @ slide_vert.vert_orig_co, world_mat @ closest_side)
                    self.snap_point = snap_point
                    # Correct Distance
                    distance =  (self.snap_point) - (world_mat @ slide_vert.vert_orig_co)
                    factor = distance.project(self.axis_vec).length
                else:
                    self.snap_point = snap_point
                    # world_origin = Vector()
                    vert_co = world_mat @ slide_vert.vert_orig_co
                    point_on_line = vert_co + self.axis_vec
                    # self.points_3d.append(point_on_line)
                    point_on_axis_line, _ = intersect_point_line(snap_target_location, vert_co, point_on_line)
                   
                    # edge_vec =  (world_mat @ closest_side) - (world_mat @slide_vert.vert_orig_co)
                    # self.points_3d.append(edge_vec)
                    # vec2 = point_on_axis_line - (world_mat @ slide_vert.vert_orig_co)
                    # isect_point = intersect_line_plane( (world_mat @ closest_side), (world_mat @ slide_vert.vert_orig_co), point_on_axis_line, self.axis_vec)
                    # p, factor = intersect_point_line(isect_point, (world_mat @ closest_side), (world_mat @slide_vert.vert_orig_co))
                    # proj_vec = vec2.project(edge_vec)
                    # self.points_3d.append((world_mat @ slide_vert.vert_orig_co) + proj_vec)
                    # self.points_3d.append(point_on_axis_line)
                    factor = (point_on_axis_line - vert_co).length

                # print(f"Factor {factor}")         
                self.edge_constraint_slide_snap(context, factor, closest_side_index, self.axis_vec)
    
    
    def ensure_bmesh(self):
        if self.bm is None or not self.bm.is_valid:
            bpy.context.active_object.update_from_editmode()
            mesh = bpy.context.active_object.data
            
            self.bm: bmesh = bmesh.from_edit_mesh(mesh)

        return self.bm
  
def get_valid_orientation():
    valid_types = {'GLOBAL','LOCAL', 'VIEW', 'CURSOR'}
    invalid_types = {'NORMAL', 'GIMBAL'}
    transform_orientation =  bpy.context.window.scene.transform_orientation_slots[0].type
    if transform_orientation in valid_types or transform_orientation not in invalid_types:
        return transform_orientation
    else:
        return None

def edge_constraint_status(layout):
    orientation = get_valid_orientation()
    if orientation is not None:
        layout.label(text=f"Edge Constraint:({orientation})",)
        layout.label(text="X Axis", icon='EVENT_X')
        layout.label(text="Y Axis", icon='EVENT_Y')
        layout.label(text="Z Axis", icon='EVENT_Z')



