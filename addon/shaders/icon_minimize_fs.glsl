
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
float sdBox(vec2 p, vec2 b, vec2 offset)
{
    float x = p.x - offset.x;
    float y = p.y - offset.y;
    p = vec2(x, y);
    vec2 d = abs(p)-b;
    return length(max(d,0.0)) + min(max(d.x,d.y),0.0);
}


// Rounded Box - exact   (https://www.shadertoy.com/view/4llXD7 and https://www.youtube.com/watch?v=s5NGeUV2EyU)
float sdRoundedBox( vec2 p, vec2 b, vec4 r )
{
    r.xy = (p.x>0.0)?r.xy : r.zw;
    r.x  = (p.y>0.0)?r.x  : r.y;
    vec2 q = abs(p)-b+r.x;
    return min(max(q.x,q.y),0.0) + length(max(q,0.0)) - r.x;
}

// Isosceles Triangle - exact   (https://www.shadertoy.com/view/MldcD7)

float sdTriangleIsosceles( vec2 p, vec2 q, vec2 offset)
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
float sdCutDisk( vec2 p, float r, float h )
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
float sdSegment(vec2 p, vec2 a, vec2 b )
{
    vec2 pa = p-a, ba = b-a;
    float h = clamp( dot(pa,ba)/dot(ba,ba), 0.0, 1.0 );
    return length( pa - ba*h );
}

void main()
{
  //vec2 u_position = vec2(278, 720);
  float u_border_thickness = 0.;
  vec2 u_size = vec2(24.0, 24.0) * u_scale;

  vec2 position = gl_FragCoord.xy - u_position.xy - u_size / 2.0;

  //position = rotate(position, PI/4);
  vec4 u_border_radius = vec4(1.,1.,1.,1.);
  vec2 half_size = u_size / 2.0 + u_border_thickness;

  float border_radius_left = position.y > 0.0 ? u_border_radius.x : u_border_radius.y;
  float border_radius_right = position.y > 0.0 ? u_border_radius.z : u_border_radius.w;
  float border_radius = position.x < 0.0 ? border_radius_left : border_radius_right;
  
  float y_offset = 0; //u_active == true ? 11. : 4; // 15 for down, 7 for up
  float x_offset = 0;

  //float center = sdCutDisk(position, 5., 0.);
  
  float res; // result
  res = sdBox(position, vec2(5 * u_scale, 1 * u_scale), vec2(x_offset, y_offset));
  if (u_active == true)
  {
    float horizontal_rect = sdBox(position, vec2(1 * u_scale, 5 * u_scale), vec2(x_offset, y_offset));
    res = min(res, horizontal_rect);
  }

//   res = min(res, thumb);
//   res = min(res, top);
  //res = min(res, pinShaft);
  //res =  min(res, pinPoint);

  float width = .5;

// res = u_active == true ? res : res;

// position = gl_FragCoord.xy - u_position.xy - u_size / 2.0;
// vec2 b = half_size;
// vec4 r = vec4(2.);

// float border = abs(sdRoundedBox(position, b, r)) - width;
// res = min(res, border);
  
float _Smoothness = 0.55;

// vec4 col = Color;
// //col = mix(col, vec4(Color.xyz, 1.), step(0., res));
// //col = mix(vec4(Color.xyz, 1.), col, smoothstep(-_Smoothness, _Smoothness, pinShaft));
// fragColor = vec4(vec3(1.), 0.);

fragColor = Color; // Output to screen
fragColor.a = mix(fragColor.a, 0.0, smoothstep(-_Smoothness, _Smoothness, res));

// fragColor.a = mix(fragColor.a, 0.0, step(0., pinShaft));

}