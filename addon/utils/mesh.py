from __future__ import annotations
from functools import singledispatch
from collections import defaultdict
from dataclasses import dataclass
from functools import reduce
from typing import *

from bmesh.types import *
from mathutils import Vector

@dataclass
class WalkerMetadata():
    active_loop: BMLoop = None
    is_loop: bool = False
    shortest_edge_len: float = float('INF')


# Blender source code adaptation. Returns a loop rather than an edge
@singledispatch
def bmesh_edge_ring_walker(loop: BMLoop, selected_only, metadata: WalkerMetadata):
    edge = loop.edge

    def is_valid_edge(edge: BMEdge):
        if not selected_only:
            return not edge.hide
        else:
            return (not edge.hide) and edge.select

    def rewind(loop):
        visited = set()
        visited.add(loop.edge)
        next_loop = loop

        while True:
            l = next_loop.link_loop_radial_next.link_loop_next.link_loop_next
            if len(l.face.verts) != 4 and (not l.edge.is_manifold or not l.edge.is_boundary) and is_valid_edge(l.edge):
                l = next_loop.link_loop_next.link_loop_next

            if len(l.face.verts) == 4 and (l.edge.is_manifold or l.edge.is_boundary) and l.edge not in visited and is_valid_edge(l.edge):
                next_loop = l
                visited.add(next_loop.edge)
            else:
                break

        return next_loop

    next_loop = rewind(loop).link_loop_radial_next
    visited = set()
    visited.add(next_loop.edge)
    
    active_loop = None
    shortest_edge_len = float('INF')

    while True:
        if metadata is not None:
            edge_len = next_loop.edge.calc_length()
            if edge_len < shortest_edge_len:
                shortest_edge_len = edge_len
            if next_loop.edge.index == edge.index:
                active_loop = next_loop

        yield next_loop
        l = next_loop.link_loop_radial_next.link_loop_next.link_loop_next

        if len(l.face.verts) != 4 and (not l.edge.is_manifold or not l.edge.is_boundary) and is_valid_edge(l.edge):
            l = next_loop.link_loop_next.link_loop_next

        if len(l.face.verts) == 4 and (l.edge.is_manifold or l.edge.is_boundary) and l.edge not in visited and is_valid_edge(l.edge):
            next_loop = l
            visited.add(next_loop.edge)
        else:
            if metadata is not None:
                if next_loop.link_loop_radial_next.link_loop_next.link_loop_next.edge in visited and not next_loop.edge.is_boundary:
                    metadata.is_loop = True
                metadata.active_loop = active_loop
                metadata.shortest_edge_len = shortest_edge_len
            break

@bmesh_edge_ring_walker.register
def _(edge: BMEdge, selected_only, metadata: WalkerMetadata):
    loop = edge.link_loops[0]
    return bmesh_edge_ring_walker(loop, selected_only, metadata)


# Only walk selected edges. Works with Ngons too.
def bmesh_edge_ring_walker_sel_only(edge: BMEdge, metadata: WalkerMetadata=None):

    def is_valid_edge(edge: BMEdge):
        return not edge.hide and edge.select

    def get_next_sel_loop(first_loop:BMLoop, visited=None):
        next_loop = first_loop
        while True:
            next_loop = next_loop.link_loop_next
            if next_loop.edge.select and (visited is not None and (next_loop.edge not in visited)):
                return next_loop
            elif next_loop.edge.select and visited is None:
                return next_loop
            if next_loop.index == first_loop.index:
                break

        return None
            

    def rewind(loop):
        visited = set()
        visited.add(loop.edge)

        # loop = loop.link_loop_radial_next
        next_loop = loop
       
        while True:
            l = next_loop.link_loop_radial_next.link_loop_next.link_loop_next

            if get_next_sel_loop(l, visited) is not None:
                next_loop = get_next_sel_loop(l, visited)
                visited.add(next_loop.edge)
                
            elif l.edge.index == loop.edge.index:
                return next_loop

            # Breaks edge slice rings
            ##################################
            elif len([edge for edge in l.face.edges if edge.select]) == 2:
                next_loop = get_next_sel_loop(l)
                break
            
            elif len(l.face.verts) == 4 and (l.edge.is_manifold or l.edge.is_boundary) and l.edge not in visited and is_valid_edge(l.edge):
                next_loop = l
                visited.add(next_loop.edge)
            ####################################
            else:
                break

        return next_loop

    loop = edge.link_loops[0]
    next_loop = rewind(loop).link_loop_radial_next
    visited = set()
    visited.add(next_loop.edge)

    first_loop = next_loop
    active_loop = None
    shortest_edge_len = float('INF')

    while True:
        if next_loop.edge.select:
            if metadata is not None:
                edge_len = next_loop.edge.calc_length()
                if edge_len < shortest_edge_len:
                    shortest_edge_len = edge_len
                if next_loop.edge.index == edge.index:
                    active_loop = next_loop
            yield next_loop
        else:
            if metadata is not None:
                if next_loop.link_loop_radial_next.link_loop_next.link_loop_next.edge in visited:
                    metadata.is_loop = True
                metadata.active_loop = active_loop
                metadata.shortest_edge_len = shortest_edge_len
            break

        l = next_loop.link_loop_radial_next.link_loop_next.link_loop_next

        # if len(l.face.verts) != 4 and (not l.edge.is_manifold or not l.edge.is_boundary) and is_valid_edge(l.edge):
        #     l = next_loop.link_loop_next.link_loop_next

        if get_next_sel_loop(l, visited) is not None:
            next_loop = get_next_sel_loop(l, visited)
            visited.add(next_loop.edge)
        elif len([edge for edge in l.face.edges if edge.select]) == 2:
                next_loop = get_next_sel_loop(l)
                if metadata is not None:
                    if next_loop.edge in visited:
                        metadata.is_loop = True
                    metadata.active_loop = active_loop
                    metadata.shortest_edge_len = shortest_edge_len
                break
        
        elif len(l.face.verts) == 4 and (l.edge.is_manifold or l.edge.is_boundary) and l.edge not in visited and is_valid_edge(l.edge):
            next_loop = l
            visited.add(next_loop.edge)
        
        else:
            if metadata is not None:
                if next_loop.link_loop_radial_next.link_loop_next.link_loop_next.edge in visited:
                    metadata.is_loop = True
                metadata.active_loop = active_loop
                metadata.shortest_edge_len = shortest_edge_len
           
            break

# Adapted from blender source code
def get_edge_other_loop(edge: BMEdge, loop: BMLoop):
    other_loop = None

    other_loop = loop if loop.edge == edge else loop.link_loop_prev
    other_loop = other_loop.link_loop_radial_next

    if other_loop.vert == loop.vert:
       pass

    elif other_loop.link_loop_next.vert == loop.vert:
        other_loop = other_loop.link_loop_next
    else: 
        return None

    return other_loop

# Adapted from blender source code
def bm_vert_step_fan_loop(loop: BMLoop, edge_step: BMEdge):
    edge_prev = edge_step
    next_edge = None

    if loop is not None:
        if loop.edge == edge_prev:
            next_edge = loop.link_loop_prev.edge
        elif loop.link_loop_prev.edge == edge_prev:
            next_edge = loop.edge
        else:
            return None, None

        if (next_edge.is_manifold):
            edge_step = next_edge
            return get_edge_other_loop(next_edge, loop), edge_step

    return None, None

def get_edge_other_loop_r(edge: BMEdge, loop: BMLoop):
    other_loop = None

    other_loop = loop if loop.edge != edge else loop.link_loop_next
    other_loop = other_loop.link_loop_radial_next

    if other_loop.vert == loop.vert:
       pass

    elif other_loop.link_loop_prev.link_loop_prev.vert == loop.vert:
        other_loop = other_loop.link_loop_prev.link_loop_prev
    else: 
        return None

    return other_loop

def bm_vert_step_fan_loop_r(loop: BMLoop, edge_step: BMEdge):
    edge_prev = edge_step
    next_edge = None

    if loop is not None:
        if loop.edge == edge_prev:
            next_edge = loop.link_loop_radial_next.link_loop_next.edge
        elif loop.link_loop_prev.edge == edge_prev:
            next_edge = loop.edge
        else:
            return None, None

        if (next_edge.is_manifold):
            edge_step = next_edge
            return get_edge_other_loop_r(next_edge, loop), edge_step

    return None, None

def get_face_loop_for_edge(face: BMFace, edge: BMEdge) -> BMLoop:
    for loop in face.loops:
        if loop.edge.index == edge.index:
            return loop
    return None

# Adapted from blender source code
def bm_tri_fan_walker(bm, face, edge: BMEdge, metadata: WalkerMetadata=None):
    def rewind(loop: BMLoop):
        nonlocal start_loop
        next_loop = None
        next_edge = loop.edge
        while True:
            next_loop, next_edge = bm_vert_step_fan_loop(loop, next_edge)
            if next_loop is not None:
                pass
            else:
                return loop.link_loop_next.link_loop_next if loop.edge != next_edge else loop
    
            loop = next_loop
            
            if next_edge == start_loop.edge:
                return loop
    
    orig_start_loop = get_face_loop_for_edge(bm.faces[face], edge)
    start_loop = orig_start_loop

    start_loop = rewind(orig_start_loop)
    shortest_edge_len = float('INF')

    yield start_loop
    
    if start_loop.edge.index == orig_start_loop.edge.index:
        start_loop = orig_start_loop.link_loop_radial_next
    
    if start_loop.link_loop_next.edge.is_manifold:
        start_loop = start_loop.link_loop_next
    else:
        yield None
        return

    loop = start_loop
    next_loop = None
    next_edge = start_loop.edge
    done = False
    while True:
        if metadata is not None:
            edge_len = loop.edge.calc_length()
            if edge_len < shortest_edge_len:
                shortest_edge_len = edge_len

        yield loop

        if done:
            metadata.active_loop = orig_start_loop
            metadata.shortest_edge_len = shortest_edge_len
            break

        next_loop, next_edge = bm_vert_step_fan_loop_r(loop, next_edge)
        if next_loop is not None:
            pass
        else:
            next_loop = loop.link_loop_radial_next.link_loop_next if loop.edge != next_edge else loop
            done = True

        loop = next_loop
        
        if next_edge == start_loop.edge:
            metadata.is_loop = True
            metadata.active_loop = orig_start_loop
            metadata.shortest_edge_len = shortest_edge_len
            break
  

def bmesh_face_loop_walker(face: BMFace, start_loop=None, reverse=False):

    if start_loop is None:
        start_loop = face.loops[0]

    next_loop = start_loop
    test_condition = True
    while test_condition:
        yield next_loop

        
        next_loop = next_loop.link_loop_next if not reverse else next_loop.link_loop_prev
        test_condition = next_loop.index != start_loop.index

    
# This one doesnt compare loops with the index. Loops are difficult to set the index 
def bmesh_face_loop_walker_no_index(face: BMFace, start_loop=None, reverse=False):

    if start_loop is None:
        start_loop = face.loops[0]

    next_loop = start_loop
    test_condition = True
    while test_condition:
        yield next_loop
        
        next_loop = next_loop.link_loop_next if not reverse else next_loop.link_loop_prev
        test_condition = next_loop is not start_loop

#TODO: Avoid using this if possible.
def ensure(mesh: BMesh, update_loops=False, loops=None):
    mesh.edges.ensure_lookup_table()
    mesh.verts.ensure_lookup_table()
    mesh.faces.ensure_lookup_table()
    if update_loops:
        bmesh_loop_index_update(mesh, loops)

def get_vertex_shared_by_edges(edges) -> BMVert:
    verts = reduce(lambda x, y: (set(x) & set(y)), [edge.verts for edge in edges])
    if len(verts) == 1:
        return verts.pop()

    return None

def is_tri_fan(loops: List[BMLoop])-> bool:
    edge_set = {loop.edge for loop in loops[0:-1]}
    verts = get_vertex_shared_by_edges(edge_set)
    if verts and (edge_set == set(verts.link_edges)):
        return True
    return False

def get_loop_other_edge_loop(loop: BMLoop, vert: BMVert):
    return loop.link_loop_prev if loop.vert == vert else loop.link_loop_next

def get_shared_edge_for_verts(vert_a: BMVert, vert_b: BMVert) -> BMEdge:

    edge_set = set(vert_a.link_edges).intersection(set(vert_b.link_edges))
    if len(edge_set) > 0:
        return edge_set.pop()
    return None

def get_face_other_vert_loop(face: BMFace, vert_prev: BMVert, vert: BMVert):
    loop = get_face_loop_for_vert(face, vert)

    if loop is not None:
        if loop.link_loop_prev.vert == vert_prev:
            return loop.link_loop_next
        elif loop.link_loop_next.vert == vert_prev:
            return loop.link_loop_prev

def get_face_loop_for_vert(face: BMFace, vert: BMVert) -> BMLoop:
    for loop in face.loops:
        if loop.vert.index == vert.index:
            return loop
    return None

def bm_edge_is_single(edge: BMEdge):
    return edge.is_boundary and len(edge.link_loops[0].face.verts) > 4 \
        and  (edge.link_loops[0].link_loop_next.edge.is_boundary \
        or edge.link_loops[0].link_loop_prev.edge.is_boundary)

def bm_vert_edge_count_nonwire(vert: BMVert) -> int:
    return len([edge for edge in vert.link_edges if not edge.is_wire])

# Blender source code adaptation
def bmesh_edge_loop_walker(edge: BMEdge,  selected_edges_only=False, skip_rewind=False, yield_loop=False):
    def rewind(edge, vert, face_hub):

        vert = edge.verts[0]
        visited_edges = set()
        visited_edges.add(edge)

        curr_edge = edge
        last_vert = vert
        current_loop = None

        is_boundry = edge.is_boundary
        is_single = (edge.is_boundary and bm_edge_is_single(edge))

        reached_end = False
        while not reached_end:
            reached_end = True
            edge = curr_edge
            next_edge = None

            loop: BMLoop = edge.link_loops[0] if len(edge.link_loops) > 0 else None
            current_loop = loop
            if face_hub is not None: # Ngon Edge
                vert = edge.other_vert(last_vert)
                vert_edge_total = bm_vert_edge_count_nonwire(vert)

                if vert_edge_total == 3:
                    # Get face other vert loop
                    loop = get_face_other_vert_loop(face_hub, last_vert, vert)
                    next_edge = get_shared_edge_for_verts(vert, loop.vert)

                    if selected_edges_only and not next_edge.select:
                        reached_end = True
                        break

                    if next_edge not in visited_edges and not next_edge.is_boundary and not next_edge.hide:
                        reached_end = False
                        curr_edge = next_edge
                        last_vert = vert

                        visited_edges.add(next_edge)
                            
                else: # Escape out of the ngon face loop.
                    reached_end = False # Why was this False?
                    face_hub = None

            elif loop is None: # wire edge
                for i in range(2):
                    vert1 = edge.verts[1] if bool(i) else edge.verts[0]
                    for next_edge1 in vert1.link_edges:
                        loop = next_edge1.link_loops[0] if len(next_edge1.link_loops) > 0 else None
                        if next_edge1 not in visited_edges and loop is None and not next_edge1.hide:
                            reached_end = False
                            curr_edge = next_edge1
                            last_vert = vert1

                            visited_edges.add(next_edge1)
    
            elif not is_boundry: # normal edge with faces
                vert = edge.other_vert(last_vert)
                vert_edge_total = bm_vert_edge_count_nonwire(vert)

                if vert_edge_total == 4 or vert_edge_total == 2:
                    i_opposite = vert_edge_total / 2
                    i = 0

                    do = True
                    while do:
                        loop = get_loop_other_edge_loop(loop, vert)
                        if loop.edge.is_manifold:
                            loop = loop.link_loop_radial_next
                        else:
                            loop = None
                            break

                        i += 1
                        do = (i != i_opposite)
                else:
                    if yield_loop:
                        current_loop = loop
                    loop = None
                     
                if loop is not None:
                    if selected_edges_only and not loop.edge.select:
                        reached_end = True
                        break 

                    l2 = edge.link_loops[0]
                    if loop != l2 and loop.edge not in visited_edges and not loop.edge.hide:
                        reached_end = False
                        curr_edge = loop.edge
                        last_vert = vert
                        current_loop = loop
                        visited_edges.add(loop.edge)
                                            

            elif is_boundry: # Boundry edge with faces
                vert = edge.other_vert(last_vert)
                vert_edge_total = bm_vert_edge_count_nonwire(vert)

                # Walk over boundary of faces but stop at corners.
                if ((not is_single and vert_edge_total) > 2) or \
                    (is_single and vert_edge_total == 2 and edge.is_boundary):
                    #  ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^
                    # Initial edge was a boundary, so is this edge and vertex is only a part of this face?
                    # this lets us walk over the boundary of an ngon which is handy. 

                    while True:
                        loop = get_loop_other_edge_loop(loop, vert)
                        if loop.edge.is_manifold:
                            loop = loop.link_loop_radial_next
                        elif loop.edge.is_boundary:
                            break
                        else:
                            loop = None
                            break
                
                if not is_single and loop is not None and bm_edge_is_single(loop.edge):
                    loop = None

                if loop is not None:

                    if selected_edges_only and not loop.edge.select:
                        reached_end = True
                        break 

                    if loop != edge.link_loops[0] and loop.edge not in visited_edges and not loop.edge.hide:
                        reached_end = False
                        curr_edge = loop.edge
                        last_vert = vert
                        current_loop = loop
                        visited_edges.add(loop.edge)
                    elif yield_loop:
                        current_loop = loop
                    
        return curr_edge, last_vert, current_loop

    vert_edge_count = [len(vert.link_edges) for vert in edge.verts]

    vert_face_count = [len(vert.link_faces) for vert in edge.verts]

    vert = edge.verts[0]
    visited_edges = set()

    curr_edge = edge
    yeild_loop = None
    last_vert = vert

    is_boundry = edge.is_boundary
    is_single = (edge.is_boundary and bm_edge_is_single(edge))

    face_hub = None

    if not is_boundry and ((vert_edge_count[0] == 3 and vert_face_count[0] == 3) or \
        ((vert_edge_count[1] == 3 and vert_face_count[1] == 3))):

        face_best: BMFace = None

        for face in edge.link_faces:
            if face_best is None or len(face.verts) > len(face_best.verts):
                face_best = face
        
        if face_best is not None:
            face_hub = face_best if len(face_best.verts) > 4 else None
        else:
            face_hub = None
    else:
        face_hub = None
    
    # Rewind
    # insert last edge in rewind to visited set
    curr_edge, last_vert = edge, vert
    if not skip_rewind:
        curr_edge, last_vert, yeild_loop = rewind(edge, vert, face_hub)
        other_vert = curr_edge.other_vert(last_vert)
        if yield_loop:
            yield yeild_loop
    visited_edges.add(curr_edge)
    other_vert = curr_edge.other_vert(last_vert)
    last_vert = other_vert

    #Start the walker step code
    reached_end = False
    initial = False

    while not reached_end:
        yeild_loop = None
        reached_end = True
        edge = curr_edge 
        next_edge = None
        loop: BMLoop = edge.link_loops[0] if len(edge.link_loops) > 0 else None
        # if yield_loop and not initial:
        #     yield loop

        if face_hub is not None: # Ngon Edge
            vert = edge.other_vert(last_vert)
            vert_edge_total = bm_vert_edge_count_nonwire(vert)

            if vert_edge_total == 3:
                # Get face other vert loop
                loop = get_face_other_vert_loop(face_hub, last_vert, vert)
                next_edge = get_shared_edge_for_verts(vert, loop.vert)

                if selected_edges_only and not next_edge.select:
                    reached_end = True

                elif next_edge not in visited_edges and not next_edge.is_boundary and not next_edge.hide:
                    reached_end = False
                    curr_edge = next_edge
                    last_vert = vert
                    yeild_loop = loop

                    visited_edges.add(next_edge)
                
                # if selected_edges_only and not next_edge.select:
                #     reached_end = True

            else: # Escape out of the ngon face loop.
                reached_end = False # Why was this False? Oh because loop slice needs this
                face_hub = None

        elif loop is None: # wire edge
            # This fails when the wire edges are not sequential and branch off
            for i in range(2):
                
                vert1 = edge.verts[1] if bool(i) else edge.verts[0]
                for next_edge1 in vert1.link_edges:
                    loop = next_edge1.link_loops[0] if len(next_edge1.link_loops) > 0 else None
                    if next_edge1 not in visited_edges and loop is None and not next_edge1.hide:
                        reached_end = False
                        curr_edge = next_edge1
                        last_vert = vert1
                        yeild_loop = loop
                        visited_edges.add(next_edge1)
                        break

        elif not is_boundry: # normal edge with faces
            vert = edge.other_vert(last_vert)
            vert_edge_total = bm_vert_edge_count_nonwire(vert)

            if vert_edge_total == 4 or vert_edge_total == 2:
                i_opposite = vert_edge_total / 2
                i = 0

                do = True
                while do:
                    loop = get_loop_other_edge_loop(loop, vert)
                    if loop.edge.is_manifold:
                        loop = loop.link_loop_radial_next
                    else:
                        loop = None
                        break

                    i += 1
                    do = (i != i_opposite)
            else:
                # if yield_loop:
                #     yeild_loop = loop
                loop = None
                # loop = get_loop_other_edge_loop(loop, vert)
                # loop = loop.link_loop_radial_next

            if loop is not None:
                l2 = edge.link_loops[0]
                if loop != l2 and loop.edge not in visited_edges and not loop.edge.hide:
                    reached_end = False
                    curr_edge = loop.edge
                    last_vert = vert
                    yeild_loop =  loop
                    visited_edges.add(loop.edge)
                
                if selected_edges_only and not loop.edge.select:
                    reached_end = True


        elif is_boundry: # Boundry edge with faces
            vert = edge.other_vert(last_vert)
            vert_edge_total = bm_vert_edge_count_nonwire(vert)
            vert_edge_total = bm_vert_edge_count_nonwire(vert)

            # Walk over boundary of faces but stop at corners.
            if (not is_single and vert_edge_total) > 2 or \
                (is_single and vert_edge_total == 2 and edge.is_boundary):
                #  ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^
                # Initial edge was a boundary, so is this edge and vertex is only a part of this face?
                # this lets us walk over the boundary of an ngon which is handy. 

                while True:
                    loop = get_loop_other_edge_loop(loop, vert)
                    if loop.edge.is_manifold:
                        loop = loop.link_loop_radial_next
                    elif loop.edge.is_boundary:
                        break
                    else:
                        loop = None
                        break

            if not is_single and loop is not None and bm_edge_is_single(loop.edge):
                loop = None

            if loop is not None:
               
                if loop != edge.link_loops[0] and loop.edge not in visited_edges and not loop.edge.hide:
                    reached_end = False
                    curr_edge = loop.edge
                    last_vert = vert
                    yeild_loop = loop
                    visited_edges.add(loop.edge)

                if selected_edges_only and not loop.edge.select:
                    reached_end = True

        if not yield_loop:
            yield edge
        else:
            yield yeild_loop


def is_ngon(bm: BMesh, face):
    bm.faces.ensure_lookup_table()
    face: BMFace = bm.faces[face]

    return len(face.edges) >= 5

def get_face_from_index(bm: BMesh, face: int)-> BMFace:
    if face is None or not bm.is_valid:
        return None
        
    if face is None or not bm.is_valid:
        return None
        
    bm.faces.ensure_lookup_table()
    return bm.faces[face]

def get_active_vert(bm):
    if bm.select_history:
        element = bm.select_history[-1]
        if isinstance(element, BMVert):
            return element
    return None

import itertools
global_loop_index_counter = itertools.count()
def bmesh_loop_index_update(bm: BMesh, loops=None):
    if loops is None:
        #Slow ASF
        index = 0
        for face in bm.faces:
            for loop in face.loops:
                loop.index = index
                index += 1
    else:
    #Update Loops directly
       for loop in loops:
            loop.index = next(global_loop_index_counter)

def face_has_edges(face: BMFace, edges) -> bool:
    return len(set(edges).intersection(set(face.edges))) == len(edges)

def get_face_with_edges(edges) -> BMFace:
    assert (len(edges) >= 2)

    faces = {face for edge in edges for face in edge.link_faces}

    while len(faces) > 0:
        face = faces.pop()
        if face_has_edges(face, edges):
            return face
    return None

def face_has_verts(face: BMFace, verts) -> bool:
    return len(set(verts).intersection(set(face.verts))) == len(verts)

def get_face_with_verts(verts) -> BMFace:
    # assert (len(verts) >= 2)

    faces = {face for vert in verts for face in vert.link_faces}

    while len(faces) > 0:
        face = faces.pop()
        if face_has_verts(face, verts):
            return face
    return None


def get_face_edge_share_loop(face:BMFace, edge:BMEdge) -> BMLoop:
    loop_first = edge.link_loops[0]
    next_loop = loop_first

    condition = True
    while condition:
        if next_loop.face == face:
            return next_loop
        
        next_loop = next_loop.link_loop_radial_next
        condition = next_loop is not loop_first

def get_opposite_face_on_edge(face:BMFace, edge:BMEdge) -> BMFace:
    return get_face_edge_share_loop(face, edge).link_loop_radial_next.face

# def get_face_other_edge_loop(face: BMFace, edge: BMEdge, vert:BMVert):
#     loop = get_face_edge_share_loop(face, edge)
#     return get_loop_other_edge_loop(loop, vert)


def calc_face_loop_direction(loop: BMLoop) -> Vector:
    dir_vec = None
    vec_next: Vector = loop.link_loop_next.vert.co - loop.vert.co
    vec_prev: Vector = loop.vert.co - loop.link_loop_prev.vert.co

    vec_next.normalize()
    vec_prev.normalize()

    dir_vec: Vector = vec_next + vec_prev
    dir_vec.normalize()

    return dir_vec


def get_next_edge(loop: BMLoop, prev_edge: BMEdge, next_edge: BMEdge, next_vert: BMVert):
    first_loop = loop
    condition  = True

    i = 0
    while condition:
        loop = get_loop_other_edge_loop(loop, next_vert)

        e = loop.edge
        if e.index == next_edge.index:
            # if i == 0:
            #     return

            # if i >= 2:
            #     return 
            # # elif  i > 2:
            # #     return loop, vec_accum, (VertSlideType.FACE_MULTI_OUSET, (loop.face.index))
            # else:
            return
        i += 1
        
        l = loop.link_loop_radial_next
        yield l.edge
        condition = (loop.index != loop.link_loop_radial_next.index) and (l.index != first_loop.index)
        loop = l


def wire_edge_walker(edge):

    vert = edge.verts[0]
    visited_edges = set()

    curr_edge = edge
    last_vert = vert
  
    visited_edges.add(curr_edge)
    other_vert = curr_edge.other_vert(last_vert)
    last_vert = other_vert

    fringe = [curr_edge]
    while fringe:

        edge = fringe.pop()
        loop: BMLoop = edge.link_loops[0] if len(edge.link_loops) > 0 else None
        
        if loop is None:
            for i in range(2):
                
                vert1 = edge.verts[1] if bool(i) else edge.verts[0]
                for next_edge in vert1.link_edges:
                    loop = next_edge.link_loops[0] if len(next_edge.link_loops) > 0 else None
                    if next_edge not in visited_edges and loop is None and not next_edge.hide:
                        curr_edge = next_edge
                        last_vert = vert1
                        fringe.append(curr_edge)
                        visited_edges.add(next_edge)
                        break

        yield edge
   