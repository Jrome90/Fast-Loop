import bpy
from bmesh.types import *

from .. import utils
from .. utils.ops import get_m_button_map as btn
from . fast_loop_common import FastLoopCommon, EdgeData, Mode, mode_enabled, set_mode
from .. snapping.snapping import SnapContext


class FastLoopClassicOperator(FastLoopCommon):
    bl_idname = 'fl.fast_loop_classic'
    bl_label = 'fast_loop clasic operator'
    bl_options = {'REGISTER'}

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
    
      
    def set_status(self, context):

        def status(header, context):
            shortcuts= [
                        {"Insert Loop": ['MOUSE_LMB']},
                        {"Even": ['EVENT_E']},
                        {"Flipped": ['EVENT_F']},
                         {"Cancel/Exit": ['MOUSE_RMB']},
                    ]

            header = utils.ops.generate_status_layout(shortcuts, header.layout)       
            utils.ui.statistics(header, context)

        context.workspace.status_text_set(status)


    def draw(self, context):
        pass


    def execute(self, context):
        return {'FINISHED'}


    def setup(self, context):
        self.set_status(context)          
        super().setup(context)     


    def invoke(self, context, event):
        set_mode(Mode.SINGLE)
        return  super().invoke(context, event)
    

    def modal(self, context, event):

        if context.mode != 'EDIT_MESH' or (self.invoked_by_tool and not any(tool_name in ['fl.fast_loop_classic_tool'] for tool_name in [tool.idname for tool in context.workspace.tools])) \
        or self.cancelled:
            return self.cancel(context)

        if mode_enabled(Mode.EDGE_SLIDE):
            return {'PASS_THROUGH'}

        if self.snap_context is None:
            self.snap_context: SnapContext = SnapContext.get(context, context.evaluated_depsgraph_get(), context.space_data, context.region)
            self.snap_context.add_object(self.active_object)

        if self.snap_context is not None and (not mode_enabled(Mode.EDGE_SLIDE)) or mode_enabled(Mode.REMOVE_LOOP): 

            mouse_coords = (event.mouse_region_x, event.mouse_region_y)
            _ , element_index, nearest_co = self.snap_context.do_snap(mouse_coords, self.active_object)

            if element_index is not None:
              self.update(element_index, nearest_co)
            else:
                self.current_edge = None
                
        handled = False
        if event.type in {'E', 'F'} and not (event.ctrl or event.alt):

            if event.type == 'E' and event.value == 'PRESS':
                self.use_even = not self.use_even

            elif event.type == 'F' and event.value == 'PRESS':
                self.flipped = not self.flipped
            handled = True

        elif event.type in {'ESC'}:
            self.cancelled = True
            handled = True

        if event.type in {btn('RIGHTMOUSE')} and event.value == 'PRESS':
            self.cancelled = True
            return {'RUNNING_MODAL'}

        if super().modal(context, event):
            handled = True

        self.set_header(context)
        context.area.tag_redraw()

        if handled:
            return {'RUNNING_MODAL'}
        else:
            return {'PASS_THROUGH'}


    def edge_slide_finished(self):    
        set_mode(Mode.SINGLE)
        bpy.ops.ed.undo_push()


    def modal_select_edge_loop_released(self):
        set_mode(Mode.SINGLE)


    def modal_remove_edge_loop_released(self):
        set_mode(Mode.SINGLE)


    def cleanup(self, context):
        super().cleanup(context)

    
    def update_current_ring(self):
        self.current_ring = list(utils.mesh.bmesh_edge_ring_walker(self.current_edge))
        if len(self.current_ring) < 2:
            return False
        return True
    

    def update_loops(self, nearest_co=None):

        if self.current_edge is None:
            return

        if nearest_co is not None:
            self.current_position = self.world_inv @ nearest_co

        if self.current_ring:
            if not self.bm.is_valid:
                return

            self.distance, self.shortest_edge_len, self.edge_start_position, self.edge_end_position, self.is_loop = self.get_data_from_edge_ring()

    def update_positions_along_edges(self):

        self.loop_draw_points.clear()
        self.edge_data.clear()
            
        for i, loop in enumerate(self.current_ring):

            if not loop.is_valid:
                return False

            points_on_edge = []
            for point_on_edge in self.get_posititon_along_edge(loop, i):
                points_on_edge.append(point_on_edge)

            self.edge_data.append(EdgeData(points_on_edge, loop))
            self.loop_draw_points.append(points_on_edge)
        
        return True

 
    def create_geometry(self, context, set_edge_flow=False):
        
        num_segments = 1

        edges = [data.edge for data in self.edge_data]
      
        edge_verts_co = [(data.first_vert.co, data.edge.other_vert(data.first_vert).co) for data in self.edge_data]

        flipped = self.flipped
        points = [data.points if not flipped else list(reversed(data.points)) for data in self.edge_data]
        
        super().create_geometry(context, edges, points, edge_verts_co, num_segments, select_edges=set_edge_flow)

    
    def get_posititon_along_edge(self, loop: BMLoop, i):
        world_mat = self.world_mat
        flipped = self.flipped
        
        opposite_edge = loop.link_loop_next.link_loop_next.edge
        if not loop.edge.is_manifold and not opposite_edge.is_manifold and loop.edge.index != self.current_edge.index:
            flipped = not flipped

        # Edge is not manifold, being moused over, and it's the first edge in teh list
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