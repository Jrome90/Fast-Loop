from math import isclose

import bpy
from bmesh.types import *

from mathutils.geometry import intersect_point_line, intersect_line_plane

from .. import utils
from . fast_loop_common import FastLoopCommon, Mode, mode_enabled, set_mode, get_active_mode, get_options, set_option
from .. snapping.snapping import SnapContext


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
    bl_options = {'REGISTER', 'UNDO'}

    invoked_by_tool: bpy.props.BoolProperty(
        name='tool invoked',
        description='Do not change. This is meant to be hidden',
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'}
    )

    is_scaling = False
    is_selecting = False
    prev_mode = None

    segments = 2
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

    
    insert_at_midpoint = False
    @property
    def insert_at_midpoint(self):
        return get_options().insert_midpoint
    
    @insert_at_midpoint.setter
    def insert_at_midpoint(self, value):
        set_option('insert_at_midpoint', value)


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
            f"Offset: {self.distance * scale:07.3f}",
            f"Scale: {self.scale:02.3f}",
            f"Even: {self.use_even}",
            f"Flipped: {self.flipped}",
            f"Segments:{self.segments}",
        )

        context.area.header_text_set(header)


    def draw(self, context):
        pass



    def execute(self, context):                
        return {'FINISHED'}


    def invoke(self, context, event):
        if self.is_running or self.cancelled:
            return {"CANCELLED"}
        self.setup(context)

        self.draw_handler_3d = bpy.types.SpaceView3D.draw_handler_add(self.draw_3d, (context, ), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}
    

    def modal(self, context, event):

        if context.mode != 'EDIT_MESH' or (self.invoked_by_tool and not \
        any(tool_name in ['fl.fast_loop_tool'] \
            for tool_name in [tool.idname for tool in context.workspace.tools])) or self.cancelled:
            return self.cancel(context)

        if event.type == 'TIMER':
            return {'RUNNING_MODAL'}

        if self.dirty_mesh and not mode_enabled(Mode.REMOVE_LOOP):
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            self.dirty_mesh = False

            return {'RUNNING_MODAL'}

        if self.snap_context is None:
            self.snap_context: SnapContext = SnapContext.get(context, context.evaluated_depsgraph_get(), context.space_data, context.region)
            self.snap_context.add_object(self.active_object)

        if self.snap_context is not None and ((not self.is_scaling and not mode_enabled(Mode.EDGE_SLIDE)) or mode_enabled(Mode.REMOVE_LOOP)):  
            self.update_snap_context()

            mouse_coords = (event.mouse_region_x, event.mouse_region_y)
            element_index, nearest_co = self.snap_context.do_snap(mouse_coords, self.active_object)

            if element_index is not None:
                
                bm: BMesh = self.ensure_bmesh()
                bm.edges.ensure_lookup_table()
                edge = bm.edges[element_index]
            
                if edge.is_valid:
                    self.current_edge = edge
                    self.current_edge_index = edge.index

                    if not (mode_enabled(Mode.REMOVE_LOOP) or mode_enabled(Mode.SELECT_LOOP)):
                        self.current_ring = list(utils.mesh.bmesh_edge_ring_walker(self.current_edge))
                        self.update(nearest_co)

                    elif mode_enabled(Mode.REMOVE_LOOP):
                        self.remove_loop_draw_points = self.compute_remove_loop_draw_points()
            else:
                self.current_edge = None

        elif self.is_scaling:
            pass 
        
        if event.type in {'S', 'M', 'N', 'E', 'F', 'I', 'L', 'G'} and not (event.ctrl or event.alt):

            if event.type == 'S' and event.value == 'PRESS':
                set_mode(Mode.SINGLE)

            elif event.type == 'M' and event.value == 'PRESS':
                set_mode(Mode.MIRRORED)
            
            elif event.type == 'N' and event.value == 'PRESS':
                set_mode(Mode.MULTI_LOOP)

            elif event.type == 'E' and event.value == 'PRESS':
                self.use_even = not self.use_even

            elif event.type == 'F' and event.value == 'PRESS':
                self.flipped = not self.flipped
                if self.use_snap_points and  self.snap_divisions == 1:
                    if self.flipped :
                        self.snap_factor = 100 - self.snap_factor
                    else:
                        self.snap_factor = 100 - self.snap_factor

            elif event.type == 'I' and event.value == 'PRESS':
                self.use_snap_points = not self.use_snap_points

            elif event.type == 'L' and event.value == 'PRESS':
                self.lock_snap_points = not self.lock_snap_points

        elif event.type in {'ESC'}:
            set_option('cancel', True)
            return {'RUNNING_MODAL'}

        if event.ctrl and event.type == 'Z' and event.value == 'PRESS':
                prev_use_snap_points = self.use_snap_points
                prev_lock_snap_points = self.lock_snap_points
                self.use_snap_points = False
                self.lock_snap_points = False

                bpy.ops.ed.undo()

                if prev_use_snap_points:
                    self.use_snap_points = True
                if prev_lock_snap_points:
                   self.lock_snap_points = True

                return {'RUNNING_MODAL'}

        if event.type in {'RIGHTMOUSE', 'LEFTMOUSE'}:

            if self.current_edge is not None and event.type in {'LEFTMOUSE'} and event.value == 'PRESS':
                if not (mode_enabled(Mode.REMOVE_LOOP) or mode_enabled(Mode.SELECT_LOOP) or mode_enabled(Mode.EDGE_SLIDE)):
                    if not event.shift:
                        self.create_geometry(context)
                    elif event.shift:
                        self.create_geometry(context, set_edge_flow=True)
                        self.set_flow()

                elif mode_enabled(Mode.REMOVE_LOOP):
                    self.remove_edge_loop(context)
                
                elif mode_enabled(Mode.SELECT_LOOP):
                    self.select_edge_loop(context)
                    self.is_selecting = True

                bpy.ops.ed.undo_push()

            if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
                if utils.ui.inside_view_3d((event.mouse_x, event.mouse_y)):
                    # Preemptively lock the points to prevent them from changing locations after the lock_points property is set to True.
                    # This is okay to do because they will be unlocked in update_snap_context() if the property is set to False.
                    self.snap_context.lock_snap_points
                    bpy.ops.wm.call_menu_pie(name="FL_MT_FastLoop_Pie")
                    return {'RUNNING_MODAL'}

        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            if not event.ctrl and mode_enabled(Mode.MULTI_LOOP):
                self.segments += 1 if event.type == 'WHEELUPMOUSE' else - 1
                
                self.update(nearest_co)
            else:
                delta = 1 if event.type == 'WHEELUPMOUSE' else - 1
                bpy.ops.view3d.zoom(delta=delta)

        if event.type == 'MOUSEMOVE':

            if self.is_scaling and not event.alt and not mode_enabled(Mode.REMOVE_LOOP):
                delta_x = event.mouse_x - self.start_mouse_pos_x
                self.scale += delta_x * 0.01
            
                self.update()
                self.start_mouse_pos_x = event.mouse_x
            
            if event.ctrl and not event.alt and mode_enabled(Mode.MULTI_LOOP):
                
                if not self.is_scaling and event.type == 'MOUSEMOVE' and not self.is_selecting:
                    self.start_mouse_pos_x = event.mouse_x

                    self.is_scaling = True

        if self.is_scaling and not event.ctrl:
            self.is_scaling = False


        if not event.alt and mode_enabled(Mode.EDGE_SLIDE):
            if self.prev_mode is not None:
                set_mode(self.prev_mode)
                bpy.ops.ed.undo_push()
            else:
                set_mode(Mode.SINGLE)

        elif event.alt and not mode_enabled(Mode.EDGE_SLIDE):
            self.prev_mode = get_active_mode()
            set_mode(Mode.EDGE_SLIDE)
            bpy.ops.fl.edge_slide('INVOKE_DEFAULT', invoked_by_op=True)

        if event.type == 'MIDDLEMOUSE':
            return {'PASS_THROUGH'}

        if self.current_edge is None and event.type not in {'S', 'M', 'N', 'E', 'F', 'I', 'L', 'G'}:
            return {'PASS_THROUGH'}

        self.set_header(context)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}


    def cleanup(self, context):
        super().cleanup(context)
    
        if self.snap_context is not None:
            if self.use_snap_points:
                self.use_snap_points = False
                self.snap_context.disable_increment_mode()


    def update(self, nearest_co=None):

        if self.current_edge is None:
            return

        if not self.is_scaling and nearest_co is not None:
            self.current_position = self.world_inv @ nearest_co

        if self.current_ring:
            if not self.bm.is_valid:
                
                print("loop is not valid")
                return
            if not self.is_scaling:
                self.ring_loops = self.calc_edge_directions()

        self.update_positions_along_edges()

    def update_positions_along_edges(self):

        self.loop_draw_points.clear()
        self.edge_data.clear()
            
        for i, loop in enumerate(self.ring_loops.keys()):

            points_on_edge = []
            for point_on_edge in self.get_posititons_along_edge(loop, i):
                points_on_edge.append(point_on_edge)

            self.edge_data.append(EdgeData(points_on_edge, loop))
            self.loop_draw_points.append(points_on_edge)


    def update_snap_context(self):
        if get_options().dirty:
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
            set_option('dirty', False)
        

    # def draw_callback_2d(self, context):
    #     font_id = 0
    #     blf.position(font_id, 15, 30, 0)
    #     blf.size(font_id, 20, 72)
    #     blf.draw(font_id, context.object.name)

    # def draw_callback_3d(self, context):
    #     self.draw_3d(context)

 
    def create_geometry(self, context, set_edge_flow=False):
       
        num_segments = self.segments
        
        if mode_enabled(Mode.MIRRORED):
            num_segments = 2
        elif mode_enabled(Mode.SINGLE):
            num_segments = 1

        edges = [data.edge for data in self.edge_data]
      
        edge_verts_co = []
        if not self.use_multi_loop_offset and mode_enabled(Mode.MULTI_LOOP):
            edge_verts_co = [(data.edge.other_vert(data.first_vert).co, data.first_vert.co) for data in self.edge_data]
        else:
            edge_verts_co = [(data.first_vert.co, data.edge.other_vert(data.first_vert).co) for data in self.edge_data]

        flipped = self.flipped
        points = [data.points if not flipped else list(reversed(data.points)) for data in self.edge_data]
        
        super().create_geometry(context, edges, points, edge_verts_co, num_segments, set_edge_flow)

    
    def get_posititons_along_edge(self, loop: BMLoop, i):
        points = []
        world_mat = self.world_mat
        
        def add_point(point):
            points.append(world_mat @ point)

        def scale_point_along_edge(point, start, end, scale_fac):
            return utils.math.scale_points_along_line([point], start, end, scale_fac)[0]
        
        def scale_point_along_edge_o(point, origin, scale_fac):
            return utils.math.scale_points_about_origin([point], origin, scale_fac)[0]

        def calculate_scale_factor(scale_factor2):
            # Distance from the midpoint to the farthest point for the edge hovered over
            l = self.shortest_edge_len

            mid_to_farthest = ((l * (n - 1 )) / (2 * (n + 1))) * scale_factor2
            end_to_farthest = l/2 - mid_to_farthest

            mid_to_farthest2 = ((vec_len * (n - 1 )) / (2 * (n + 1)))
            end_to_farthest2 = vec_len/2 - mid_to_farthest2

            dist_difference = end_to_farthest2 - end_to_farthest

            desired_dist = mid_to_farthest2 + dist_difference

            if not isclose(mid_to_farthest2, 0.0):
                scale_factor2 = desired_dist / mid_to_farthest2
            else:
                scale_factor2 = 0

            return scale_factor2
            

        flipped = self.flipped
        
        opposite_edge = loop.link_loop_next.link_loop_next.edge
        if not loop.edge.is_manifold and not opposite_edge.is_manifold and loop.edge.index != self.current_edge.index:
            flipped = not flipped

        # Edge is not manifold, being moused over,  and it's the first edge in teh list
        elif not loop.edge.is_manifold and loop.edge.index == self.current_edge.index and i == 0:
            if opposite_edge.is_manifold:
                flipped = not flipped

        elif not loop.edge.is_manifold and loop.edge.index != self.current_edge.index and i == 0:
            if opposite_edge.is_manifold:
                flipped = not flipped

        start = loop.vert.co
        end = loop.edge.other_vert(loop.vert).co
      
        vec_len = (start-end).length

        factor = self.offset
        use_even = self.use_even
        straight = False
        final = None
        if mode_enabled(Mode.MIRRORED):  
            
            if use_even:
                factor = utils.math.remap(0.0, vec_len, 0.0, self.current_edge.calc_length(), self.offset)
          
            pos = start.lerp(end, factor) 
            pos_other = end.lerp(start, factor)

            _, fac = intersect_point_line(pos, start, end)
            if fac >  0.5:
                
                pos = end.lerp(start, fac)
                pos_other = start.lerp(end, fac)
                
            temp = [pos, pos_other]
            if flipped:
                temp.reverse()
            final = temp[0] 
            final_other = temp[1] 

            add_point(final)
            add_point(final_other)

        elif mode_enabled(Mode.SINGLE):
            if not straight:
                if use_even:
                        factor = utils.math.remap(0.0, vec_len, 0.0, self.current_edge.calc_length(), self.offset)
                if not flipped: 
                    final = start.lerp(end, utils.math.clamp(0.0, factor, 1.0))
                else:   
                    final = end.lerp(start, utils.math.clamp(0.0, factor, 1.0))
            else:

                plane_normal = (self.edge_end_position - self.edge_start_position).normalized()
                plane_origin = self.current_position
                isect_point = intersect_line_plane(start, end, plane_origin, plane_normal)
                if isect_point is not None:
                    final = utils.math.constrain_point_to_line_seg(start, isect_point, end)
                    
            add_point(final)

        else:

            if not self.insert_at_midpoint:
                if use_even:  
                    factor = utils.math.remap(0.0, vec_len, 0.0, self.current_edge.calc_length(), self.offset)

                origin = None
                if not flipped:
                    origin = start.lerp(end, utils.math.clamp(0.0, factor, 1.0))
                else:
                    origin = end.lerp(start, utils.math.clamp(0.0, factor, 1.0))

                c = utils.math.clamp(0, self.scale, 1)
                init_scale_factor = utils.math.remap(0.0, 1.0, 0.0, 1.0 + (2.0/( self.segments - 1.0)), c)
                scale_factor = init_scale_factor
                
                n = self.segments
                for j in range(0, n) :
                    scale_factor = init_scale_factor
                    percent = ((1.0 + j) / ( n + 1.0))

                    if not flipped:
                        if not self.use_multi_loop_offset:
                            pos = end + (start - end) * percent
                            
                            #Make insides even?
                            scale_factor = utils.math.remap(0.0, vec_len, 0.0, self.shortest_edge_len, scale_factor)
            
                            scale = scale_point_along_edge(pos, start, end, scale_factor)
                            final = scale + (origin - ((start + end) * 0.5))
                        else:
                            pos = origin + (end - start) * percent
                            scale_factor = utils.math.remap(0.0, vec_len, 0.0, self.shortest_edge_len, scale_factor)
                            scale = scale_point_along_edge_o(pos, origin, scale_factor)
                            final = scale - ((scale_factor*(end-start))/(n+1))
                        
                        final = utils.math.constrain_point_to_line_seg(start, final, end)

                    else:
                        if not self.use_multi_loop_offset:
                            pos = start + (end - start) * percent
                            # Make insides even?
                            scale_factor = utils.math.remap(0.0, vec_len, 0.0, self.shortest_edge_len, scale_factor)
                            scale = scale_point_along_edge(pos, start, end, scale_factor)
                            final = scale + (origin - ((start + end) * 0.5))
                        else:
                            pos = origin + (start - end) * percent
                            scale_factor = utils.math.remap(0.0, vec_len, 0.0, self.shortest_edge_len, scale_factor)
                            scale = scale_point_along_edge_o(pos, origin, scale_factor)
                            final = scale - ((scale_factor * (start-end)) / (n + 1))
                        
                        final = utils.math.constrain_point_to_line_seg(end, final, start)

                    add_point(final)
                    
            elif self.insert_at_midpoint and not self.use_multi_loop_offset:
                if use_even:
                    factor = 0.5

                init_origin = start.lerp(end, utils.math.clamp(0.0, factor, 1.0))
                origin = init_origin
                c = utils.math.clamp(0, self.scale, 1)
                init_scale_factor = utils.math.remap(0.0, 1.0, 0.0, 1.0 + (2.0/( self.segments - 1.0)), c)
                scale_factor = self.scale

                n = int(self.segments)
                for i in range(0, n) :
                    percent = ((1.0 + i) / ( n + 1.0))

                    origin = init_origin
                    scale_factor = init_scale_factor
                    if use_even:
                       
                            scale_factor = calculate_scale_factor(scale_factor)                        

                    if not flipped:
                        
                        pos = end + (start - end) * percent
                      
                        # Make insides even?
                        #scale_factor = utils.math.remap(0.0, vec_len, 0.0, self.shortest_edge_len, scale_factor)

                        scale = scale_point_along_edge(pos, start, end, scale_factor)
                        final = scale + (origin - ((start + end) * 0.5))

                        final = utils.math.constrain_point_to_line_seg(start, final, end)

                    else:
                        origin = end.lerp(start, utils.math.clamp(0.0, factor, 1.0))
                        pos = start + (end - start) * percent
                        
                        # Make insides even?
                        #scale_factor = utils.math.remap(0.0, vec_len, 0.0, self.shortest_edge_len, scale_factor)
                        scale = scale_point_along_edge(pos, start, end, scale_factor)
                        final = scale + (origin - ((start + end) * 0.5))

                        final = utils.math.constrain_point_to_line_seg(end, final, start)

                    add_point(final)

            elif self.insert_at_midpoint and self.use_multi_loop_offset:

                if use_even:    
                    factor = utils.math.remap(0.0, vec_len, 0.0, self.shortest_edge_len, factor)

                init_origin = start.lerp(end, utils.math.clamp(0.0, factor, 1.0))
                origin = init_origin
                c = utils.math.clamp(0, self.scale, 1)
                init_scale_factor = utils.math.remap(0.0, 1.0, 0.0, 1.0 + (2.0/( self.segments - 1.0)), c)
                scale_factor = init_scale_factor

                n = int(self.segments)
                for i in range(0, n) :
                    percent = ((1.0 + i) / ( n + 1.0))
                    origin = init_origin
                    scale_factor = init_scale_factor
                    last = (n-1)

                    if use_even:
                        if i == last:
                            scale_factor = calculate_scale_factor(scale_factor)
                        else:
                            origin = start + (end - start) * 0.5
                        
                    if not flipped:          
                        pos = origin + (end - start) * percent
                       
                        scale = scale_point_along_edge_o(pos, origin, scale_factor)
                        final = scale - ((scale_factor*(end-start))/(n+1))
                        final = utils.math.constrain_point_to_line_seg(start, final, end)

                    else:
                        origin = end.lerp(start, utils.math.clamp(0.0, factor, 1.0))
                        if i != last:
                            origin = start + (end - start) * 0.5
                        pos = origin + (start - end) * percent
                        scale = scale_point_along_edge_o(pos, origin, scale_factor)
                        final = scale - ((scale_factor * (start-end)) / (n + 1))
                        final = utils.math.constrain_point_to_line_seg(end, final, start)

                    add_point(final)

        return points
