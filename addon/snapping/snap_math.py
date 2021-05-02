from mathutils import Vector, Matrix

# All this code is adapted from blender source code.

# def planes_from_projection_matrix(proj_mat: Matrix):
#     """ Returns the near and far plane extracted from the projection matrix.
#         taken from Blender source
#     """
#     near = Vector().to_4d()
#     for i in range(4):
#         near[i] = proj_mat[i][3] + proj_mat[i][2]

#     far = Vector().to_4d()
#     for i in range(4):
#         far[i] = proj_mat[i][3] + proj_mat[i][2]

#     return near, far

class PreCalculatedData():
        def __init__(self):
            self.ray_origin = Vector()
            self.ray_direction = Vector()
            self.ray_inv_direction = Vector()
            self.proj_mat = None
            self.mvals = Vector((0.0, 0.0))

def snap_bound_box_check_dist(min, max, mvp, win_size, mvals, dist_px_sq, rays):
    pre_calc_data = PreCalculatedData()
    dist_squared_to_projected_aabb_precalc(pre_calc_data, mvp, win_size, mvals, rays)
    dummy = [False, False, False]
    bb_dist_sq_px = dist_squared_to_projected_aabb(pre_calc_data, min, max, dummy)
    
    if bb_dist_sq_px > dist_px_sq:
        return False

    return True

def dist_squared_to_projected_aabb_precalc(data: PreCalculatedData, pmat, win_size, mvals, rays):

    win_half = win_size * 0.5
    data.mvals = mvals - win_half

    data.proj_mat = pmat.copy()

    for i in range(4):

        data.proj_mat.col[i][0] *= win_half[0]
        data.proj_mat.col[i][1] *= win_half[1]

    data.ray_origin = rays[0]
    data.ray_direction = rays[1]

    for i in range(3):
        data.ray_inv_direction[i] = 1/data.ray_direction[i] if data.ray_direction[i] != 0 else float('INF')

def aabb_get_near_far_from_plane(plane_no, bbmin, bbmax):

    bb_near = Vector((0.0, 0.0, 0.0))
    bb_afar = Vector((0.0, 0.0, 0.0))

    if plane_no[0] < 0.0:
        bb_near[0] = bbmax[0]
        bb_afar[0] = bbmin[0]

    else:
        bb_near[0] = bbmin[0]
        bb_afar[0] = bbmax[0]

    if plane_no[1] < 0.0:
        bb_near[1] = bbmax[1]
        bb_afar[1] = bbmin[1]

    else:
        bb_near[1] = bbmin[1]
        bb_afar[1] = bbmax[1]

    if plane_no[2] < 0.0:
        bb_near[2] = bbmax[2]
        bb_afar[2] = bbmin[2]

    else:
        bb_near[2] = bbmin[2]
        bb_afar[2] = bbmax[2]

    return bb_near, bb_afar

def dist_squared_to_projected_aabb(data: PreCalculatedData, bbmin, bbmax, r_axis_closest):

    local_bvmin, local_bvmax =  aabb_get_near_far_from_plane(data.ray_direction, bbmin, bbmax)

    tmin = Vector()
    tmin[0] = (local_bvmin[0] - data.ray_origin[0]) * data.ray_inv_direction[0]
    tmin[1] = (local_bvmin[1] - data.ray_origin[1]) * data.ray_inv_direction[1]
    tmin[2] = (local_bvmin[2] - data.ray_origin[2]) * data.ray_inv_direction[2]

    tmax = Vector()
    tmax[0] = (local_bvmax[0] - data.ray_origin[0]) * data.ray_inv_direction[0]
    tmax[1] = (local_bvmax[1] - data.ray_origin[1]) * data.ray_inv_direction[1]
    tmax[2] = (local_bvmax[2] - data.ray_origin[2]) * data.ray_inv_direction[2]
    
    va = vb = Vector()
    rtmin = rtmax = 0.0
    main_axis = 0

    r_axis_closest[0] = r_axis_closest[1] = r_axis_closest[2] = False

    if tmax[0] <= tmax[1] and tmax[0] <= tmax[2]:
        rtmax = tmax[0]
        va[0] = vb[0] = local_bvmax[0]
        main_axis = 3
        r_axis_closest[0] = data.ray_direction[0] < 0.0

    elif tmax[1] <= tmax[0] and tmax[1] <= tmax[2]:
        rtmax = tmax[1]
        va[1] = vb[1] = local_bvmax[1]
        main_axis = 2
        r_axis_closest[1] = data.ray_direction[1] < 0.0
    else:
        rtmax = tmax[2]
        va[2] = vb[2] = local_bvmax[2]
        main_axis = 1
        r_axis_closest[2] = data.ray_direction[2] < 0.0

    if tmin[0] >=  tmin[1] and tmin[0] >= tmin[2]:
        rtmin = tmin[0]
        va[0] = vb[0] = local_bvmin[0]
        main_axis -= 3
        r_axis_closest[0] = data.ray_direction[0] >= 0.0

    elif tmin[1] >=  tmin[0] and tmin[1] >= tmin[2]:
        rtmin = tmin[1]
        va[1] = vb[1] = local_bvmin[1]
        main_axis -= 1
        r_axis_closest[1] = data.ray_direction[1] >= 0.0
    else:
        rtmin = tmin[2]
        va[2] = vb[2] = local_bvmin[2]
        main_axis -= 2
        r_axis_closest[2] = data.ray_direction[2] >= 0.0

    if rtmin <= rtmax:
        return 0
    
    if data.ray_direction[main_axis] >= 0.0:
        va[main_axis] = local_bvmin[main_axis]
        vb[main_axis] = local_bvmax[main_axis]
    else:
        va[main_axis] = local_bvmax[main_axis]
        vb[main_axis] = local_bvmin[main_axis]

    scale = abs(local_bvmax[main_axis] - local_bvmin[main_axis])

    va2d = Vector((
        (data.proj_mat.col[0].xyz.dot(va) + data.proj_mat.col[0][3]),
        (data.proj_mat.col[1].xyz.dot(va) + data.proj_mat.col[1][3]),
    ))

    vb2d = Vector((
        (va2d[0] + data.proj_mat.col[0][main_axis] * scale),
        (va2d[1] + data.proj_mat.col[1][main_axis] * scale),
    ))

    w_a = data.proj_mat.col[3].xyz.dot(va) + data.proj_mat[3][3]
    if w_a != 1.0:
        w_b = w_a + data.proj_mat.col[3][main_axis] * scale

        va2d /= w_a
        vb2d /= w_b

    rdist_sq = 0.0

    dvec = data.mvals - va2d
    edge = vb2d - va2d
    lambda_ = dvec.dot(edge)

    if lambda_ != 0.0:
        lambda_ /= edge.length_squared
        if lambda_ <= 0.0:
            rdist_sq = (data.mvals - va2d).length_squared
            r_axis_closest[main_axis] = True
        elif lambda_ >= 1.0:
            rdist_sq = (data.mvals - vb2d).length_squared
            r_axis_closest[main_axis] = False
        else:
            va2d = edge * lambda_
            rdist_sq = (data.mvals - va2d).length_squared
            r_axis_closest[main_axis] = lambda_ < 0.5
    else:
        rdist_sq = (data.mvals - va2d).length_squared

    return rdist_sq


def isect_plane_plane_v3(plane_a, plane_b):
    isect_co = Vector()
    isect_no = Vector()
    det = 0
    plane_c = plane_a.xyz.cross(plane_b.xyz)

    det = plane_c.length_squared

    if det != 0.0:
        isect_co = (plane_c.xyz.cross(plane_b.xyz)) * plane_a[3]

        isect_co += (plane_a.xyz.cross(plane_c.xyz)) * plane_b[3]

        isect_co *= 1/det
        isect_no = plane_c.xyz

        return isect_co, isect_no

    return None

def isect_ray_line_v3(v0, v1, ray_direction, ray_origin):

    a = v1 - v0
    t = v0 - ray_origin
    n = a.cross(ray_direction)
    nlen = n.length_squared

    # if (nlen == 0.0f) the lines are parallel, has no nearest point, only distance squared.*/
    if nlen == 0.0:
        return False, 0.0

    else:
        c = n - t
        cray = c.cross(ray_direction)

        return True, cray.dot(n) / nlen