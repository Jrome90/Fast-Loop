
void main()
{
    gl_Position = ModelViewProjectionMatrix * vec4(pos.xy, 0.0f, 1.0f);
    gl_Position.z = 1.0;

}