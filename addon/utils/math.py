from math import isclose

import bpy

from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_point_line
                            

def is_point_on_line_segment(point, vec_a, vec_b, abs_tol=1e-6):
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
    denom = plane_n.dot(ray_dir_vec)
    if denom == 0:
        return 0
    
    return (plane_origin - ray_origin).dot(plane_n) / denom


def remap(imin, imax, omin, omax, v, clamp_val=False):
    
    if imax - imin == 0:
         return 1/v
    new_val = (v - imin) / (imax - imin) * (omax - omin) + omin

    if clamp_val:
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


def location_3d_to_2d(loc: Vector, context_override=None):
    region = None
    rv3d = None
    if context_override is None:
        context =  bpy.context
        region = context.region
        rv3d = context.space_data.region_3d
    else:
        region = context_override["region"]
        rv3d = context_override["space"].region_3d

    return location_3d_to_region_2d(region, rv3d, loc)


def inv_lerp(a, b, value):
    ab = b - a
    av = value - a

    d = ab.dot(ab)

    if d != 0.0:
        return av.dot(ab) / d
    
    return 0.0


def normalize_vector(vec:Vector, unit_len):
    normalized_vec = None
    d = vec.dot(vec)
    if d > 1.0e-35:
        d = d**0.5
        normalized_vec = vec * (unit_len/d)
    else:
        normalized_vec = Vector()
        
    return normalized_vec


def ortho_basis_from_normal(normal: Vector):
    epsilon = 1.192092896e-07
    len_sq = normal.x**2 + normal.y**2
    if len_sq > epsilon:
        d = 1.0 / (len_sq**0.5)

        ortho_vec_a = Vector()
    
        ortho_vec_a[0] = normal.y * d
        ortho_vec_a[1] = -normal.x * d
        ortho_vec_a[2] = 0.0

        ortho_vec_b = normal.cross(ortho_vec_a)

        return ortho_vec_a, ortho_vec_b
    else:
        ortho_vec_a = Vector()
        ortho_vec_b = Vector()

        ortho_vec_a.x = -1 if normal.y < 0 else 1
        ortho_vec_a.y = 0
        ortho_vec_a.z = 0

        ortho_vec_b.x = 0
        ortho_vec_b.y = 1
        ortho_vec_b.z = 0

        return ortho_vec_a, ortho_vec_b

def basis_mat_from_plane_normal(normal:Vector)->Matrix:
    basis_mat = Matrix().to_3x3()

    x, y = ortho_basis_from_normal(normal)
    if x is not None and y is not None:
        basis_mat[0] = x
        basis_mat[1] = y
        basis_mat[2] = normal

        basis_mat.transpose()
        return basis_mat

def rotate_direction_vec(vec: Vector, rot_mat: Matrix)-> Vector:
    return rot_mat.to_quaternion() @ vec

def cm_to_meters(cms):
        return cms / 100

def meters_to_cm(meters):
    return meters * 100

def mm_to_meters(mms):
    return mms / 1000

def meters_to_mm(meters):
    return meters * 1000