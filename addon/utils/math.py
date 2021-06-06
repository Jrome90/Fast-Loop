from math import isclose

import bpy

from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_point_line
                            

def is_point_on_line_segment(point, vec_a, vec_b, abs_tol=1e-10):
    dist, lambda_ = dist_to_line_segment_squared(point, vec_a, vec_b)
    if 0.0 <= lambda_ <= 1.0:
        return isclose(dist, 0.0, abs_tol=abs_tol)
    return False

def dist_to_line_segment_squared(point, vec_a, vec_b):
    cp , l = closest_to_line(point, vec_a, vec_b)
    return (point - cp).length_squared, l

def closest_to_line(point, vec_a, vec_b)-> Vector:
    o: Vector = vec_a
    d: Vector = vec_a - vec_b
    h: Vector = point - o
    lambda_ = d.dot(h)/d.length_squared

    return (o + d * lambda_), -lambda_

def project_point_plane(point: Vector, plane_n: Vector):
    """ Project a point onto the plane.

        Args:
            point: The point to project.
            plane_n: Normalized vector perpendicular to the plane.
    """
    proj_vec = point.project(plane_n)
    return point - proj_vec


def ray_plane_intersection(ray_origin, ray_dir_vec, plane_origin,  plane_n):
    denom = ray_dir_vec.dot(plane_n)
    if denom == 0:
        return 0
    
    return ((plane_origin) - ray_origin).dot(plane_n) / denom


def remap(imin, imax, omin, omax, v, clamp=False):
    
    if imax - imin == 0:
         return 1/v
    new_val = (v - imin) / (imax - imin) * (omax - omin) + omin

    if clamp:
        if (omin < omax):
            return clamp(omin, new_val, omax)
        else:
            return clamp(omax, new_val, omin)

    return new_val

def scale_points(vec, space_mat: Matrix, points):
    ret = []
    scale_mat = Matrix()
    scale_mat[0][0] = vec[0]
    scale_mat[1][1] = vec[1]
    scale_mat[2][2] = vec[2]

    space_mat_inv = space_mat.inverted()
    mat = space_mat_inv @ scale_mat @ space_mat

    for point in points:
        point = mat @ point
        ret.append(point)

    return ret

def scale_points_about_origin(points, origin, factor):
    mat = Matrix.Translation((-origin[0], -origin[1], -origin[2]))

    return scale_points([factor, factor, factor], mat, points)

def scale_points_along_line(points, start, end, factor):
    origin = (start + end) * 0.5

    return scale_points_about_origin(points, origin, factor)

def constrain_point_to_line_seg(min: Vector, point: Vector, max: Vector):
    """ Constrain a point to the range of the line segment defined by the min and max vectors.
        
        Args:

            min: Vector that defines the start of the segment.
            point: The point we are constraining. 
            max: Vector that defines the end of the segment.

        Returns:
            percent < 0: min.
            percent > 1: max
            0 <= percent <=1: point
    """
    _, percent = intersect_point_line(point, min, max)
    if  0.0 <= percent <= 1.0:
        return point
    elif percent < 0.0:
        return min
    else:
        return max

def clamp(minvalue, value, maxvalue):
    return max(minvalue, min(value, maxvalue))


def location_3d_to_2d(loc: Vector):
    context = bpy.context
    return location_3d_to_region_2d(context.region, context.space_data.region_3d, loc)