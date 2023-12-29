from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from .snapping import SnapObjectEditMeshData

from bmesh.types import *
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_point_line

from . import snap_math

# This isn't what I'd consider utilities

@dataclass
class SnapEdgeParams():
    snap_object = None
    edge_index: int = None

    ray_origin: Vector = None
    ray_direction: Vector = None
    radius: float = None
    win_size: float = None
    mval: Vector = Vector((0.0, 0.0))

    proj_matrix: Matrix = None
    is_perpective: bool = False

def do_raycast(snap_object: SnapObjectEditMeshData, origin: Vector, direction: Vector)-> None | Tuple:
            while True:
                isect_co, _, face_index, distance = snap_object.bvh_tree.ray_cast(
                    origin, direction)
                bm = snap_object.bm
                if face_index is None:
                    return None
            
                try:
                    face = bm.faces[face_index]
                except IndexError:
                    bm.faces.ensure_lookup_table()
                    continue
                
                if face is not None and not face.hide:
                    return isect_co, face, distance
                elif face is not None and face.hide:
                    origin = isect_co + direction*0.0001


def cb_snap_edge(params: SnapEdgeParams)-> None | Tuple:
    current_object = params.snap_object
    bm = current_object.bm
    bm.edges.ensure_lookup_table()
    edge: BMEdge = bm.edges[params.edge_index]
    va_co = edge.verts[0].co
    vb_co = edge.other_vert(edge.verts[0]).co

    nearest_co = _test_projected_edge_dist(params, (va_co, vb_co))
    if nearest_co is not None:
        _, perc = intersect_point_line(nearest_co, va_co, vb_co)
        if perc < 0.0:
            return va_co, 0.0
        elif perc > 1.0:
            return vb_co, 1.0
        elif 0.0 <= perc <= 1.0:
            return va_co.lerp(vb_co, perc), perc

    return None


def _test_projected_edge_dist(params, verts_co)-> None | Vector:
    va_co, vb_co = verts_co
    intersects, lambda_ = snap_math.isect_ray_line_v3(
        va_co, vb_co, params.ray_direction, params.ray_origin)
    near_co = Vector()

    if not intersects:
        near_co = va_co.copy()
    else:
        if lambda_ <= 0.0:
            near_co = va_co.copy()
        elif lambda_ >= 1.0:
            near_co = vb_co.copy()
        else:
            near_co = va_co.lerp(vb_co, lambda_)

        if _test_projected_vert_dist(params, near_co):
            return near_co
    return None


def _test_projected_vert_dist(params, co)-> bool:

    win_half = params.win_size * 0.5
    mvals = params.mval - win_half
    current_object = params.snap_object
    co = current_object.object_matrix @ co

    proj_mat = params.proj_matrix

    for i in range(4):
        proj_mat.col[i][0] *= win_half[0]
        proj_mat.col[i][1] *= win_half[1]

    pro_mat = proj_mat.to_3x3()

    row_x = pro_mat.row[0]
    row_y = pro_mat.row[1]

    co_2d = Vector((
        row_x.dot(co) + proj_mat.col[3][0],
        row_y.dot(co) + proj_mat.col[3][1]
    ))

    if params.is_perpective:
        w = (proj_mat.col[0][3] * co[0]) + (proj_mat.col[1][3] * co[1]) + (proj_mat.col[2][3] * co[2]) + proj_mat.col[3][3]
        co_2d /= w
    dist_sq = (mvals - co_2d).length

    dist_px_sq = params.radius
    if dist_sq < dist_px_sq:
        return True
    return False