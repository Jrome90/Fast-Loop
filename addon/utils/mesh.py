from functools import reduce
from math import isclose

from bmesh.types import *

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

def bmesh_face_loop_walker(face: BMFace):
    # Get the first loop
    next_loop = face.loops[0]
    test_condition = True
    while test_condition:
        yield next_loop

        next_loop = next_loop.link_loop_next
        test_condition = next_loop.index != face.loops[0].index

# 
# def bmesh_subdivide_edge(bm: BMesh, edge: BMEdge, vert: BMVert, n=1):
#     ret = []
#     current_vert = vert
#     current_edge = edge
#     for i in range(0, n):
#         percent = 1.0 / float((n + 1 - i))

#         new_edge, new_vert = bmesh.utils.edge_split(current_edge, current_vert, percent)
#         current_vert = new_edge.other_vert(new_vert)
#         current_edge = new_edge
#         ret.append((new_edge, new_vert))

#     bm.verts.index_update()
#     return ret


# def bmesh_scale(bm: BMesh, vec, space_mat: Matrix, verts):
#     scale_mat = Matrix()
#     scale_mat[0][0] = vec[0]
#     scale_mat[1][1] = vec[1]
#     scale_mat[2][2] = vec[2]

#     space_mat_inv = space_mat.inverted()
#     mat = space_mat_inv @ scale_mat @ space_mat

#     bm.verts.ensure_lookup_table()
#     for vert_idx in verts:
#         bm_vert = bm.verts[vert_idx]

#         bm_vert.co = mat @ bm_vert.co


def ensure(mesh: BMesh):
    mesh.edges.ensure_lookup_table()
    mesh.verts.ensure_lookup_table()
    mesh.faces.ensure_lookup_table()

def get_vertex_shared_by_edges(edges) -> BMVert:
    verts = reduce(lambda x, y: (set(x) & set(y)), [edge.verts for edge in edges])
    if len(verts) == 1:
        return verts.pop()

    return None

def face_has_edges(face: BMFace, edges) -> bool:
    return len(set(edges).intersection(set(face.edges))) == len(edges)


# def get_face_with_edges(edges) -> BMFace:
#     assert (len(edges) >= 2)

#     faces = {face for edge in edges for face in edge.link_faces}

#     while len(faces) > 0:
#         face = faces.pop()
#         if face_has_edges(face, edges):
#             return face
#     return None

# def get_loop_from_direction_and_edge_2(edge, dir_vec) -> BMLoop:
#     ''' Return the loop that has the same direction defined by vert_a and vert_b
#     '''
#     dir_vec.normalize()
#     thetas = []
#     for loop in edge.link_loops:
#         edge = loop.edge
#         l_vert = loop.vert
#         l_other_vert= edge.other_vert(l_vert)

#         l_dir_vec = l_other_vert.co - l_vert.co
#         l_dir_vec.normalize()

#         theta = dir_vec.dot(l_dir_vec)
#         thetas.append(theta)
#         if isclose(theta, 1.0, abs_tol=0.001) :
#             return loop

#     print("WTF")

# def get_loop_from_direction_and_vert(vert_a: BMVert, vert_b: BMVert) -> BMLoop:
#     ''' Return the loop that has the same direction defined by vert_a and vert_b
#     '''
#     dir_vec = (vert_b.co - vert_a.co)
#     dir_vec.normalize()
#     thetas = []
#     for loop in vert_a.link_loops:
#         edge = loop.edge
#         l_vert = loop.vert
#         l_other_vert= edge.other_vert(l_vert)

#         l_dir_vec = l_other_vert.co - l_vert.co
#         l_dir_vec.normalize()

#         theta = dir_vec.dot(l_dir_vec)
#         thetas.append(theta)
#         if isclose(theta, 1.0, abs_tol=0.001) :
#             return loop

#     print("WTF")

# def get_loop_from_direction_and_edge(vert_a: BMVert, vert_b: BMVert, edge: BMEdge) -> BMLoop:
#     ''' Return the edge's loop that has the same direction defined by vert_a and vert_b.
#         direction: vert_a -----> vert_b
        
#     '''
#     dir_vec = (vert_b.co - vert_a.co)
#     dir_vec.normalize()
#     thetas = []
#     for loop in edge.link_loops:
#         edge = loop.edge
#         l_vert = loop.vert
#         l_other_vert= edge.other_vert(l_vert)

#         l_dir_vec = l_other_vert.co - l_vert.co
#         l_dir_vec.normalize()

#         theta = dir_vec.dot(l_dir_vec)
#         thetas.append(theta)
#         if isclose(theta, 1.0, abs_tol=0.001) :
#             return loop
       
#     print(f"WTF: {edge.index}; verts:{vert_a.index}, {vert_b.index} ")
            

# def get_perc_along(vec_a: Vector, vec_b: Vector, vec_c: Vector) -> float:
#     """ Calculate the percent along a vector
#         Projects the vector ac onto the vector ab and then returns as a float the percentage along ab that ac is.
#         Args:
#             vec_a: Normalized vector.
#             vec_b: Normalized vector.
#             vec_c: Normalized vector.
#         Returns:
#             The percentage along the vector ab.
#     """

#     ab: Vector = vec_b - vec_a
#     ac: Vector = vec_c - vec_a

#     return ab.dot(ac) / ab.length_squared  # Why does dot() return a vector?

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
                
                if selected_edges_only and not loop.edge.select:
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