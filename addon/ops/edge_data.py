from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..props.fl_properties import AllPropsNoSnap
    from .fast_loop import FastLoopOperator
from functools import singledispatchmethod
from collections import namedtuple


from mathutils.geometry import intersect_point_line
from bmesh.types import BMEdge

from .edge_ring import EdgeRing, TriFan, SingleLoop, LoopCollection

EdgeMetaData = namedtuple('ActiveEdgeData','bm_edge points')
class EdgeData():
    def __init__(self, loop_collection, props):
        self.points = []
        # self.distances = [] TODO
        self.edges = []
        self.edge_verts = []
        self.first_edge: EdgeMetaData = None
        self.other_edge: EdgeMetaData = None

        self.populate_data(loop_collection, props)
     
     
    @singledispatchmethod
    def populate_data(self, loop_collection: EdgeRing, props):
        self.calculate_points_on_edges(loop_collection, props)

    @populate_data.register
    def _(self, loop_collection: TriFan, props):
        self.calculate_points_on_edges(loop_collection, props)

    @populate_data.register
    def _(self, loop_collection: SingleLoop, props):
        self.calculate_points_on_edge(loop_collection, props)


    def calculate_points_on_edges(self, data: LoopCollection, props:AllPropsNoSnap)-> EdgeData:
        context: FastLoopOperator = data.get_owner()
        context.loop_draw_points.clear()

        for i, loop in enumerate(data.get_loops()):
            if not loop.is_valid:
                return False
            
            start_vert = loop.vert
            end_vert = loop.edge.other_vert(loop.vert)
            self.edge_verts.append((start_vert, end_vert))
            self.edges.append(loop.edge)

            flipped = props.common.flipped
            opposite_edge = loop.link_loop_next.link_loop_next.edge
            active_edge: BMEdge  = data.get_active_loop().edge
            if not loop.edge.is_manifold and not opposite_edge.is_manifold and loop.edge.index != active_edge.index:
                flipped = not flipped

            # Edge is not manifold, being moused over, and it's the first edge in the list
            elif not loop.edge.is_manifold and loop.edge.index == active_edge.index and i == 0:
                if opposite_edge.is_manifold:
                    flipped = not flipped

            # Edge is not manifold, not moused over, and it's the first edge in the list
            elif not loop.edge.is_manifold and loop.edge.index != active_edge.index and i == 0:
                if opposite_edge.is_manifold:
                    flipped = not flipped
            
            if context.force_offset_value == -1:
                position = context.current_position.world if not context.is_snapping else context.snap_position
                start_pos, end_pos = data.get_active_loop_endpoints()
                _, factor = intersect_point_line(position, start_pos, end_pos)
    
            else:
                factor = context.force_offset_value

            points_on_edge, is_reversed = context.edge_pos_algorithm.execute(context, props, start_vert.co.copy(), end_vert.co.copy(), factor, flipped)
            self.points.append(points_on_edge)
            context.loop_draw_points.append(points_on_edge)

            if is_reversed:
                points_on_edge = list(reversed(points_on_edge))

            if loop.edge.index == active_edge.index:
                self.first_edge = EdgeMetaData(active_edge, points_on_edge)

            elif loop.edge.index == data.get_other_loop().edge.index:
                self.other_edge = EdgeMetaData(loop.edge, points_on_edge)


    def calculate_points_on_edge(self, data: LoopCollection, props:AllPropsNoSnap)-> EdgeData:
        context: FastLoopOperator = data.get_owner()
        context.loop_draw_points.clear()
        loop = data.get_loops()[0]
        self.edges.append(loop.edge)

        start_vert = loop.vert
        end_vert = loop.edge.other_vert(loop.vert)
        self.edge_verts.append((start_vert, end_vert))

        if context.force_offset_value == -1:
            position = context.current_position.world if not context.is_snapping else context.snap_position
            start_pos, end_pos = data.get_active_loop_endpoints()
            _, factor = intersect_point_line(position, start_pos, end_pos)
        else:
            factor = context.force_offset_value

        points_on_edge, is_reversed = context.edge_pos_algorithm.execute(context, props, start_vert.co.copy(), end_vert.co.copy(), factor, context.flipped)
        active_edge: BMEdge  = data.get_active_loop().edge
        if is_reversed:
            points_on_edge = list(reversed(points_on_edge))
        self.first_edge = EdgeMetaData(active_edge, points_on_edge)
        self.other_edge = EdgeMetaData(active_edge, points_on_edge)

        self.points.append(points_on_edge)
        context.loop_draw_points.append(points_on_edge)