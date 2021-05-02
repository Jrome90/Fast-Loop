import bpy
from bmesh.types import *

from .. import utils
from .. utils.ops import get_m_button_map as btn
from . fast_loop_common import FastLoopCommon, Mode, mode_enabled, set_mode
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


class FastLoopClassicOperator(bpy.types.Operator, FastLoopCommon):
    bl_idname = 'fl.fast_loop_classic'
    bl_label = 'fast_loop clasic operator'
    bl_options = {'REGISTER'}

    invoked_by_tool: bpy.props.BoolProperty(
        name='tool invoked',
        description='Do not change. This is meant to be hidden',
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'}
    )

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
            f"Even: {self.use_even}",
            f"Flipped: {self.flipped}",
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
        self.is_classic = True
        set_mode(Mode.SINGLE)

        self.draw_handler_3d = bpy.types.SpaceView3D.draw_handler_add(self.draw_3d, (context, ), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}
    

    def modal(self, context, event):

        if context.mode != 'EDIT_MESH' or (self.invoked_by_tool and not any(tool_name in ['fl.fast_loop_classic_tool'] for tool_name in [tool.idname for tool in context.workspace.tools])) \
        or self.cancelled:
            return self.cancel(context)

        if self.snap_context is None:
            self.snap_context: SnapContext = SnapContext.get(context, context.evaluated_depsgraph_get(), context.space_data, context.region)
            self.snap_context.add_object(self.active_object)

        if self.snap_context is not None and (not mode_enabled(Mode.EDGE_SLIDE)) or mode_enabled(Mode.REMOVE_LOOP): 

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
                
        handled = False
        if event.type in {'E', 'F'} and not (event.ctrl or event.alt):

            if event.type == 'E' and event.value == 'PRESS':
                self.use_even = not self.use_even

            elif event.type == 'F' and event.value == 'PRESS':
                self.flipped = not self.flipped
            handled = True

        elif not event.alt and mode_enabled(Mode.EDGE_SLIDE):
            set_mode(Mode.SINGLE)
            bpy.ops.ed.undo_push()
            handled = True

        elif event.alt and not mode_enabled(Mode.EDGE_SLIDE):

            set_mode(Mode.EDGE_SLIDE)
            bpy.ops.fl.edge_slide('INVOKE_DEFAULT', invoked_by_op=True)          
            handled = True      

        elif event.type in {'ESC'}:
            self.cancelled = True
            handled = True

        if event.type in {'RIGHTMOUSE', 'LEFTMOUSE'}:
            if self.current_edge is not None and event.type in {btn('LEFTMOUSE')} and event.value == 'PRESS':
                if mode_enabled(Mode.SINGLE):
                    if not event.shift:
                        self.create_geometry(context)

                    elif event.shift and not event.ctrl:
                        self.create_geometry(context, True)
                        self.set_flow()

                elif mode_enabled(Mode.SELECT_LOOP):
                    self.select_edge_loop(context)

                elif mode_enabled(Mode.REMOVE_LOOP):
                    self.remove_edge_loop(context)
                    context.area.tag_redraw()
                    
                bpy.ops.ed.undo_push()
                handled = True
            elif event.type in {btn('RIGHTMOUSE')} and event.value == 'PRESS':
                self.cancelled = True
                return {'RUNNING_MODAL'}
                        
        if event.ctrl and event.type in {'RIGHT_SHIFT', 'LEFT_SHIFT'}:
            set_mode(Mode.REMOVE_LOOP)
            context.area.tag_redraw()
            handled = True

        if event.type not in {'RIGHT_SHIFT', 'LEFT_SHIFT'} and not event.ctrl and mode_enabled(Mode.REMOVE_LOOP):
           set_mode(Mode.SINGLE)
           handled = True

        if event.ctrl and not (mode_enabled(Mode.SELECT_LOOP) or mode_enabled(Mode.REMOVE_LOOP)) and not mode_enabled(Mode.EDGE_SLIDE):
            set_mode(Mode.SELECT_LOOP)
            context.area.tag_redraw()
            handled = True

        elif not event.ctrl and mode_enabled(Mode.SELECT_LOOP):
            set_mode(Mode.SINGLE)
            handled = True

        self.set_header(context)
        context.area.tag_redraw()

        if handled:
            return {'RUNNING_MODAL'}
        else:
            return {'PASS_THROUGH'}


    def cleanup(self, context):
        super().cleanup(context)
    

    def update(self, nearest_co=None):

        if self.current_edge is None:
            return

        if nearest_co is not None:
            self.current_position = self.world_inv @ nearest_co

        if self.current_ring:
            if not self.bm.is_valid:
                return

            self.ring_loops = self.calc_edge_directions()

        self.update_positions_along_edges()

    def update_positions_along_edges(self):

        self.loop_draw_points.clear()
        self.edge_data.clear()
            
        for i, loop in enumerate(self.ring_loops.keys()):

            points_on_edge = []
            for point_on_edge in self.get_posititon_along_edge(loop, i):
                points_on_edge.append(point_on_edge)

            self.edge_data.append(EdgeData(points_on_edge, loop))
            self.loop_draw_points.append(points_on_edge)

 
    def create_geometry(self, context, set_edge_flow=False):
        
        num_segments = 1

        edges = [data.edge for data in self.edge_data]
      
        edge_verts_co = [(data.first_vert.co, data.edge.other_vert(data.first_vert).co) for data in self.edge_data]

        flipped = self.flipped
        points = [data.points if not flipped else list(reversed(data.points)) for data in self.edge_data]
        
        super().create_geometry(context, edges, points, edge_verts_co, num_segments, set_edge_flow)

    
    def get_posititon_along_edge(self, loop: BMLoop, i):
        world_mat = self.world_mat
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

        factor = self.offset
        use_even = self.use_even

        point = None
        if use_even:
                factor = utils.math.remap(0.0, (start-end).length, 0.0, self.current_edge.calc_length(), self.offset)

        if not flipped: 
            point = start.lerp(end, utils.math.clamp(0.0, factor, 1.0))
        else:   
            point = end.lerp(start, utils.math.clamp(0.0, factor, 1.0))
                
        return [world_mat @ point]