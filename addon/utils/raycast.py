from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d

from mathutils.geometry import intersect_line_line

def get_ray(region, rv3d, mouse_coords):
 
    ray_origin = region_2d_to_origin_3d(region, rv3d, mouse_coords)
    ray_dir_vec = region_2d_to_vector_3d(region, rv3d, mouse_coords)

    return ray_origin, ray_dir_vec

def get_mouse_line_isect(context, mouse_coords, p1, p2):
    mouse_pos, mouse_dir = get_ray(context.region, context.region_data, mouse_coords)
    _ , isect= intersect_line_line( p1, p2, mouse_pos, mouse_pos + (mouse_dir * 10000.0)) 
    return isect
