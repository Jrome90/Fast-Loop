from functools import reduce

from bmesh.types import *
from mathutils import Vector

# Blender source code adaptation returns a loop rather than an edge
def bmesh_edge_ring_walker(edge: BMEdge):
    def rewind(loop):
        visited = set()
        visited.add(loop.edge)
        loop = loop.link_loop_radial_next

        next_loop = loop

        while True:
            l = next_loop.link_loop_radial_next.link_loop_next.link_loop_next
            if len(l.face.verts) != 4 and (not l.edge.is_manifold or not l.edge.is_boundary) and not l.edge.hide :
                l = next_loop.link_loop_next.link_loop_next

            if len(l.face.verts) == 4 and (l.edge.is_manifold or l.edge.is_boundary) and not l.edge.hide and l.edge not in visited:
                next_loop = l
                visited.add(next_loop.edge)
            else:
                break

        return next_loop

    loop = edge.link_loops[0]
    next_loop = rewind(loop).link_loop_radial_next
    visited = set()
    visited.add(next_loop.edge)

    while True:
        yield next_loop
        l = next_loop.link_loop_radial_next.link_loop_next.link_loop_next

        if len(l.face.verts) != 4 and (not l.edge.is_manifold or not l.edge.is_boundary) and not l.edge.hide:
            l = next_loop.link_loop_next.link_loop_next

        if len(l.face.verts) == 4 and (l.edge.is_manifold or l.edge.is_boundary) and not l.edge.hide and l.edge not in visited:
            next_loop = l
            visited.add(next_loop.edge)
        else:
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
def bm_tri_fan_walker(bm, face, edge: BMEdge):
    def rewind(loop: BMLoop, edge: BMEdge):
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

    start_loop = rewind(orig_start_loop, edge)

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
        yield loop

        if done:
            break

        next_loop, next_edge = bm_vert_step_fan_loop_r(loop, next_edge)
        if next_loop is not None:
            pass
        else:
            next_loop = loop.link_loop_radial_next.link_loop_next if loop.edge != next_edge else loop
            done = True

        loop = next_loop
        
        if next_edge == start_loop.edge:
            break
  

def bmesh_face_loop_walker(face: BMFace):
    # Get the first loop
    next_loop = face.loops[0]
    test_condition = True
    while test_condition:
        yield next_loop

        next_loop = next_loop.link_loop_next
        test_condition = next_loop.index != face.loops[0].index

def ensure(mesh: BMesh):
    mesh.edges.ensure_lookup_table()
    mesh.verts.ensure_lookup_table()
    mesh.faces.ensure_lookup_table()

def get_vertex_shared_by_edges(edges) -> BMVert:
    verts = reduce(lambda x, y: (set(x) & set(y)), [edge.verts for edge in edges])
    if len(verts) == 1:
        return verts.pop()

    return None

def get_loop_other_edge_loop(loop: BMLoop, vert: BMVert):
    return loop.link_loop_prev if loop.vert == vert else loop.link_loop_next

def get_shared_edge_for_verts(vert_a: BMVert, vert_b: BMVert) -> BMEdge:

    edge_set = set(vert_a.link_edges).intersection(set(vert_b.link_edges))
    if len(edge_set) > 0:
        return edge_set.pop()

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

# Blender source code adaptation
def bmesh_edge_loop_walker(edge: BMEdge,  selected_edges_only=False, skip_rewind=False):
    def rewind(edge, vert, face_hub):

        vert = edge.verts[0]
        visited_edges = set()
        visited_edges.add(edge)

        curr_edge = edge
        last_vert = vert

        is_boundry = edge.is_boundary
        is_single = (edge.is_boundary and bm_edge_is_single(edge))

        reached_end = False
        while not reached_end:
            reached_end = True
            edge = curr_edge
            next_edge = None
            loop: BMLoop = edge.link_loops[0] if len(edge.link_loops) > 0 else None

            if face_hub is not None: # Ngon Edge
                vert = edge.other_vert(last_vert)
                vert_edge_total = len(vert.link_edges)

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

            elif loop is None: # wire edge
                for i in range(2):
                    vert1 = edge.verts[1] if bool(i) else edge.verts[0]
                    for next_edge1 in vert1.link_edges:
                        loop = next_edge1.link_loops[0] if len(next_edge1.link_loops) > 0 else None
                        if next_edge1 not in visited_edges and loop is None and not next_edge1.hide:
                            reached_end = False
                            curr_edge = next_edge1
                            last_vert = vert1

                            visited_edges.add(next_edge)
    
            elif not is_boundry: # normal edge with faces
                vert = edge.other_vert(last_vert)
                vert_edge_total = len(vert.link_edges)

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

                        visited_edges.add(loop.edge)

            elif is_boundry: # Boundry edge with faces
                vert = edge.other_vert(last_vert)
                vert_edge_total = len(vert.link_edges)

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

                    if selected_edges_only and not loop.edge.select:
                        reached_end = True
                        break 

                    if loop != edge.link_loops[0] and loop.edge not in visited_edges and not loop.edge.hide:
                        reached_end = False
                        curr_edge = loop.edge
                        last_vert = vert

                        visited_edges.add(loop.edge)
                    
        return curr_edge, last_vert

    vert_edge_count = [len(vert.link_edges) for vert in edge.verts]

    vert_face_count = [len(vert.link_faces) for vert in edge.verts]

    vert = edge.verts[0]
    visited_edges = set()

    curr_edge = edge
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
        curr_edge, last_vert = rewind(edge, vert, face_hub)
        other_vert = curr_edge.other_vert(last_vert)

    visited_edges.add(curr_edge)
    other_vert = curr_edge.other_vert(last_vert)
    last_vert = other_vert


    #Start the walker step code
    reached_end = False
    while not reached_end:
  
        reached_end = True
        edge = curr_edge
        next_edge = None
        loop: BMLoop = edge.link_loops[0] if len(edge.link_loops) > 0 else None

        if face_hub is not None: # Ngon Edge
            vert = edge.other_vert(last_vert)
            vert_edge_total = len(vert.link_edges)

            if vert_edge_total == 3:
                # Get face other vert loop
                loop = get_face_other_vert_loop(face_hub, last_vert, vert)
                next_edge = get_shared_edge_for_verts(vert, loop.vert)

                if next_edge not in visited_edges and not next_edge.is_boundary and not next_edge.hide:
                    reached_end = False
                    curr_edge = next_edge
                    last_vert = vert

                    visited_edges.add(next_edge)
                
                if selected_edges_only and not next_edge.select:
                    reached_end = True

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
            vert_edge_total = len(vert.link_edges)

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
                loop = None
            
            if loop is not None:
                l2 = edge.link_loops[0]
                if loop != l2 and loop.edge not in visited_edges and not loop.edge.hide:
                    reached_end = False
                    curr_edge = loop.edge
                    last_vert = vert

                    visited_edges.add(loop.edge)
                
                if selected_edges_only and not loop.edge.select:
                    reached_end = True


        elif is_boundry: # Boundry edge with faces
            vert = edge.other_vert(last_vert)
            vert_edge_total = len(vert.link_edges)

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

                    visited_edges.add(loop.edge)

                if selected_edges_only and not loop.edge.select:
                    reached_end = True
        
        yield edge

def is_ngon(bm: BMesh, face):
    bm.faces.ensure_lookup_table()
    face: BMFace = bm.faces[face]

    return len(face.edges) >= 5

def is_tri(bm: BMesh, face):
    bm.faces.ensure_lookup_table()
    face: BMFace = bm.faces[face]

    return len(face.edges) == 3

def get_face_from_index(bm: BMesh, face: int)-> BMFace:
    bm.faces.ensure_lookup_table()
    return bm.faces[face]

