//uniform mat4 ModelViewProjectionMatrix
// Uniform vec2 texCoord
// Uniform vec2 position

void main()
{



    // Object to world Mat
    // vec4 wpos = (ModelMatrix * vec4(position, 1.0));
    float bias_z = 0.005;

    vec4 pos = ModelViewProjectionMatrix * vec4(position, 1.0f);
    texCoord_interp = texCoord;
    pos.z -= bias_z;
    gl_Position = pos;
    //vec4 pos = vec4(wpos, 1.0);

    // gl_ClipDistance[0] = dot(WorldClipPlanes[0], pos);
    // gl_ClipDistance[1] = dot(WorldClipPlanes[1], pos);
    // gl_ClipDistance[2] = dot(WorldClipPlanes[2], pos);
    // gl_ClipDistance[3] = dot(WorldClipPlanes[3], pos);
    // gl_ClipDistance[4] = dot(WorldClipPlanes[4], pos);
    // gl_ClipDistance[5] = dot(WorldClipPlanes[5], pos);

}