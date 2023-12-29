
#define PI 3.14159265

vec2 rotate(vec2 uv, float th) {
  return mat2(cos(th), sin(th), -sin(th), cos(th)) * uv;
}


float sMin(float a, float b, float k)
{
    float h = clamp(0.5+0.5*(b-a)/k, 0.0, 1.0);
    return mix(b, a, h) - k*h*(1.0-h);
}

float sMax(float a, float b, float k)
{
    return -sMin(-a, -b, k);
}


vec4 getBackgroundColor(vec2 uv) {
  uv = uv * 0.5 + 0.5; // remap uv from <-0.5,0.5> to <0.25,0.75>
  vec4 gradientStartColor = vec4(1., 0., 1., 1.);
  vec4 gradientEndColor = vec4(0., 1., 1., 1.);
  return mix(gradientStartColor, gradientEndColor, uv.y); // gradient goes from bottom to top
}

float sdCircle(vec2 uv, float r, vec2 offset) {
  float x = uv.x - offset.x;
  float y = uv.y - offset.y;

  return length(vec2(x, y)) - r;
}

float sdSquare(vec2 uv, float size, vec2 offset) {
  float x = uv.x - offset.x;
  float y = uv.y - offset.y;

  return max(abs(x), abs(y)) - size;
}

// Box - exact   (https://www.youtube.com/watch?v=62-pRVZuS5c)
float sdBox(in vec2 p, in vec2 b)
{
    // float x = p.x - offset.x;
    // float y = p.y - offset.y;
    // p = vec2(x, y);
    vec2 d = abs(p)-b;
    return length(max(d,0.0)) + min(max(d.x,d.y),0.0);
}


// Rounded Box - exact   (https://www.shadertoy.com/view/4llXD7 and https://www.youtube.com/watch?v=s5NGeUV2EyU)
float sdRoundedBox( in vec2 p, in vec2 b, in vec4 r )
{
    r.xy = (p.x>0.0)?r.xy : r.zw;
    r.x  = (p.y>0.0)?r.x  : r.y;
    vec2 q = abs(p)-b+r.x;
    return min(max(q.x,q.y),0.0) + length(max(q,0.0)) - r.x;
}

// Isosceles Triangle - exact   (https://www.shadertoy.com/view/MldcD7)

float sdTriangleIsosceles( in vec2 p, in vec2 q, in vec2 offset)
{

    float x = p.x - offset.x;
    float y = p.y - offset.y;
    p = vec2(x, y);
    
    p.x = abs(p.x);
    vec2 a = p - q*clamp( dot(p,q)/dot(q,q), 0.0, 1.0 );
    vec2 b = p - q*vec2( clamp( p.x/q.x, 0.0, 1.0 ), 1.0 );
    float s = -sign( q.y );
    vec2 d = min( vec2( dot(a,a), s*(p.x*q.y-p.y*q.x) ),
                  vec2( dot(b,b), s*(p.y-q.y)  ));
    return -sqrt(d.x)*sign(d.y);
}

// Cut Disk - exact   (https://www.shadertoy.com/view/ftVXRc)
float sdCutDisk( in vec2 p, in float r, in float h )
{
    //p = rotate(p, PI);

    float w = sqrt(r*r-h*h); // constant for any given shape
    p.x = abs(p.x);
    float s = max( (h-r)*p.x*p.x+w*w*(h+r-2.0*p.y), h*p.x-w*p.y );
    return (s<0.0) ? length(p)-r :
           (p.x<w) ? h - p.y     :
                     length(p-vec2(w,h));
}

float rect_sdf(vec2 p, vec2 s, float r)
{
    vec2 d = abs(p) - s + vec2(r);
    return min(max(d.x, d.y), 0.0) + length(max(d, 0.0)) - r;   
}

// Segment - exact   (https://www.shadertoy.com/view/3tdSDj and https://www.youtube.com/watch?v=PMltMdi1Wzg)
float sdSegment( in vec2 p, in vec2 a, in vec2 b )
{
    vec2 pa = p-a, ba = b-a;
    float h = clamp( dot(pa,ba)/dot(ba,ba), 0.0, 1.0 );
    return length( pa - ba*h );
}

float invLerp(float from, float to, float value){
  return (value - from) / (to - from);
}

void main()
{
  vec2 u_position = vec2(0, 0);
  float u_border_thickness = 0.;
  //vec2 u_size = vec2(64.0, 64.0);

  vec2 position = texCoord_interp.xy; //- u_size / 2.0;

  //position = rotate(position, PI/4);
  vec4 u_border_radius = vec4(1.,1.,1.,1.);
  //vec2 half_size = u_size / 2.0 + u_border_thickness;

  float y_offset = 0.; //u_active == true ? 11. : 4; // 15 for down, 7 for up
  float x_offset = 0.;

  //float center = sdCutDisk(position, 5., 0.);
  
  float res; // result
  vec2 size = u_size;
  size.x *= u_aspect_ratio;

  // Remap the coords to the center
  //position = (position-0.5) * 2.0;
  position.x *= u_aspect_ratio;
  vec2 shaft_pos = position;
  shaft_pos.y += -.5;
 
  //float shaft = sdSegment(position, vec2((1.0 - 0.5), 0.), vec2((-1.0 + 0.5)*u_aspect_ratio, 0.)) - 0.03;//sdBox(position, size);

//   vec2 arrow_r_pos = rotate(position,-PI/2);
//   arrow_r_pos.y += 1.;
//   float arrow_right = sdTriangleIsosceles(arrow_r_pos, vec2(0.1* u_scale, 0.1* u_scale/u_aspect_ratio), vec2(0,0));

//   vec2 arrow_l_pos = rotate(position, PI/2);
//   arrow_l_pos.y += 1.;
//   float arrow_left = sdTriangleIsosceles(arrow_l_pos, vec2(0.1* u_scale, 0.1* u_scale/u_aspect_ratio), vec2(0,0));

// position.x /= u_aspect_ratio;
//position.y = clamp(position.y, -0.5, 0.5);
float line_width = 0.02 * u_scale;

float offset = 0.1;
float fac = invLerp(0., u_aspect_ratio, u_aspect_ratio - offset);
float right_arrow_pos = fac * u_aspect_ratio;
float shaft = sdSegment(shaft_pos, vec2((offset), 0.), vec2(right_arrow_pos, 0.) ) - line_width;

float arrow_offset = 0.07*1.70710;
float arrow_left_top = sdSegment(shaft_pos, vec2((offset), 0.), vec2(offset + arrow_offset, arrow_offset) ) - line_width;
float arrow_left_bottom = sdSegment(shaft_pos, vec2((offset), 0.), vec2(offset + arrow_offset, -arrow_offset) ) - line_width;

float arrow_right_top = sdSegment(shaft_pos, vec2(right_arrow_pos, 0.), vec2(right_arrow_pos - arrow_offset, -arrow_offset) ) - line_width;
float arrow_right_bottom = sdSegment(shaft_pos, vec2((right_arrow_pos), 0.), vec2(right_arrow_pos - arrow_offset, arrow_offset) ) - line_width;

res = shaft;
res = min(res, arrow_left_top);
res = min(res, arrow_left_bottom);
res = min(res, arrow_right_top);
res = min(res, arrow_right_bottom);

float _Smoothness = 0.0005;

// vec4 col = Color;
// //col = mix(col, vec4(Color.xyz, 1.), step(0., res));
// //col = mix(vec4(Color.xyz, 1.), col, smoothstep(-_Smoothness, _Smoothness, pinShaft));
// fragColor = vec4(vec3(1.), 0.);
// if (res > 0.5)
// {
fragColor = Color; // Output to screen

//fragColor = mix(fragColor, vec4(1., 0., 0., 1.), step(0.0, texCoord_interp.x*u_aspect_ratio) - step(10.0, texCoord_interp.x*u_aspect_ratio));
//fragColor = mix(fragColor, vec4(1., 0., 0., 1.), step(0.5, texCoord_interp.x));
// }
// else
// {
// discard;
// }

    //sdf distance per pixel (gradient vector)
    vec2 ddist = vec2(dFdx(res), dFdy(res));

    // distance to edge in pixels (scalar)
    float pixelDist = res / length(ddist);

    fragColor.a = clamp(0.3 - pixelDist, 0., Color.a); 


//fragColor.a = mix(fragColor.a, 0.0, 1-smoothstep(pixelDist, pixelDist, res));
//fragColor = mix(fragColor, vec4(1., 0., 0., 1.), step(0.0, texCoord_interp.x));

//fragColor.a = mix(fragColor.a, 0.0, step(0.0, res));

}