from math import isclose

from mathutils.geometry import intersect_line_plane
from .. import utils

from . fast_loop_common import mode_enabled, Mode

class ComputeEdgePostitonsStrategyInterface():
    @staticmethod
    def execute(context, start, end, factor, use_even, flipped, mirrored, straight=False):
        pass

class ComputeEdgePostitonsSingleAlgorithm(ComputeEdgePostitonsStrategyInterface):
    @staticmethod
    def execute(context, start, end, factor, use_even, flipped, mirrored, straight=False):
        points = []
        mirrored_points = []
        world_mat = context.world_mat

        vec_len = (start-end).length
        
        def add_point(point):
            points.append(world_mat @ point)
        
        def add_m_point(point):
            mirrored_points.append(world_mat @ point)

        new_factor = factor
        if use_even:
            new_factor = utils.math.remap(0.0, vec_len, 0.0, context.current_edge.calc_length(), factor)

        m_factor = 1-new_factor
        if flipped and not straight:
            start_tmp = start
            start = end
            end = start_tmp
 
        final = start.lerp(end, utils.math.clamp(0.0, new_factor, 1.0))

        if straight:   
            plane_normal = (context.edge_end_position - context.edge_start_position).normalized()
            plane_origin = context.edge_start_position.lerp(context.edge_end_position, new_factor)
            isect_point = intersect_line_plane(start, end, plane_origin, plane_normal)
            if isect_point is not None:
                final = utils.math.constrain_point_to_line_seg(start, isect_point, end)  

        add_point(final)

        if mirrored:
            final = start.lerp(end, utils.math.clamp(0.0, m_factor, 1.0))

            if straight:
                plane_normal = (context.edge_end_position - context.edge_start_position).normalized()
                plane_origin = context.edge_start_position.lerp(context.edge_end_position, m_factor)
                isect_point = intersect_line_plane(start, end, plane_origin, plane_normal)
                if isect_point is not None:
                    final = utils.math.constrain_point_to_line_seg(start, isect_point, end)

            add_m_point(final)

        points.extend(mirrored_points)

        return points

class ComputeEdgePostitonsMultiAlgorithm(ComputeEdgePostitonsStrategyInterface):
    @staticmethod
    def execute(context, start, end, factor, use_even, flipped, mirrored, straight=False):
        points = []
        mirrored_points = []
        world_mat = context.world_mat

        vec_len = (start-end).length
        
        def add_point(point):
            points.append(world_mat @ point)
        
        def add_m_point(point):
            mirrored_points.append(world_mat @ point)

        def calculate_scale_factor(scale_factor2):
            # Distance from the midpoint to the farthest point for the edge hovered over
            l = context.shortest_edge_len

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

        n = int(context.segments)
        if not context.insert_at_midpoint:
            if use_even:
                factor = utils.math.remap(0.0, vec_len, 0.0, context.current_edge.calc_length(), context.offset)

            c_factor = utils.math.clamp(0.0, factor, 1.0)

            if flipped:
                start_tmp = start
                start = end
                end = start_tmp

            origin = start.lerp(end, c_factor)

            c = utils.math.clamp(0, context.scale, 1)
            init_scale_factor = 0.0
            if context.segments - 1 != 0:
                init_scale_factor = utils.math.remap(0.0, 1.0, 0.0, 1.0 + (2.0/( context.segments - 1.0)), c)

            for j in range(0, n):
                scale_factor = init_scale_factor
                percent = ((1.0 + j) / ( n + 1.0))

                if not context.use_multi_loop_offset:
                    pos = end + (start - end) *  percent
                    
                    if use_even:
                        # Make insides even?
                        scale_factor = utils.math.remap(0.0, vec_len, 0.0, context.shortest_edge_len, scale_factor)

                    scale = scale_point_along_edge(pos, start, end, scale_factor)
                    final = scale + (origin - ((start + end) * 0.5))
                    final = utils.math.constrain_point_to_line_seg(start, final, end)

                    if mirrored:
                        final = utils.math.constrain_point_to_line_seg(start, final, (start+end)*0.5)
                        origin_m = end.lerp(start, c_factor)
                        final_m = scale + (origin_m - ((start + end) * 0.5))
                        final_m = utils.math.constrain_point_to_line_seg((start+end)*0.5, final_m, end)
                        
                        if straight:
                            final_m = straight_multiloop(context, start, end, percent, c_factor, scale_factor, True, final_m)

                        add_m_point(final_m)

                    if straight:
                        final = straight_multiloop(context, start, end, percent, c_factor, scale_factor, False, final)
                
                    add_point(final)

                # MLO
                else:
                   
                    if not straight:
                        scale_factor = utils.math.remap(0.0, vec_len, 0.0, context.shortest_edge_len, scale_factor)
                    
                    final = None
                    pos = origin + (end - start) * percent
                    scale = scale_point_along_edge_o(pos, origin, scale_factor)
                    final = scale - ((scale_factor * (end-start)) / (n + 1))
                    final = utils.math.constrain_point_to_line_seg(start, final, end)

                    if straight:
                        final = straight_multiloop_offset(context, start, end, percent, c_factor, scale_factor, False, final)

                    add_point(final)

                    # Mirrored side
                    if mirrored:
                        origin_m = end.lerp(start, c_factor)
                        pos = origin_m - (end - start) * (1-percent)
                        scale = scale_point_along_edge_o(pos, origin_m, (scale_factor))
                        final_m = scale - ((scale_factor * (start-end)) / (n + 1))
                        final_m = utils.math.constrain_point_to_line_seg(end, final_m, start)
                    
                        if straight:
                            final_m = straight_multiloop_offset(context, start, end, percent, c_factor, scale_factor, True, final_m)

                        add_m_point(final_m)
            
        elif context.insert_at_midpoint and not context.use_multi_loop_offset:

            if flipped:
                start_tmp = start
                start = end
                end = start_tmp
            c_factor = utils.math.clamp(0.0, factor, 1.0)
            init_origin = start.lerp(end, c_factor)
            origin = init_origin
            c = utils.math.clamp(0, context.scale, 1)
            init_scale_factor = 0.0
            if context.segments - 1 != 0:
                init_scale_factor = utils.math.remap(0.0, 1.0, 0.0, 1.0 + (2.0/( context.segments - 1.0)), c)
            scale_factor = context.scale

            for i in range(0, n) :
                percent = ((1.0 + i) / ( n + 1.0))

                scale_factor = init_scale_factor
                if use_even:
                    scale_factor = calculate_scale_factor(scale_factor)

                pos = end + (start - end) * percent

                # Make insides even?
                #scale_factor = utils.math.remap(0.0, vec_len, 0.0, self.shortest_edge_len, scale_factor)
                scale = scale_point_along_edge(pos, start, end, scale_factor)
                final = scale + (origin - ((start + end) * 0.5))

                final = utils.math.constrain_point_to_line_seg(start, final, end)

                if straight:
                    final = straight_multiloop_midpoint(context, start, end, percent, c_factor, scale_factor, final)

                add_point(final)

        elif context.insert_at_midpoint and context.use_multi_loop_offset:

            if use_even:
                factor = utils.math.remap(0.0, vec_len, 0.0, context.shortest_edge_len, factor)
            c_factor = utils.math.clamp(0.0, factor, 1.0)
            init_origin = start.lerp(end, c_factor)
            origin = init_origin
            c = utils.math.clamp(0, context.scale, 1)

            init_scale_factor = 0.0
            if context.segments - 1 != 0:
                init_scale_factor = utils.math.remap(0.0, 1.0, 0.0, 1.0 + (2.0/( context.segments - 1.0)), c)

            scale_factor = init_scale_factor

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
                    origin = end.lerp(start, c_factor)
                    if i != last:
                        origin = start + (end - start) * 0.5
                    pos = origin + (start - end) * percent
                    scale = scale_point_along_edge_o(pos, origin, scale_factor)
                    final = scale - ((scale_factor * (start-end)) / (n + 1))
                    final = utils.math.constrain_point_to_line_seg(end, final, start)


                if straight:
                    final = straight_multiloop_midpoint_offset(context, start, end, percent, c_factor, scale_factor, final)

                add_point(final)

        if mirrored:
            if factor < 0.5 and not context.use_multi_loop_offset:
                mirrored_points.reverse()
                points.reverse()
                points.extend(mirrored_points)
                points.reverse()

            elif factor > 0.5 and context.use_multi_loop_offset and not straight:
                mirrored_points.reverse()
                points.reverse()

                points.extend(mirrored_points)
                points.reverse()

            elif straight and context.use_multi_loop_offset:
                if factor < 0.5:
                    mirrored_points.reverse()
                    points.extend(mirrored_points)
                else:
                   
                    points.reverse()

                    points.extend(mirrored_points)
                    points.reverse()

            else:
                points.extend(mirrored_points)

        return points

def scale_point_along_edge(point, start, end, scale_fac):
            return utils.math.scale_points_along_line([point], start, end, scale_fac)[0]
        
def scale_point_along_edge_o(point, origin, scale_fac):
    return utils.math.scale_points_about_origin([point], origin, scale_fac)[0]

def calc_line_plane_intersection(start, end, plane_normal, plane_origin, fallback=None):
    isect_point = intersect_line_plane(start, end, plane_origin, plane_normal)
    if isect_point is not None:
        return utils.math.constrain_point_to_line_seg(start, isect_point, end)
    else:
        return fallback

def straight_multiloop(context, start, end, percent, c_factor, scale_factor, mirrored, fallback):
    e_start = context.edge_start_position
    e_end = context.edge_end_position

    if not mirrored:
        origin = e_start.lerp(e_end, c_factor)
    else:
        origin = e_end.lerp(e_start, c_factor)

    pos =  e_end + ( e_start - e_end) *  percent
    scale = scale_point_along_edge(pos, e_start, e_end, scale_factor)
    
    plane_normal = (e_end - e_start).normalized()
    plane_origin = scale + (origin - ((e_start + e_end) * 0.5))

    return calc_line_plane_intersection(start, end, plane_normal, plane_origin, fallback)


def straight_multiloop_offset(context, start, end, percent, c_factor, scale_factor, mirrored, fallback):
    e_start = context.edge_start_position
    e_end = context.edge_end_position

    if not mirrored:
        origin = e_start.lerp(e_end, c_factor)
        pos =  origin + (e_end - e_start) * percent
        scale = scale_point_along_edge_o(pos, origin, scale_factor)

        plane_normal = (e_end - e_start).normalized()
        plane_origin = scale - ((scale_factor * (e_end-e_start)) / (context.segments + 1))
    else:
        origin = e_end.lerp(e_start, c_factor)
        context.points_3d.append(origin)
        pos = origin + (e_start-e_end) * percent
        scale = scale_point_along_edge_o(pos, origin, scale_factor)

        plane_normal = (e_end - e_start).normalized()
        plane_origin = scale - ((scale_factor * (e_start-e_end)) / (context.segments + 1))

    return calc_line_plane_intersection(start, end, plane_normal, plane_origin, fallback)

def straight_multiloop_midpoint(context, start, end, percent, c_factor, scale_factor, fallback):
    e_start = context.edge_start_position
    e_end = context.edge_end_position

    origin = e_start.lerp(e_end, c_factor)
    pos = e_end + (e_start - e_end) * percent
    scale = scale_point_along_edge(pos, e_start, e_end, scale_factor)

    plane_normal = (e_end - e_start).normalized()
    plane_origin = scale + (origin - ((e_start + e_end) * 0.5))
    
    return calc_line_plane_intersection(start, end, plane_normal, plane_origin, fallback)

def straight_multiloop_midpoint_offset(context, start, end, percent, c_factor, scale_factor, fallback):
    e_start = context.edge_start_position
    e_end = context.edge_end_position

    origin = e_start.lerp(e_end, c_factor)
    pos =  origin + (e_end - e_start) * percent
    scale = scale_point_along_edge_o(pos, origin, scale_factor)

    plane_normal = (e_end - e_start).normalized()
    plane_origin = scale - ((scale_factor * (e_end-e_start)) / (context.segments + 1))

    return calc_line_plane_intersection(start, end, plane_normal, plane_origin, fallback)

import bpy
class ComputeEdgePostitonsOverrideAlgorithm(ComputeEdgePostitonsStrategyInterface):
    @staticmethod
    def execute(context, start, end, factor, use_even, flipped, mirrored, straight=False):
        points = []
        mirrored_points = []
        world_mat = context.world_mat

        vec_len = (start-end).length
        
        def add_point(point):
            points.append(world_mat @ point)
        
        def add_m_point(point):
            mirrored_points.append(world_mat @ point)

        scene = bpy.context.scene
        index = scene.Loop_Cut_Lookup_Index
        slot = scene.Loop_Cut_Slots.loop_cut_slots[index]
        for loop_cut in slot.loop_cut_slot.values():
            new_factor = 0.0
            if loop_cut.get_method() == 'PERCENT':
                new_factor = loop_cut.percent * 0.01
            else:
                unit_scale = scene.unit_settings.scale_length
                new_factor = (loop_cut.distance * unit_scale) / context.current_edge.calc_length()

            if use_even:
                new_factor = utils.math.remap(0.0, vec_len, 0.0, context.current_edge.calc_length(), new_factor)

            m_factor = 1-new_factor
            if flipped and not straight:
                new_factor = 1-new_factor
                m_factor = 1-m_factor
                
            final = start.lerp(end, utils.math.clamp(0.0, new_factor, 1.0))

            if straight:   
                plane_normal = (context.edge_end_position - context.edge_start_position).normalized()
                plane_origin = context.edge_start_position.lerp(context.edge_end_position, new_factor)
                isect_point = intersect_line_plane(start, end, plane_origin, plane_normal)
                if isect_point is not None:
                    final = utils.math.constrain_point_to_line_seg(start, isect_point, end)  

            add_point(final)

            if mirrored:
                final = start.lerp(end, utils.math.clamp(0.0, m_factor, 1.0))

                if straight:
                    plane_normal = (context.edge_end_position - context.edge_start_position).normalized()
                    plane_origin = context.edge_start_position.lerp(context.edge_end_position, m_factor)
                    isect_point = intersect_line_plane(start, end, plane_origin, plane_normal)
                    if isect_point is not None:
                        final = utils.math.constrain_point_to_line_seg(start, isect_point, end)

                add_m_point(final)

        if mirrored:
            if mode_enabled(Mode.MULTI_LOOP):
                mirrored_points.reverse()
                points.extend(mirrored_points)

            elif mode_enabled(Mode.SINGLE):
                points.extend(mirrored_points)
                points.reverse()

        return points
