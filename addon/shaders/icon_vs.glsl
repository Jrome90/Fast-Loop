//uniform mat4 ModelViewProjectionMatrix
// Uniform vec2 texCoord
// Uniform vec2 pos

void main()
{
    gl_Position = ModelViewProjectionMatrix * vec4(pos.xy, 0.0f, 1.0f);
    gl_Position.z = 1.0;
    //texCoord_interp = texCoord;
}