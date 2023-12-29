import pathlib

from gpu import shader, types

def _load_shaders(vertex_shader_source, fragment_shader_source, out_shader_info):

    folder = pathlib.Path(__file__).parent.parent.joinpath('shaders')

    out_shader_info.vertex_source(folder.joinpath(vertex_shader_source).read_text())
    out_shader_info.fragment_source(folder.joinpath(fragment_shader_source).read_text()) 


def create_2d_shader(vertex_shader="icon_vs.glsl", fragment_shader="icon_test_fs.glsl"):

    shader_2d_info = types.GPUShaderCreateInfo()
        
    # Defines vertex shader inputs and uniforms that are now called constants.
    
    shader_2d_info.vertex_in(0, 'VEC2', "pos")
    # shader_2d_info.vertex_in(1, 'VEC2', "texCoord")
    shader_2d_info.push_constant('FLOAT', "u_scale")
    shader_2d_info.push_constant('VEC2', "u_position")
    shader_2d_info.push_constant('MAT4', "ModelViewProjectionMatrix")
    shader_2d_info.push_constant('MAT4', "ModelMatrix")
    shader_2d_info.push_constant('VEC4', "Color")
    shader_2d_info.push_constant('BOOL', "u_active")

    # Define as Interface the attributes that will be transferred from the vertex shader to the fragment shader. 
    # Before they would be both a vertex shader output and fragment shader input.
    # An interface can be flat(), no_perspective() or smooth()
    # Warning: You need to give a string to the GPUStageInterfaceInfo() or the shader will not work. Any string will work.
    shader_2d_interface = types.GPUStageInterfaceInfo("shader_2d_interface")    
    shader_2d_interface.smooth('VEC2', "texCoord_interp")
    shader_2d_info.vertex_out(shader_2d_interface)

    # fragment shader output
    shader_2d_info.fragment_out(0, 'VEC4', 'fragColor')

    _load_shaders(vertex_shader, fragment_shader, shader_2d_info)
    created_shader = shader.create_from_info(shader_2d_info)
    del shader_2d_info
    del shader_2d_interface
    return created_shader


def create_3d_shader(vertex_shader, fragment_shader):

    shader_3d_info = types.GPUShaderCreateInfo()
        
    # Defines vertex shader inputs and uniforms that are now called constants.
    shader_3d_info.vertex_in(0, 'VEC3', "position")
    shader_3d_info.vertex_in(1, 'VEC2', "texCoord")
    shader_3d_info.push_constant('FLOAT', "u_scale")
    shader_3d_info.sampler(0, 'FLOAT_2D', "image")
    shader_3d_info.push_constant('FLOAT', "u_aspect_ratio")
    shader_3d_info.push_constant('VEC2', "u_size")
    shader_3d_info.push_constant('VEC2', "u_position")
    shader_3d_info.push_constant('MAT4', "ModelViewProjectionMatrix")
    shader_3d_info.push_constant('VEC4', "Color")

    # Define as Interface the attributes that will be transferred from the vertex shader to the fragment shader. 
    # Before they would be both a vertex shader output and fragment shader input.
    # An interface can be flat(), no_perspective() or smooth()
    # Warning: You need to give a string to the GPUStageInterfaceInfo() or the shader will not work. Any string will work.
    shader_3d_interface = types.GPUStageInterfaceInfo("shader_3d_interface")    
    shader_3d_interface.smooth('VEC2', "texCoord_interp")
    shader_3d_info.vertex_out(shader_3d_interface)

    # fragment shader output
    shader_3d_info.fragment_out(0, 'VEC4', 'fragColor')

    _load_shaders(vertex_shader, fragment_shader, shader_3d_info)
    created_shader = shader.create_from_info(shader_3d_info)
    del shader_3d_info
    del shader_3d_interface
    return created_shader