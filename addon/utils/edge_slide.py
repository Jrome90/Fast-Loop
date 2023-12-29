from typing import *
from collections import namedtuple
from dataclasses import dataclass, field
from math import cos, isclose

import bpy
from bmesh.types import *
from mathutils import Vector
from mathutils.geometry import intersect_point_line, intersect_line_plane

from .. import utils


from enum import Enum
class VertSlideType(Enum):
    NORMAL = 1
    FACE_INSET = 2
    FACE_OUTSET = 3
    FACE_MULTI_INSET = 4
    FACE_MULTI_OUSET = 5
    FACE_NGON = 6

@dataclass
class EdgeVertexSlideData():
    
    vert:int = None
    vert_orig_co: Vector = None
    vert_side: List[int] = field(default_factory=lambda: [None, None])
    dir_side: List[Vector] =  field(default_factory=lambda: [None, None])
    direction_edges: List[int] = field(default_factory=lambda: [None, None])
    edge_len: List[float] = field(default_factory=lambda: [None, None])

    slide_type: List[VertSlideType] = field(default_factory=lambda: [None, None])
    face_slide: List[tuple] = field(default_factory=lambda: [None, None])
    edge: int = None
    prev_edge: int = None
    # def __repr__(self) -> str:
    #     vert_side_a = self.vert_side[0].index if self.vert_side[0] is not None else None
    #     vert_side_b = self.vert_side[1].index if self.vert_side[1] is not None else None
    #     string = f"vert_side: a {vert_side_a}; b {vert_side_b} \n"
    #     string += f"dir_side: a {self.dir_side[0]}; b {self.dir_side[1]} \n"
    #     return string


class EdgeSlideReturnData():
    def  __init__(self):
        self.loop = None
        self.slide_type = None
        self.faces = None
        self.edge_slide_vec = None
        self.dir_vec = None

 
def calculate_edge_slide_directions(bm:BMesh, current_edge, selected_edge_indicies=None, return_edges=False):
    def add_to_return_edges(edge):
        if v.index not in edges_to_return:
            edges_to_return[v.index] = edge.index if edge is not None else None


    def edge_slide_vert_is_inner(vert: BMVert, edge_dir: BMEdge):
        return (not edge_dir.is_boundary) and len([edge for edge in vert.link_edges if not edge.is_wire]) == 2 
    
    def calculate_opposite_edge_co(edge_loop: BMLoop, plane_normal: Vector) -> Vector: 
        first_loop = edge_loop.link_loop_next
        last_loop = edge_loop.link_loop_prev

        min_dist = float('inf')
        return_co = None

        for loop in utils.mesh.bmesh_face_loop_walker(first_loop.face, first_loop):
            if loop.index == last_loop.index:
                break
            
            isect_co = intersect_line_plane(loop.vert.co, loop.link_loop_next.vert.co, edge_loop.vert.co, plane_normal)
            if isect_co is not None:
                _, fac = intersect_point_line(isect_co, loop.vert.co, loop.link_loop_next.vert.co)
                if fac > 1.192092896e-05 and fac < 1.0 + 1.192092896e-05:
                    dist = (edge_loop.vert.co - isect_co).length
                    if dist < min_dist:
                        min_dist = dist
                        return_co = isect_co
            
        return return_co
    #TODO If vert is inner and next ver is not selected do something else.
    # Perhaps if not ngon then force to be a normal slide
    # If ngon then use only singe edge to calculate direction
    def calculate_edge_slide(loop: BMLoop, prev_edge: BMEdge, next_edge: BMEdge, next_vert: BMVert):
        first_loop = loop
        condition  = True
        slide_vec = None

        vec_accum: Vector = Vector()
        vec_accum_len = 0.0
        i = 0
        while condition:
            loop = utils.mesh.get_loop_other_edge_loop(loop, next_vert)

            e = loop.edge
            if e.index == next_edge.index:
                if i != 0:
                    # Dont slide on edge
                    # loop_temp: BMLoop = utils.mesh.get_face_loop_for_vert(first_loop.face, next_vert)              

                    # vec_1 = (e.other_vert(next_vert).co - next_vert.co)
                    # vec_2 = first_loop.edge.other_vert(next_vert).co - next_vert.co
                    # f_tan = first_loop.edge.calc_tangent(first_loop)
                    # l_tan = loop_temp.edge.calc_tangent(loop)
                    # half_angle = f_tan.angle(l_tan)/2
                    # print(f"Factor: {1/cos(half_angle)}")

                    # vec_accum = f_tan+l_tan
                    # vec_accum = utils.math.normalize_vector(vec_accum, (vec_1.length + vec_2.length)/float(i))


                    # loop_temp: BMLoop = utils.mesh.get_face_loop_for_vert(first_loop.face, next_vert) 
                    # dir_vec = utils.mesh.calc_face_loop_direction(first_loop)
                    # vec_accum2 = loop_temp.face.normal.cross(dir_vec)

                    # # opposite_edge_co = calculate_opposite_edge_co(first_loop, dir_vec)
                    # # dist = 0.0
                    # # if opposite_edge_co is not None:
                    # #     dist = (loop_temp.vert.co - opposite_edge_co).length
                    # # else:
                    # dist = (prev_edge.calc_length() + next_edge.calc_length()) * 0.5
                    
                    # vec_accum = utils.math.normalize_vector(vec_accum, dist)

                    # f_tan = first_loop.edge.calc_tangent(first_loop.link_loop_radial_next)
                    # l_tan = loop.edge.calc_tangent(loop.link_loop_radial_next)
                    # half_angle = f_tan.angle(l_tan)/2
                    # factor = 1/cos(half_angle)
                    # vec_accum.normalize()
                    # vec_accum *= factor
                    
                    # return loop, vec_accum, (VertSlideType.FACE_NGON, loop.face.index)

                    # dir_vec = utils.mesh.calc_face_loop_direction(loop_temp)

                    # vec_1: Vector = loop_temp.link_loop_next.vert.co - loop_temp.vert.co
                    # vec_2: Vector = loop_temp.vert.co - loop.vert.co #loop_temp.link_loop_radial_next.link_loop_next.vert.co

                    # vec_1: Vector = first_loop.edge.other_vert(first_loop.vert).co - first_loop.vert.co
                    # vec_2: Vector = loop.edge.other_vert(loop.vert).co - loop.vert.co

                    # vec_1.normalize()
                    # vec_2.normalize()
                    

                    # Comment this out if not sliding on rails (Loop slide)   
                    if i == 1: #and not len(next_vert.link_edges) >= 3:
                        test = list(utils.mesh.get_next_edge(loop.link_loop_radial_next, next_edge, prev_edge, next_vert))
                        if len(test) <= 1:

                            f_tan = first_loop.edge.calc_tangent(first_loop)
                            l_tan = loop.edge.calc_tangent(loop)
                            half_angle = f_tan.angle(l_tan)/2
                            # angle_signed = vec_1.cross(vec_2)
                            # half_angle = vec_1.angle(vec_2)/2
                            # print(f"Factor: {1/cos(half_angle)}")
                            factor = 1/cos(half_angle)

                            # vec_accum = f_tan+l_tan
                            vec_accum = utils.math.normalize_vector(vec_accum, vec_accum_len/float(i))
                            # vec_accum.normalize()
                            # vec_accum *= factor


                            return loop, vec_accum, (VertSlideType.NORMAL, (loop.face.index,)) #(False, None)
                    # Faces = NamedTuple("Faces", ('first', 'second'))
                    # faces = Faces(first_loop.face.index, loop.face.index)

                    # print(f"First Loop Face: {first_loop.face}")
                    # print(f"Last Loop Face: {loop.face}")
                    f_tan = first_loop.edge.calc_tangent(first_loop)
                    l_tan = loop.edge.calc_tangent(loop)
                    half_angle = f_tan.angle(l_tan)/2
                    # angle_signed = vec_1.cross(vec_2)
                    # half_angle = vec_1.angle(vec_2)/2
                    # print(f"Factor: {1/cos(half_angle)}")
                    factor = 1/cos(half_angle)

                    vec_accum = f_tan+l_tan
                    
                    #vec_accum = utils.math.normalize_vector(vec_accum, vec_accum_len/float(i))
                    
                    #vec_accum = calculate_opposite_edge_co(first_loop, utils.mesh.calc_face_loop_direction(first_loop).normalized())
                    vec_accum.normalize()
                    vec_accum *= factor
                    # print("Not a normal edge slide. Other side is inset or outset")
                    return loop, vec_accum, (VertSlideType.FACE_OUTSET, (first_loop.face.index, loop.face.index))# (True, loop.face.index)
                # elif  i > 2:
                #     return loop, vec_accum, (VertSlideType.FACE_MULTI_OUSET, (loop.face.index))
                    # It's either a normal edge slide or an inset that has an additional single edge 

                    

                    # vec_accum = utils.math.normalize_vector(vec_accum, vec_accum_len/float(i))
                # if slide_vec is not None:
                #     return loop, slide_vec, (False, None)
                else:
                    loop_temp: BMLoop = utils.mesh.get_face_loop_for_vert(first_loop.face, next_vert)            
                    if len(loop_temp.face.edges) == 4:
                        # slide_vec = (loop_temp.link_loop_next.link_loop_next.vert.co - next_vert.co)
                        # return loop, slide_vec, (VertSlideType.FACE_INSET, loop_temp.face.index)
                        
                        # dir_vec = utils.mesh.calc_face_loop_direction(loop_temp)
                        # vec_accum = loop_temp.face.normal.cross(dir_vec)

                        # vec_1: Vector = loop_temp.link_loop_next.vert.co - loop_temp.vert.co
                        # vec_2: Vector = loop_temp.vert.co - loop_temp.link_loop_prev.vert.co
                        vec_1 = (e.other_vert(next_vert).co - next_vert.co)
                        vec_2 = first_loop.edge.other_vert(next_vert).co - next_vert.co

                        f_tan = first_loop.edge.calc_tangent(first_loop)
                        l_tan = loop_temp.edge.calc_tangent(loop)
                        half_angle = f_tan.angle(l_tan)/2
                        # print(f"Factor: {1/cos(half_angle)}")
                        factor = 1/cos(half_angle)
                        #f_tan.normalize()
                        vec_accum = f_tan + l_tan

                        vec_accum = utils.math.normalize_vector(vec_accum, (vec_1.length + vec_2.length)/float(2))
                        vec_accum.normalize()

                        vec_accum *= factor

                        #vec_accum = (loop.face.calc_center_median() - loop_temp.vert.co)


                        return loop, vec_accum, (VertSlideType.FACE_INSET, (loop_temp.face.index,))
                    else:
                        #Ngon
                        dir_vec = utils.mesh.calc_face_loop_direction(loop_temp)
                        vec_accum = loop_temp.face.normal.cross(dir_vec)

                        opposite_edge_co = calculate_opposite_edge_co(loop_temp, dir_vec)
                        dist = 0.0
                        if opposite_edge_co is not None:
                            dist = (loop_temp.vert.co - opposite_edge_co).length
                        else:
                            dist = (prev_edge.calc_length() + next_edge.calc_length()) * 0.5
                        
                        utils.math.normalize_vector(vec_accum, dist)

                        f_tan = first_loop.edge.calc_tangent(first_loop)
                        l_tan = loop_temp.edge.calc_tangent(loop)
                        half_angle = f_tan.angle(l_tan)/2
                        # print(f"Factor: {1/cos(half_angle)}")
                        factor = 1/cos(half_angle)

                        vec_accum *= factor
                        
                        return loop, vec_accum, (VertSlideType.FACE_NGON, (loop.face.index,))

                # if i >= 2:
                #     # loop_temp: BMLoop = utils.mesh.get_face_loop_for_vert(first_loop.face, next_vert) 
                #     # dir_vec = utils.mesh.calc_face_loop_direction(first_loop)
                #     # vec_accum2 = loop_temp.face.normal.cross(dir_vec)

                #     # # opposite_edge_co = calculate_opposite_edge_co(first_loop, dir_vec)
                #     # # dist = 0.0
                #     # # if opposite_edge_co is not None:
                #     # #     dist = (loop_temp.vert.co - opposite_edge_co).length
                #     # # else:
                #     # dist = (prev_edge.calc_length() + next_edge.calc_length()) * 0.5
                    
                #     # vec_accum = utils.math.normalize_vector(vec_accum, dist)

                #     # f_tan = first_loop.edge.calc_tangent(first_loop.link_loop_radial_next)
                #     # l_tan = loop.edge.calc_tangent(loop.link_loop_radial_next)
                #     # half_angle = f_tan.angle(l_tan)/2
                #     # factor = 1/cos(half_angle)
                #     # vec_accum.normalize()
                #     # vec_accum *= factor
                    
                #     # return loop, vec_accum, (VertSlideType.FACE_NGON, loop.face.index)

                #     # dir_vec = utils.mesh.calc_face_loop_direction(loop_temp)

                #     # vec_1: Vector = loop_temp.link_loop_next.vert.co - loop_temp.vert.co
                #     # vec_2: Vector = loop_temp.vert.co - loop.vert.co #loop_temp.link_loop_radial_next.link_loop_next.vert.co

                #     # vec_1: Vector = first_loop.edge.other_vert(first_loop.vert).co - first_loop.vert.co
                #     # vec_2: Vector = loop.edge.other_vert(loop.vert).co - loop.vert.co

                #     # vec_1.normalize()
                #     # vec_2.normalize()

                #     print(f"First Loop Face: {first_loop.face}")
                #     print(f"Last Loop Face: {loop.face}")
                #     f_tan = first_loop.edge.calc_tangent(first_loop)
                #     l_tan = loop.edge.calc_tangent(loop)
                #     half_angle = f_tan.angle(l_tan)/2
                #     # angle_signed = vec_1.cross(vec_2)
                #     # half_angle = vec_1.angle(vec_2)/2
                #     print(f"Factor: {1/cos(half_angle)}")
                #     factor = 1/cos(half_angle)

                #     vec_accum = f_tan+l_tan
                #     vec_accum = utils.math.normalize_vector(vec_accum, vec_accum_len/float(i))
                #     vec_accum.normalize()
                
                #     # if vec_accum.dot((f_tan+l_tan).normalized()) > 0:
                #     #     print("Inset")
                #     # else:
                #     #     print("Outset")
                #     vec_accum *= factor
                #     return loop, vec_accum, (VertSlideType.FACE_OUTSET, (first_loop.face.index, loop.face.index))# (True, loop.face.index)
                # # elif  i > 2:
                # #     return loop, vec_accum, (VertSlideType.FACE_MULTI_OUSET, (loop.face.index))
                # else:
                #     # It's either a normal edge slide or an inset that has an additional single edge 
                #     test = list(utils.mesh.get_next_edge(loop.link_loop_radial_next, next_edge, prev_edge, next_vert))
                #     if len(test) > 1:
                #         # Need to force this edge to not be considered a normal edge slide
                #         print("Not a normal edge slide. Other side is inset or outset")

                    

                #     return loop, vec_accum, (VertSlideType.NORMAL, (loop.face.index)) #(False, None)

            # Calc Slide vec
            slide_vec: Vector = (e.other_vert(next_vert).co - next_vert.co)
            vec_accum_len += slide_vec.length
            vec_accum += slide_vec
            i += 1

            if utils.mesh.get_loop_other_edge_loop(loop, next_vert).edge.index == next_edge.index:
                if i != 0:
                    loop_temp: BMLoop = utils.mesh.get_face_loop_for_vert(first_loop.face, next_vert)              
                    # Dont slide on edge
                    vec_1 = (e.other_vert(next_vert).co - next_vert.co)
                    vec_2 = first_loop.edge.other_vert(next_vert).co - next_vert.co
                    f_tan = first_loop.edge.calc_tangent(first_loop)

                    loop_temp2 = loop_temp.link_loop_radial_next.link_loop_next 
                    l_tan = loop_temp2.edge.calc_tangent(loop_temp2)
                    half_angle = f_tan.angle(l_tan)/2
                    # print(f"Factor: {1/cos(half_angle)}")

                    vec_accum = f_tan+l_tan
                    vec_accum = utils.math.normalize_vector(vec_accum, (vec_1.length + vec_2.length)/float(i))
                    # vec_accum = utils.math.normalize_vector(vec_accum, vec_accum_len/float(i))
                    return utils.mesh.get_loop_other_edge_loop(utils.mesh.get_loop_other_edge_loop(loop, next_vert), next_vert), vec_accum, (VertSlideType.FACE_OUTSET, (utils.mesh.get_loop_other_edge_loop(loop, next_vert).face.index,)) #(False, None)

                # return utils.mesh.get_loop_other_edge_loop(loop, next_vert), slide_vec, (False, None)
            
            l = loop.link_loop_radial_next
            condition = (loop.index != loop.link_loop_radial_next.index) and (l.index != first_loop.index)
            loop = l
        
        # if i != 0:
        #     vec_accum = normalize_vector(vec_accum, vec_accum_len/float(i))

        return None, None, (None, None)

    def get_next_edge(vert: BMVert, edge: BMEdge, edges):
        for next_edge in vert.link_edges:
            if next_edge.index in edges and next_edge.index != edge.index:
                return next_edge

    # def is_vert_selected(vert: BMVert):
    #     return len([edge for edge in vert.link_edges if edge.select]) > 0
    
    if current_edge is None:
        return False
    
    slide_verts: Dict[int, EdgeVertexSlideData] = {}
    edges_to_return = {}
    prev_edge = None

    edge_indicies = None
    if selected_edge_indicies is not None:
        edge_indicies = selected_edge_indicies
    else:
        edge_indicies = list(utils.mesh.bmesh_edge_loop_walker(current_edge, selected_edges_only=True))

    edges = {edge for edge in edge_indicies}

    bm.edges.ensure_lookup_table()

    #current_edge = #bm.edges[edge_indicies[0]]
    first_vert = current_edge.verts[0]
    last_edge = None #first_vert.link_edges[0]#edges_l[-1]

    for edge in first_vert.link_edges:
        if edge.index in edges:
            last_edge = edge
            break

    vert = first_vert
    edge = last_edge #current_edge
    visited = {edge}
    while True:
        
        edge = get_next_edge(vert, edge, edges)
        if edge is not None and edge not in visited:
            visited.add(edge)
            last_edge = edge
        else:
            edge = last_edge
            break
        
        vert = edge.other_vert(vert)
        # if not is_vert_selected(vert):
        #     break
        
        

        # if edge.index == last_edge.index:
        #     break

    first_edge = edge
    vec_a = None
    vec_b = None

    l_a: BMLoop = edge.link_loops[0]
    l_b = l_a.link_loop_radial_next

    

    fs_a = (VertSlideType.NORMAL, None)
    fs_b = (VertSlideType.NORMAL, None)
    
    v = vert

    add_to_return_edges(edge)

    next_edge = get_next_edge(v, edge, edges)
    if next_edge is not None:
        _, vec_a, fs_a = calculate_edge_slide(l_a, edge, next_edge, v)

    else:
        # pass
        l_tmp = utils.mesh.get_loop_other_edge_loop(l_a, v)
        if edge_slide_vert_is_inner(v, l_tmp.edge):
            pass
            _, vec_a, fs_a = calculate_edge_slide(l_a, edge, l_tmp.edge, v)
            print(f"Vert is inner {v.index}")

        #TEST
        # _, vec_a, _ = get_slide_edge(l_a, edge, v)
        #ORIG
        else:
            vec_a = (l_tmp.edge.other_vert(v).co - vert.co)

    if l_a.index != l_b.index:

        next_edge = get_next_edge(v, edge, edges)
        if next_edge is not None:
            _, vec_b, fs_b = calculate_edge_slide(l_b, edge, next_edge, v)
            
        else:
            l_tmp = utils.mesh.get_loop_other_edge_loop(l_b, v)
            if edge_slide_vert_is_inner(v, l_tmp.edge):
                pass
                _, vec_b, fs_b = calculate_edge_slide(l_b, edge, l_tmp.edge, v)
                print(f"Vert is inner {v.index}")
             #TEST
            # _, vec_b, fs_b = calculate_edge_slide(l_b, l_tmp.edge, edge, v)
            #ORIG
            else:
                vec_b = (l_tmp.edge.other_vert(v).co - vert.co)

    else:
        l_b = None
        
    l_a_prev = None
    l_b_prev = None

    prev_vert = None

    condition = True
    while condition:
        slide_verts[v.index] = EdgeVertexSlideData()
        sv: EdgeVertexSlideData = slide_verts[v.index]
        sv.vert = v.index
        sv.vert_orig_co = v.co.copy()
        current_edge = edge
        sv.edge = current_edge.index
        
        if prev_edge is not None:
            sv.prev_edge = prev_edge.index
        else:
            tmp_prev_edge = get_next_edge(v, edge.other_vert(v), edges)
            if tmp_prev_edge is not None:
                sv.prev_edge = tmp_prev_edge.index
            else:
                sv.prev_edge = None

        if l_a is not None or l_a_prev is not None:
            l_tmp: BMLoop = utils.mesh.get_loop_other_edge_loop(l_a if l_a is not None else l_a_prev, v)
            if vec_a is not None:
                sv.vert_side[0] = l_tmp.edge.other_vert(v).index
                sv.direction_edges[0] = l_tmp.edge.index
                sv.dir_side[0] = vec_a
                sv.edge_len[0] = vec_a.length
                sv.slide_type[0] = fs_a[0]
                sv.face_slide[0] = fs_a[1]
                

                add_to_return_edges(edge)

            else:
                print("vec_a is none")

        if l_b is not None or l_b_prev is not None:
            l_tmp: BMLoop = utils.mesh.get_loop_other_edge_loop(l_b if l_b is not None else l_b_prev, v)
            if vec_b is not None:
                sv.vert_side[1] = l_tmp.edge.other_vert(v).index
                sv.dir_side[1] = vec_b
                sv.direction_edges[1] = l_tmp.edge.index
                sv.edge_len[1] = vec_b.length
                sv.slide_type[1] = fs_b[0]
                sv.face_slide[1] = fs_b[1]

                #edges_to_return.append(l_b)
                add_to_return_edges(edge)

            else:
                print("vec_b is none")
        prev_vert = v
        v = edge.other_vert(v)

        prev_edge = edge
        edge = get_next_edge(v, edge, edges)  

        
        if edge is None:
            slide_verts[v.index] = EdgeVertexSlideData()
            sv: EdgeVertexSlideData = slide_verts[v.index]
            sv.vert = v.index
            sv.vert_orig_co = v.co.copy()

            sv.edge = l_a.edge.index
            sv.prev_edge = prev_edge.index

            if l_a is not None: #and (len(v.link_edges) > 3 or l_a.edge.is_boundary):
                l_tmp = utils.mesh.get_loop_other_edge_loop(l_a, v)
                if edge_slide_vert_is_inner(v, l_tmp.edge):
                    pass
                    _, vec_a, fs_a = calculate_edge_slide(l_a, prev_edge, l_tmp.edge, v)
                    sv.vert_side[0] = vert.index
                    sv.dir_side[0] = vec_a
                    sv.direction_edges[0] = l_tmp.edge.index
                    sv.edge_len[0] = vec_a.length
                    sv.slide_type[0] = fs_a[0]
                    sv.face_slide[0] = fs_a[1]
                else:
                    vert = l_tmp.edge.other_vert(v)
                    # _, vec_a, _ = get_slide_edge(l_a, l_tmp.edge, v)
                    sv.vert_side[0] = vert.index
                    sv.dir_side[0] = (vert.co - v.co) #TODO make it option to slide not on edge
                    sv.direction_edges[0] = l_tmp.edge.index
                    sv.edge_len[0] = sv.dir_side[0].length
                    sv.slide_type[0] = VertSlideType.NORMAL
                    sv.face_slide[0] = None
                add_to_return_edges(edge)

            if l_b is not None :
                l_tmp = utils.mesh.get_loop_other_edge_loop(l_b, v)
                if edge_slide_vert_is_inner(v, l_tmp.edge):
                    pass
                    _, vec_b, fs_b = calculate_edge_slide(l_b, prev_edge, l_tmp.edge, v)
                    sv.vert_side[1] = vert.index
                    sv.dir_side[1] = vec_b
                    sv.direction_edges[1] = l_tmp.edge.index
                    sv.edge_len[1] = vec_b.length
                    sv.slide_type[1] = fs_b[0]
                    sv.face_slide[1] = fs_b[1]
                else:
                    vert = l_tmp.edge.other_vert(v)
                    # _, vec_b, _ = get_slide_edge(l_a, l_tmp.edge, v)
                    sv.vert_side[1] = vert.index
                    sv.dir_side[1] = (vert.co - v.co)
                    sv.direction_edges[1] = l_tmp.edge.index
                    sv.edge_len[1] = sv.dir_side[1].length
                    sv.slide_type[1] = VertSlideType.NORMAL
                    sv.face_slide[1] = None
                    # sv.face_slide[1] = False

                    # edges_to_return.append(l_b)
                add_to_return_edges(edge)

            break 

        l_a_prev = l_a
        l_b_prev = l_b

        if l_a is not None:
            l_a, vec_a, fs_a = calculate_edge_slide(l_a, prev_edge, edge, v)
            # vec_a = None
            #edges_to_return.append(l_a)

        else:
            vec_a = Vector()
        
        if l_b is not None:
            l_b, vec_b, fs_b = calculate_edge_slide(l_b, prev_edge, edge, v)
            #edges_to_return.append(l_b)
        else:
            vec_b = Vector()

        # prev_edge = current_edge
        condition = edge.index != first_edge.index and (l_a is not None or l_b is not None)

    if not return_edges:
        return slide_verts
    else:
        return slide_verts, edges_to_return