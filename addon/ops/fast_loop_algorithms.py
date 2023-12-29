from __future__ import annotations
from abc import ABC
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .fast_loop_common import FastLoopCommon
    from ..props.fl_properties import AllPropsNoSnap


from mathutils.geometry import intersect_line_plane
from .. import utils

from .fast_loop_helpers import Mode, mode_enabled


class ComputeEdgePostitonsStrategy(ABC):
    @staticmethod
    def execute(context: FastLoopCommon, props: AllPropsNoSnap, start, end, factor, flipped):
        pass


class ComputeEdgePostitonsSingleAlgorithm(ComputeEdgePostitonsStrategy):
    @staticmethod
    def execute(context: FastLoopCommon, props: AllPropsNoSnap, start, end, factor, flipped):
        points = []
        mirrored_points = []
        world_mat = context.world_mat

        vec_len = (start-end).length
        
        def add_point(point):
            points.append(world_mat @ point)
        
        def add_m_point(point):
            mirrored_points.append(world_mat @ point)

        use_even = props.common.use_even
        perpendicular = props.common.perpendicular
        new_factor = factor
        if use_even and not perpendicular:
            new_factor = utils.math.remap(0.0, vec_len, 0.0, context.current_edge.calc_length(), factor)

        if flipped and not perpendicular:
            start, end = end, start
 
        final = start.lerp(end, utils.math.clamp(0.0, new_factor, 1.0))

        if perpendicular:
            world_inv = context.world_inv
            start_pos, end_pos = context.loop_data.get_active_loop_endpoints()
            start_pos_local = world_inv @ start_pos
            end_pos_local = world_inv @ end_pos
            plane_origin = start_pos_local.lerp(end_pos_local, new_factor)
            plane_normal = (end_pos_local - start_pos_local).normalized()
            isect_point = intersect_line_plane(start, end, plane_origin, plane_normal)
            if isect_point is not None:
                final = utils.math.constrain_point_to_line_seg(start, isect_point, end)  

        add_point(final)
        mirrored = props.common.mirrored
        if mirrored:
            m_factor = 1-new_factor
            final = start.lerp(end, utils.math.clamp(0.0, m_factor, 1.0))

            if perpendicular:
                world_inv = context.world_inv
                start_pos, end_pos = context.loop_data.get_active_loop_endpoints()
                start_pos_local = world_inv @ start_pos
                end_pos_local = world_inv @ end_pos
                plane_origin = start_pos_local.lerp(end_pos_local, m_factor)
                plane_normal = (end_pos_local - start_pos_local).normalized()
                isect_point = intersect_line_plane(start, end, plane_origin, plane_normal)
                if isect_point is not None:
                    final = utils.math.constrain_point_to_line_seg(start, isect_point, end)

            add_m_point(final)

            points.extend(mirrored_points)
        is_reversed = False
        if mirrored:
            if factor > 0.5 and not context.flipped:
                points.reverse()
                is_reversed = True

            elif factor < 0.5 and context.flipped:
                points.reverse()
                is_reversed = True

        return points, is_reversed


class ComputeEdgePostitonsMultiAlgorithm(ComputeEdgePostitonsStrategy):
    @staticmethod
    def execute(context: FastLoopCommon, props: AllPropsNoSnap, start, end, factor, flipped):
        ml_props = props.multi_loop
        points = []
        mirrored_points = []
        world_mat = context.world_mat

        edge_len = (start-end).length
        
        def add_point_append(point):
            points.append(world_mat @ point)
        
        def add_m_point(point):
            mirrored_points.append(world_mat @ point)

        # def calculate_scale_factor(scale_factor2):
        #     # Distance from the midpoint to the farthest point for the edge hovered over
        #     l = context.shortest_edge_len

        #     mid_to_farthest = ((l * (n - 1 )) / (2 * (n + 1))) * scale_factor2
        #     end_to_farthest = l/2 - mid_to_farthest

        #     mid_to_farthest2 = ((vec_len * (n - 1 )) / (2 * (n + 1)))
        #     end_to_farthest2 = vec_len/2 - mid_to_farthest2

        #     dist_difference = end_to_farthest2 - end_to_farthest

        #     desired_dist = mid_to_farthest2 + dist_difference

        #     if not isclose(mid_to_farthest2, 0.0):
        #         scale_factor2 = desired_dist / mid_to_farthest2
        #     else:
        #         scale_factor2 = 0

        #     return scale_factor2

        n = int(context.segments)
        # if not context.insert_midpoint:
        use_even = props.common.use_even
        perpendicular = props.common.perpendicular
        if use_even and not perpendicular:
            factor = utils.math.remap(0.0, edge_len, 0.0, context.current_edge.calc_length(), factor)

        factor = utils.math.clamp(0.0, factor, 1.0)

        if flipped:
            start, end = end, start

        origin = start.lerp(end, factor)
        c = utils.math.clamp(0, ml_props.scale, 1)
        init_scale_factor = 0.0
        if context.segments >= 2:
            # c2 = 1 - (2/(context.segments + 1)) #1 - (1 / (((context.segments - 1) /2) + 1))
            init_scale_factor = utils.math.remap(0.0, 1.0, 0.0, 1.0 + (2.0/( context.segments - 1.0)), c)
        # orig_cos = []
        # ab_cos = []
        # ab_lengths = []
        # if not context.use_multi_loop_offset:
            # for j in range(0, n):
                
        # value = 0.1
        # init_scale_factor = ((value/edge_len) * (context.segments + 1.0)) 
        # init_scale_factor = utils.math.remap(0.0, edge_len, 0.0, context.shortest_edge_len, init_scale_factor)
        mirrored = props.common.mirrored

        for j in range(0, n):
            scale_factor = init_scale_factor
            percent = ((1.0 + j) / ( n + 1.0))

            if not ml_props.use_multi_loop_offset:
                    #end + (start - end) *  percent
                
                if use_even and not perpendicular:
                    pos = end.lerp(start, percent)
                    # Make insides even?
                    # if j == n-1:
                    #     scale_factor = utils.math.remap(0.0, vec_len, 0.0, context.shortest_edge_len, scale_factor)
                    # else:
                    scale_factor = utils.math.remap(0.0, edge_len, 0.0, context.loop_data.get_shortest_edge_len(), scale_factor)
                else:
                    pos = end.lerp(start, percent)
                scale = scale_point_along_edge(pos, start, end, scale_factor)
                final = scale + (origin - ((start + end) * 0.5))
                final = utils.math.constrain_point_to_line_seg(start, final, end)

                if perpendicular:
                    final = straight_multiloop(context, end, start, percent, factor, scale_factor, False, final)

                if mirrored:
                    final = utils.math.constrain_point_to_line_seg(start, final, (start+end)*0.5)

                add_point_append(final)
                if mirrored:
                    pos = end.lerp(start, percent)

                    # if j == 0:
                    #     scale_factor = utils.math.remap(0.0, vec_len, 0.0, context.shortest_edge_len, -scale_factor)
                    # else:
                    #     scale_factor = utils.math.remap(0.0, vec_len, 0.0, vec_len, -scale_factor)


                    scale = scale_point_along_edge(pos, start, end, scale_factor)
                    origin_m = end.lerp(start, factor)
                    final_m = scale + (origin_m - ((start + end) * 0.5))
                    # if j == n-1:
                    #     context.points_3d.append(final_m)
                    
                    if perpendicular:
                        final_m = straight_multiloop(context, end, start, percent, factor, scale_factor, True, final_m)
                    
                    final_m = utils.math.constrain_point_to_line_seg((start+end)*0.5, final_m, end)

                    add_m_point(final_m)

            # MLO
            else:
                #TODO if using distance instead of scale percent then dont remap
                if not perpendicular:
                    scale_factor = utils.math.remap(0.0, edge_len, 0.0, context.loop_data.get_shortest_edge_len(), scale_factor)
                final = None
                pos = origin + (end - start) * percent
                scale = scale_point_along_edge_o(pos, origin, scale_factor)
                final = scale - ((scale_factor * (end-start)) / (n + 1))
                final = utils.math.constrain_point_to_line_seg(start, final, end)

                if perpendicular:
                    final = straight_multiloop_offset(context, start, end, percent, factor, scale_factor, False, final)
                
                add_point_append(final)

                # Mirrored side
                if mirrored:
                    origin_m = end.lerp(start, factor)
                    pos = origin_m - (end - start) * (1-percent)
                    scale = scale_point_along_edge_o(pos, origin_m, (scale_factor))
                    final_m = scale - ((scale_factor * (start-end)) / (n + 1))
                    final_m = utils.math.constrain_point_to_line_seg(end, final_m, start)
                
                    if perpendicular:
                        final_m = straight_multiloop_offset(context, end, start, percent, factor, scale_factor, True, final_m)
                    add_m_point(final_m)

        is_reversed = False
        if not ml_props.use_multi_loop_offset:
            if not context.flipped or (context.flipped and mirrored):
                points.reverse()

            if mirrored:
                if factor < 0.5:
                    mirrored_points.reverse()
                    points.extend(mirrored_points)
                
                elif factor > 0.5 and not use_even:
                    points.extend(mirrored_points)
                
                if context.flipped:
                    points.reverse()
                    is_reversed = True
        
        elif ml_props.use_multi_loop_offset:
            if context.flipped:
                points.reverse()

            if mirrored:
                if not context.flipped:
                    points.reverse()

                if factor > 0.5:
                    if not perpendicular:
                        mirrored_points.reverse()
                    points.extend(mirrored_points)
                    if not context.flipped:
                        is_reversed = True
                elif factor < 0.5:
                    if not perpendicular:
                        mirrored_points.reverse()
                    points[:0] = mirrored_points
                    if context.flipped:
                        is_reversed = True

                if not context.flipped:
                    points.reverse()
                    
        return points, is_reversed

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
    start_pos, end_pos = context.loop_data.get_active_loop_endpoints()

    start_pos_local = context.world_inv @ start_pos
    end_pos_local = context.world_inv @ end_pos

    if not mirrored:
        origin = start_pos_local.lerp(end_pos_local, c_factor)
    else:
        origin = end_pos_local.lerp(start_pos_local, c_factor)

    pos =  end_pos_local + ( start_pos_local - end_pos_local) *  percent
    scale = scale_point_along_edge(pos, start_pos_local, end_pos_local, scale_factor)
    
    plane_normal = (end_pos_local - start_pos_local).normalized()
    plane_origin = scale + (origin - ((start_pos_local + end_pos_local) * 0.5))

    return calc_line_plane_intersection(start, end, plane_normal, plane_origin, fallback)


def straight_multiloop_offset(context, start, end, percent, c_factor, scale_factor, mirrored, fallback):
    start_pos, end_pos = context.loop_data.get_active_loop_endpoints()
    start_pos_local = context.world_inv @ start_pos
    end_pos_local = context.world_inv @ end_pos

    if not mirrored:
        origin = start_pos_local.lerp(end_pos_local, c_factor)
        pos =  origin + (end_pos_local - start_pos_local) * percent
        scale = scale_point_along_edge_o(pos, origin, scale_factor)

        plane_normal = (end_pos_local - start_pos_local).normalized()
        plane_origin = scale - ((scale_factor * (end_pos_local-start_pos_local)) / (context.segments + 1))
    else:
        origin = end_pos_local.lerp(start_pos_local, c_factor)
        pos = origin + (start_pos_local - end_pos_local) * percent
        scale = scale_point_along_edge_o(pos, origin, scale_factor)

        plane_normal = (end_pos_local - start_pos_local).normalized()
        plane_origin = scale - ((scale_factor * (start_pos_local-end_pos_local)) / (context.segments + 1))

    return calc_line_plane_intersection(start, end, plane_normal, plane_origin, fallback)


import bpy
class ComputeEdgePostitonsOverrideAlgorithm(ComputeEdgePostitonsStrategy):
    @staticmethod
    def execute(context, props: AllPropsNoSnap, start, end, factor, flipped):
        points = []
        mirrored_points = []
        world_mat = context.world_mat

        vec_len = (start-end).length
        
        def add_point(point):
            points.append(world_mat @ point)
        
        def add_m_point(point):
            mirrored_points.append(world_mat @ point)
        use_even = props.common.use_even
        perpendicular = props.common.perpendicular

        window_manager = bpy.context.window_manager
        index = window_manager.Loop_Cut_Lookup_Index
        slot = window_manager.Loop_Cut_Slots.loop_cut_slots[index]
        for loop_cut in slot.loop_cut_slot.values():
            new_factor = 0.0
            if loop_cut.get_method() == 'PERCENT':
                new_factor = loop_cut.percent * 0.01
                if use_even:
                    new_factor = utils.math.remap(0.0, vec_len, 0.0, context.current_edge.calc_length(), new_factor)

            else:
                scene = bpy.context.scene
                unit_scale = 1#scene.unit_settings.scale_length
                new_factor = (loop_cut.distance * unit_scale) / vec_len

            m_factor = 1-new_factor
            if flipped and not perpendicular:
                new_factor = 1-new_factor
                m_factor = 1-m_factor
                
            final = start.lerp(end, utils.math.clamp(0.0, new_factor, 1.0))

            if perpendicular:
                start_pos, end_pos = context.loop_data.get_active_loop_endpoints()

                plane_normal = (end_pos - start_pos).normalized()
                plane_origin = start_pos.lerp(end_pos, new_factor)
                isect_point = intersect_line_plane(start, end, plane_origin, plane_normal)
                if isect_point is not None:
                    final = utils.math.constrain_point_to_line_seg(start, isect_point, end)  

            add_point(final)
            mirrored = props.common.mirrored
            if mirrored:
                final = start.lerp(end, utils.math.clamp(0.0, m_factor, 1.0))

                if perpendicular:
                    start_pos, end_pos = context.loop_data.get_active_loop_endpoints()
                    plane_normal = (end_pos - context.start_pos).normalized()
                    plane_origin = context.start_pos.lerp(end_pos, m_factor)
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
       
        if flipped:
            points.reverse()

        return points, False