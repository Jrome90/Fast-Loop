void main()
{
    vec2 uv = texCoord_interp;

    uv.x *= u_aspect_ratio;
    fragColor = texture(image, uv);

    fragColor = mix(vec4(uv, 0.0, 1.0), fragColor, 0.5); 

    if (uv.x < 0.1 && uv.y < 0.1)
    {
        fragColor = vec4(1., 1., 1., 1.);
    }
    else if (uv.x > 0.9 * u_aspect_ratio && uv.x < 1. * u_aspect_ratio && uv.y < 0.1)
    {
        fragColor = vec4(1., 0., 0., 1.);
    }
    else if (uv.x < 0.1 && uv.y > 0.9 && uv.y < 1.)
    {
        fragColor = vec4(0., 1., 0., 1.);
    }
    else if (uv.x > 0.9 * u_aspect_ratio && uv.x < 1. * u_aspect_ratio && uv.y > 0.9 &&  uv.y < 1.)
    {
        fragColor = vec4(1., 1., 0., 1.);
    }
}