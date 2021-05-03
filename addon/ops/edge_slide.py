from typing import *
from dataclasses import dataclass, field
from math import isclose

import bpy, bmesh
from bmesh.types import *
from mathutils import Matrix, Vector
from mathutils.geometry import intersect_point_line, intersect_line_plane

from .. import utils
from .. utils.ops import get_m_button_map as btn
from . edge_constraint import EdgeConstraint_Translation, edge_constraint_status, get_valid_orientation


@dataclass
class EdgeVertexSlideData():
    
    vert: BMVert = None
    vert_orig_co: Vector = None
    vert_side: List[BMVert] = field(default_factory=lambda: [None, None])
    dir_side: List[Vector] =  field(default_factory=lambda: [None, None])

    # Only used with edge contraints.
    edge_len: List[float] = field(default_factory=lambda: [None, None])
   

    def __repr__(self) -> str:
        vert_side_a = self.vert_side[0].index if self.vert_side[0] is not None else None
        vert_side_b = self.vert_side[1].index if self.vert_side[1] is not None else None
        string = f"vert_side: a {vert_side_a}; b {vert_side_b} \n"
        string += f"dir_side: a {self.dir_side[0]}; b {self.dir_side[1]} \n"
        return string


from enum import Enum
class Mode(Enum):
    EDGE_SLIDE = 1
    EDGE_CONSTRAINT = 2
    PASS_THROUGH = 3


class EdgeSlideOperator(bpy.types.Operator, EdgeConstraint_Translation):
    bl_idname = 'fl.edge_slide'
    bl_label = 'edge slide'
    bl_options = {'REGISTER'}

    invoked_by_op: bpy.props.BoolProperty(
        name='op invoked',
        description='Do not change. This is meant to be hidden',
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'}
    )   

    mode = Mode.EDGE_SLIDE
    is_sliding = False
    slide_value = 0.0
    bm: BMesh = None
    nearest_vert = None
    nearest_vert_co = None

    world_mat: Matrix = None
    world_inv: Matrix = None

    draw_handler_2d = None

    # For Debug
    points_2d = []
    points_3d = []

    slide_verts: Dict[int ,EdgeVertexSlideData] = {}
    ss_slide_directions: List[Vector] = []


    @classmethod
    def poll(cls, context):
       return (context.space_data.type == 'VIEW_3D'
                and context.active_object
                and context.active_object.type == "MESH"
                and context.active_object.mode == 'EDIT'                
              )


    def set_status(self, context):
        def status(header, context):
            layout = header.layout
            layout.label(text="Even Edge Loop", icon='EVENT_CTRL')
            layout.label(text="Preserve Loop Shape", icon='EVENT_SHIFT')

            if not self.invoked_by_op:
                edge_constraint_status(layout)
            utils.ui.statistics(header, context)

        context.workspace.status_text_set(status)


    def setup(self, context):
        self.world_mat = context.object.matrix_world.normalized()
        self.world_inv = context.object.matrix_world.inverted_safe()
        self.slide_verts.clear()
        self.mode = Mode.EDGE_SLIDE
        self.is_sliding = False
        self.ensure_bmesh()
        utils.mesh.ensure(self.bm)
        
        self.bm.select_mode = {'EDGE'}
        self.bm.select_flush_mode()
        

    def invoke(self, context, event):
 
        self.report({'INFO'}, 'Edge Slide Started')
        self.set_status(context)
        self.setup(context)
        self.draw_handler_2d = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, (context, ), 'WINDOW', 'POST_PIXEL')
        self.draw_handler_3d = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_3d, (context, ), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self)
        bpy.context.window.cursor_modal_set("CROSSHAIR")
        return {'RUNNING_MODAL'}


    def finished(self, context):
        super().finished(context)
        self.clear_draw()
        bpy.context.window.cursor_modal_restore()
        context.workspace.status_text_set(None)
        self.report({'INFO'}, 'Edge Slide Finished')


        if getattr(self, 'draw_handler_2d', None):
            self.draw_handler_2d = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler_2d, 'WINDOW')

        if getattr(self, 'draw_handler_3d', None):
            self.draw_handler_3d = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler_3d, 'WINDOW')
    
    def clear_draw(self):
        self.axis_draw_points.clear()
        self.axis_draw_colors.clear()
        self.slide_edge_draw_lines.clear()

    def modal(self, context, event):
        
        if not self.invoked_by_op and event.ctrl and event.type == 'Z' and event.value == 'PRESS':
            return {'PASS_THROUGH'}
        handled = False
        if not self.invoked_by_op and not event.ctrl and event.type in {'X', 'Y', 'Z', 'S'} and event.value == 'PRESS':
            if event.type == 'S':
                if not self.mode == Mode.PASS_THROUGH:
                    self.mode = Mode.PASS_THROUGH

                    self.is_sliding = False
                    self.clear_draw()
                    self.points_2d = None

                    context.area.tag_redraw()
                    return {'RUNNING_MODAL'}
                else:
                    self.mode = Mode.EDGE_SLIDE
                    handled = True

            elif not event.ctrl and get_valid_orientation() is not None and event.value == 'PRESS' :
                    bm = self.ensure_bmesh()

                    mouse_coords = (event.mouse_region_x, event.mouse_region_y)
                    selected_verts = [vert for vert in bm.verts if vert.select]
                    
                    vert = self.get_nearest_vert(selected_verts, mouse_coords)
                    if vert is not None:
                        self.nearest_vert = vert
                        self.nearest_vert_co = vert.co.copy()
                        self.clear_draw()
                    else:
                        self.report({'INFO'}, 'Please select an edge before using.')
                        return {'RUNNING_MODAL'}

                    if not self.is_sliding:
                    
                        self.active_axis = event.type
                        self.axis_vec = self.get_axis(event.type, self.world_mat)
                        self.calculate_axis_draw_points(context, vert, self.active_axis, self.world_mat)
                        self.slide_verts = self.get_slide_edges(selected_verts, self.axis_vec, self.world_mat)
                        self.slide_edge_draw_lines =  self.calculate_slide_draw_lines(vert, self.slide_verts, self.world_mat)

                        self.is_sliding = True
                        self.mode = Mode.EDGE_CONSTRAINT

                    elif self.is_sliding and self.mode == Mode.EDGE_CONSTRAINT:
                        self.is_sliding = False
                        self.mode = Mode.EDGE_SLIDE

            handled = True
            
        if self.mode == Mode.PASS_THROUGH:
            return {'PASS_THROUGH'}

        if not event.alt and self.invoked_by_op:
            self.finished(context)
            return {'FINISHED'}

        elif not self.invoked_by_op and event.type == btn('RIGHTMOUSE') and event.value == 'PRESS':
            self.finished(context)
            context.area.tag_redraw()
            return {'FINISHED'}
        
        if event.type in {'LEFTMOUSE', 'RIGHTMOUSE', 'MOUSEMOVE'}:

            if not self.mode == Mode.EDGE_CONSTRAINT and event.type == btn('LEFTMOUSE') and event.value == 'PRESS' and not self.is_sliding:
                self.ensure_bmesh()
                utils.mesh.ensure(self.bm)
                mouse_coords = (event.mouse_region_x, event.mouse_region_y)
                vert, edge = self.get_nearest_vert_and_edge(mouse_coords)
                if vert is not None:
                    self.nearest_vert = vert
                    self.slide_verts =  self.calculate_edge_slide_directions(edge)
                    self.ss_slide_directions =  self.calculate_screen_space_slide_directions(edge, mouse_coords)
                    self.is_sliding = True
                else:
                    self.report({'INFO'}, 'Please select an edge before using.')
                    return {'RUNNING_MODAL'}

            if event.type == 'MOUSEMOVE' and self.is_sliding:

                if self.is_sliding:
                    mouse_coords = (event.mouse_region_x, event.mouse_region_y)
                    if self.mode == Mode.EDGE_SLIDE:
                        even =  event.ctrl and not event.shift
                        keep_shape = event.shift and not event.ctrl
                        self.edge_slide(context, mouse_coords, even, keep_shape)
                    else:                    
                        self.edge_constraint_slide(context, mouse_coords, self.axis_vec, self.world_mat)

            if event.type == btn('LEFTMOUSE') and event.value == 'RELEASE' and self.is_sliding:
                self.slide_verts.clear()
                self.ensure_bmesh()
                utils.mesh.ensure(self.bm)
                self.is_sliding = False
                self.axis_draw_points.clear()
                self.points_2d = None
                if not self.invoked_by_op:
                    self.mode = Mode.EDGE_SLIDE
                    bpy.ops.ed.undo_push()

            handled = True
            
        context.area.tag_redraw()
        if handled:
            return {'RUNNING_MODAL'}
        else:
            return {'PASS_THROUGH'}

    
    def draw_callback_3d(self, context):
        if self.mode == Mode.EDGE_CONSTRAINT:
            super().draw_callback_3d(context)

        if self.points_3d:
            utils.drawing.draw_points(self.points_3d)


    def draw_callback_px(self, context):
      

        if self.points_2d:
            utils.drawing.draw_points_2d(self.points_2d)

        if  self.mode == Mode.EDGE_SLIDE and self.is_sliding and self.nearest_vert_co_2d is not None:
            utils.drawing.draw_circle_2d((self.nearest_vert_co_2d), 2.5)
            #utils.drawing.draw_rectangle_2d(5, self.nearest_vert_co_2d)

        elif self.mode == Mode.EDGE_CONSTRAINT:
            super().draw_callback_px(context)

        elif self.mode == Mode.PASS_THROUGH:
            utils.drawing.draw_region_border(context)

    # TODO: Use a better method to do this.
    def get_nearest_vert_and_edge(self, mouse_coords):
        bm = self.ensure_bmesh()
        mouse_co: Vector = Vector(mouse_coords)
        min_dist_sq = float('INF')
        min_angle = float('INF')
        visited_verts = set()
        nearest_vert = None
        nearest_edge = None
        nearest_vert_2d = None

        for edge in bm.edges:
            if edge.select:
                for vert in [edge.verts[0], edge.other_vert(edge.verts[0])]:
                    if vert.index not in visited_verts:
                        vert_co = self.world_mat @ vert.co
                        vert_2d = utils.math.location_3d_to_2d(vert_co)
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

                    edge_2d = (other_vert_co_2d - nearest_vert_2d)
                    if not isclose(edge_2d.length, 0.0):
                        angle = (nearest_vert_2d - mouse_co).angle(edge_2d)

                        if angle < min_angle:
                            nearest_edge = vert_edge
                            min_angle = angle
            
        if nearest_vert is not None:
            return nearest_vert, nearest_edge

        return None, None

    def get_nearest_vert(self, selected_verts, mouse_coords):
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

    # Modified blender source code implementation to calculate the edges to slide one. 
    # Does not support Ngons or verts with a valence > 4. 
    def calculate_edge_slide_directions(self, current_edge):
        def get_slide_edge(loop: BMLoop, edge_next: BMEdge, next_vert: BMVert):
            first_loop = loop
            condition  = True
            slide_vec = None

            while condition:
                loop = utils.mesh.get_loop_other_edge_loop(loop, next_vert)

                e = loop.edge
                if e.index == edge_next.index:
                    return loop, slide_vec

                # Calc Slide vec
                slide_vec: Vector = (e.other_vert(next_vert).co - next_vert.co)

                if utils.mesh.get_loop_other_edge_loop(loop, next_vert).edge.index == edge_next.index:
                    return utils.mesh.get_loop_other_edge_loop(loop, next_vert), slide_vec
                
                l = loop.link_loop_radial_next
                condition = (loop.index != loop.link_loop_radial_next.index) and (l.index != first_loop.index)
                loop = l
            return None, None

        def get_next_edge(vert: BMVert, edge: BMEdge, edges):
            for next_edge in vert.link_edges:
                if next_edge.index in edges and next_edge.index != edge.index:
                    return next_edge
        
        if current_edge is None:
            return False
        
        slide_verts: Dict[int, EdgeVertexSlideData] = {}

        self.ensure_bmesh()
        edges_l = list(utils.mesh.bmesh_edge_loop_walker(current_edge, selected_edges_only=True))
        edges = {edge.index for edge in edges_l}
        
        current_edge = edges_l[0]
        last_edge = edges_l[-1]

        first_vert = current_edge.verts[0]
        vert = first_vert
        edge = current_edge
        while True:
            
            next_edge = get_next_edge(vert, edge, edges)
            if next_edge is None:
                break
            
            vert = next_edge.other_vert(vert)
            edge = next_edge

            if next_edge.index == last_edge.index:
                break

        first_edge = edge
        vec_a = None
        vec_b = None

        l_a: BMLoop = edge.link_loops[0]
        l_b = l_a.link_loop_radial_next
        
        v = vert

        next_edge = get_next_edge(v, edge, edges)
        if next_edge is not None:
            _, vec_a = get_slide_edge(l_a, next_edge, v)
        
        else:
            l_tmp = utils.mesh.get_loop_other_edge_loop(l_a, v)
            vec_a = l_tmp.edge.other_vert(v).co - vert.co

        if l_a.index != l_b.index:

            next_edge = get_next_edge(v, edge, edges)
            if next_edge is not None:
                _, vec_b = get_slide_edge(l_b, next_edge, v)
             
            else:
                l_tmp = utils.mesh.get_loop_other_edge_loop(l_b, v)
                vec_b = l_tmp.edge.other_vert(v).co - vert.co
        else:
            l_b = None
            
        l_a_prev = None
        l_b_prev = None

        condition = True
        while condition:
   
            slide_verts[v.index] = EdgeVertexSlideData()
            sv: EdgeVertexSlideData = slide_verts[v.index]
            sv.vert = v
            sv.vert_orig_co = v.co.copy()


            if l_a is not None or l_a_prev is not None:
                l_tmp: BMLoop = utils.mesh.get_loop_other_edge_loop(l_a if l_a is not None else l_a_prev, v)
                sv.vert_side[0] = l_tmp.edge.other_vert(v)
                sv.dir_side[0] = vec_a.normalized()
                sv.edge_len[0] = vec_a.length
            
            if l_b is not None or l_b_prev is not None:
                l_tmp: BMLoop = utils.mesh.get_loop_other_edge_loop(l_b if l_b is not None else l_b_prev, v)
                sv.vert_side[1] = l_tmp.edge.other_vert(v)
                sv.dir_side[1] = vec_b.normalized()
                sv.edge_len[1] = vec_b.length
            
            v = edge.other_vert(v)
            edge = get_next_edge(v, edge, edges)     
            if edge is None:

                slide_verts[v.index] = EdgeVertexSlideData()
                sv: EdgeVertexSlideData = slide_verts[v.index]
                sv.vert = v
                sv.vert_orig_co = v.co.copy()

                if l_a is not None:
                    l_tmp = utils.mesh.get_loop_other_edge_loop(l_a, v)
                    sv.vert_side[0] = l_tmp.edge.other_vert(v)
                    sv.dir_side[0] =  sv.vert_side[0].co - v.co
                    sv.edge_len[0] = sv.dir_side[0].length

                if l_b is not None:
                    l_tmp = utils.mesh.get_loop_other_edge_loop(l_b, v)
                    sv.vert_side[1] = l_tmp.edge.other_vert(v)
                    sv.dir_side[1] =  sv.vert_side[1].co - v.co
                    sv.edge_len[1] = sv.dir_side[1].length
                break 

            l_a_prev = l_a
            l_b_prev = l_b

            if l_a is not None:
                l_a, vec_a = get_slide_edge(l_a, edge, v)
     
            else:
                vec_a = Vector()
            
            if l_b is not None:
                l_b, vec_b = get_slide_edge(l_b, edge, v)
            
            else:
                vec_b = Vector()
        
            condition = edge.index != first_edge.index and (l_a is not None or l_b is not None)

        return slide_verts
       

    def calculate_screen_space_slide_directions(self, current_edge, mouse_coords):
        mouse_coord_vec: Vector = Vector(mouse_coords)
        nearest_vert = None
        nearest_co_2d = None
        min_dist_sq = float('inf')
        points = []
        for vert in current_edge.verts:
            vert_2d = utils.math.location_3d_to_2d(self.world_mat @ vert.co)
            points.append(vert_2d)
            dist_sq = (mouse_coord_vec - vert_2d).length_squared
            if dist_sq < min_dist_sq:
                nearest_vert = vert
                nearest_co_2d = vert_2d
                min_dist_sq = dist_sq

        self.nearest_vert_co_2d = nearest_co_2d
        slide_vecs = [nearest_co_2d]
        
        slide_data = self.slide_verts.get(nearest_vert.index)
        if slide_data is not None:
            for other_vert in slide_data.vert_side:
                if other_vert is not None:
                    other_co_2d = utils.math.location_3d_to_2d(self.world_mat @  other_vert.co)
                    slide_vecs.append((other_co_2d - nearest_co_2d))

        return slide_vecs


    def edge_slide(self, context, mouse_coords, even, keep_shape):
        mouse_co = Vector(mouse_coords)
        if not self.ss_slide_directions:
            return
        o = self.ss_slide_directions[0]
        mouse_vec: Vector = (mouse_co - o).normalized()
        
        dir_vecs = [vec for vec in self.ss_slide_directions[1:] if vec is not None]
        closest_vec = None
        tmp_vec = None
        k = 0
        max_cos_theta = float('-inf')
        min_dist_sq = float('inf')
        for i, vec in enumerate(dir_vecs):
            
            cos_theta = mouse_vec.dot(vec.normalized())
            if cos_theta > max_cos_theta:
                tmp_vec = vec
                max_cos_theta = cos_theta
                k = i

                cp, lambda_ = intersect_point_line(mouse_co, o, o + tmp_vec)
                if 0.0 <= lambda_ <= 1.0:
                    dist_sq = (mouse_co - cp).length_squared
                   
                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq
                        closest_vec = vec

        tmp_vec = o + tmp_vec
        if closest_vec is not None:
            if not self.nearest_vert.is_valid:
                return
            nearest_vert_slide_data = self.slide_verts.get(self.nearest_vert.index, None)
            if nearest_vert_slide_data is None:
                return
                
            vert_orig_co = self.world_mat @ nearest_vert_slide_data.vert_orig_co
            v = nearest_vert_slide_data.vert_side[k]
            if v is not None:
                vert_other_co = self.world_mat @ v.co
                edge_len = (vert_orig_co - vert_other_co).length
                cp, _ = intersect_point_line(mouse_co, o, tmp_vec)
                isect_point = utils.raycast.get_mouse_line_isect(context, cp, vert_orig_co, vert_other_co)


                if isect_point is not None:
                    cp, lambda_ = intersect_point_line(isect_point, vert_orig_co, vert_other_co)
                    d = (cp - vert_orig_co).length

                    for data in self.slide_verts.values():
                        vert = data.vert
                        o_co = data.vert_orig_co
                        dir_vec_norm = data.dir_side[k] 
                        dir =  data.vert_side[k].co
                        vec_len = data.edge_len[k]
                        
                        if even: 
                            l2 = utils.math.remap(0.0, vec_len, 0.0, edge_len, 1)
                            vert.co = (dir.lerp(o_co, l2) + ((dir-o_co).normalized() * d))

                        elif keep_shape:
                            offset = o_co + ((dir - o_co).normalized() * d)
                            plane_isect = intersect_line_plane(o_co, dir, offset, dir_vec_norm)
                            if plane_isect is not None:
                                vert.co = plane_isect
                            # else:
                            #     print("Plane isect is none")
                        else:
                            vert.co = o_co.lerp(dir, lambda_)

        mesh = context.active_object.data
        bmesh.update_edit_mesh(mesh, destructive=False)
   
    def ensure_bmesh(self):
        if self.bm is None or not self.bm.is_valid:
            bpy.context.active_object.update_from_editmode()
            mesh = bpy.context.active_object.data
            
            self.bm: bmesh = bmesh.from_edit_mesh(mesh)

        return self.bm