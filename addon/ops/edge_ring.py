from __future__ import annotations
from abc import ABCMeta
from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from ..props.fl_properties import AllPropsNoSnap
    
from collections import namedtuple

from ..utils.mesh import (WalkerMetadata,bmesh_edge_ring_walker, bmesh_edge_ring_walker_sel_only, 
                        bm_tri_fan_walker, is_ngon, get_face_from_index, get_face_loop_for_edge, is_tri_fan)

LoopEndpoints = namedtuple('LoopEndpoints','start end')


class LoopCollection(metaclass=ABCMeta):
    def __init__(self):
        self._owner = None
        self._active_loop = None
        self._other_loop = None
        self._active_face = None
        self._loops = []
        self._is_loop = False
        self._shortest_len = None
        self._loop_endpoints = None

    def set_owner(self, owner):
        self._owner = owner

    def get_owner(self):
        return self._owner

    def get_active_loop(self):
       return self._active_loop

    def set_active_loop(self, value):
        self._active_loop = value
    
    def set_other_loop(self, active_loop):
        self._other_loop = active_loop.link_loop_next.link_loop_next
    
    def get_other_loop(self):
        return self._other_loop

    def get_active_face(self):
       return self._active_face

    def set_active_face(self, value):
        self._active_face = value
       
    def get_loops(self):
       return self._loops

    def set_loop_data(self, value: List):
        self._loops = value
    
    def get_is_loop(self):
        return self._is_loop

    def set_is_loop(self, value: bool):
        self._is_loop = value
    
    def get_shortest_edge_len(self):
        return self._shortest_len

    def set_shortest_edge_len(self, value):
        self._shortest_len = value
    
    def get_active_loop_endpoints(self):
        return self._loop_endpoints
    
    def set_active_loop_endpoints(self, start, end):
        self._loop_endpoints = LoopEndpoints(start, end)
    
    def is_single_loop(self):
        return len(self._loops) == 1


class EdgeRing(LoopCollection):
    pass
   
class TriFan(LoopCollection): 
    pass      
   
class SingleLoop(LoopCollection):
    pass

     
#TODO Put into own module
#TODO Only instantiate Loop collection when the data changes
class EdgeDataFactory():

    @staticmethod
    def create(start_edge, context):
        current_edge = start_edge
        selected_only = context.insert_on_selected_edges
        face = get_face_from_index(context.active_object.bm, context.current_face_index)
        if face is None:
            return None

        loops = []
        data = None
        active_loop = None

        def get_loop_endpoints():
            start = context.world_mat @ active_loop.vert.co
            end = context.world_mat @ active_loop.edge.other_vert(active_loop.vert).co
            if context.flipped:
                end, start = start, end
            
            return start, end

        if(is_ngon(context.active_object.bm, context.current_face_index) or context.insert_verts):
            active_loop = get_face_loop_for_edge(face, start_edge)
            data = SingleLoop()
            data.set_owner(context)
            data.set_is_loop(False)
            data.set_loop_data([active_loop])
            data.set_active_loop(active_loop)
            data.set_active_face(face)
            data.set_shortest_edge_len(active_loop.edge.calc_length())
            data.set_active_loop_endpoints(*get_loop_endpoints())
            return data
    
        metadata = WalkerMetadata()
        if not selected_only:
            active_loop = get_face_loop_for_edge(face, start_edge)
            loops = list(bmesh_edge_ring_walker(start_edge, False, metadata))
        else:
            loops = list(bmesh_edge_ring_walker_sel_only(current_edge, metadata))

            if loops and metadata.is_loop:
                active_loop = metadata.active_loop
                if active_loop is None:
                    return None
       
                if is_tri_fan(loops):
                    data = TriFan()
                    data.set_owner(context)
                    data.set_is_loop(True)
                    data.set_loop_data(loops)
                    data.set_active_loop(active_loop)
                    data.set_active_face(face)
                    data.set_shortest_edge_len(metadata.shortest_edge_len)
                    data.set_other_loop(get_face_loop_for_edge(face, start_edge))
                    data.set_active_loop_endpoints(*get_loop_endpoints())
                    return data

        if len(loops) < 2 and not selected_only:
            loops = list(bm_tri_fan_walker(context.active_object.bm, context.current_face_index, start_edge, metadata))
            active_loop = metadata.active_loop
            if loops[1] is not None and active_loop:
                data = TriFan()
                data.set_owner(context)
                data.set_loop_data(loops)
                data.set_shortest_edge_len(metadata.shortest_edge_len)
                data.set_active_loop(active_loop)
                data.set_active_face(face)
                data.set_is_loop(metadata.is_loop)
                data.set_other_loop(get_face_loop_for_edge(face, start_edge))
                data.set_active_loop_endpoints(*get_loop_endpoints())
                if metadata.is_loop:
                    del data.get_loops()[-1]
                return data
            else:
                return None
        if loops:
            active_loop = metadata.active_loop
            if active_loop is None:
                return None
            data = EdgeRing()
            data.set_owner(context)
            data.set_is_loop(metadata.is_loop)
            data.set_loop_data(loops)
            data.set_shortest_edge_len(metadata.shortest_edge_len)
            data.set_active_loop(active_loop)
            data.set_active_face(face)
            data.set_other_loop(get_face_loop_for_edge(face, start_edge))
            data.set_active_loop_endpoints(*get_loop_endpoints())
            return data
        else:
            return None