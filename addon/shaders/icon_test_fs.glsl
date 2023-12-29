
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
float sdBox(in vec2 p, in vec2 b, in vec2 offset)
{
    float x = p.x - offset.x;
    float y = p.y - offset.y;
    p = vec2(x, y);
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

vec4 drawScene(vec2 uv, vec2 fragCoord) {
//   vec2 position = uv;
//   vec4 u_border_radius = vec4(1.,1.,1.,1.);
//   vec2 half_size = vec2(25.);

//   float border_radius_left = position.y > 0.0 ? u_border_radius.x : u_border_radius.y;
//   float border_radius_right = position.y > 0.0 ? u_border_radius.z : u_border_radius.w;
//   float border_radius = position.x < 0.0 ? border_radius_left : border_radius_right;

  //vec2 p = (2.0*fragCoord-iResolution.xy)/iResolution.y;
  vec4 col = vec4(1.);//getBackgroundColor(uv);
  //float d1 = sdCircle(uv, 0.1, vec2(0., 0.));
  //float d2 = sdSquare(uv, 0.05, vec2(0.0, 0.14));
  float thumb = sdBox(uv, vec2(0.05, 0.09), vec2(0.0, 0.11));
  float top = sdBox(uv, vec2(0.075, 0.017), vec2(0.0, 0.19));
  float pinShaft = sdBox(uv, vec2(0.015, .1), vec2(0.0, 0.0));
  float pinPoint = sdTriangleIsosceles(uv, vec2(0.015, 0.1), vec2(0.0, -0.19));
  //uv+= 0.5;
  float center = sdCutDisk(uv, 0.1, 0.005);
  float res; // result

  res = top;
  
//   res = min(thumb, top);
//   res = min(res, pinShaft);
//   res = min(res, pinPoint);
//   res = min(res, center);
  
  float _Smoothness = 0.0025;

  //res = min(d1, d2); // Union
  //res = max(d1, d2); // Intersect
  //res = max(-d1, d2); // Subtraction Subtract d1 from d2
  //res = max(d1, -d2); // Subtraction Subtract d2 from d1
  //res = max(min(d1, d2), -max(d1, d2)); // XOR
  
  //res = sMin(d1, d2, 0.05); // Smooth Union
   //res = sMax(d1, d2, 0.05); // smooth intersection

  //res = step(0., res); // Same as res > 0. ? 1. : 0.;
  // TODO
  //float pinPoint = sdTriangleIsosceles(uv, vec2(0.015, 0.1), vec2(0.0, -0.19));
  
  //float smoothedAlpha  = 1.0 - smoothstep(-edgeSoftness, edgeSoftness, pinPoint);
  //vec4  quadColor      = mix(vec4(1.0), vec4(0.0, 0.2, 1.0, smoothedAlpha), smoothedAlpha);
col = mix(vec4(1, 0, 0, 0.0), col, step(0., res));
  //col = mix(vec4(1, 0, 0, 0), col, smoothstep(-_Smoothness, _Smoothness, res));
  //col = mix(vec4(1, 0, 0, 0), col, smoothstep(-_Smoothness, _Smoothness, top));
  //col = mix(vec4(1, 0, 0, 0), col, smoothstep(-_Smoothness, _Smoothness, pinShaft));
  //col = mix(vec4(1, 0, 0, 0), col, smoothstep(-_Smoothness, _Smoothness, pinPoint));
  
  //col.a = mix(col.a, 0.0, aa);
  //col = mix(vec4(1,0,0,0), col, smoothstep(-_Smoothness, _Smoothness, d3));
  col.a = mix(col.a, 0.0, step(0., top));
  return col;
}

void main()
{
  //vec2 u_position = vec2(365, 750);
  float u_border_thickness = 0.;
  vec2 u_size = vec2(24, 24) * u_scale;
  

  vec2 position = gl_FragCoord.xy - u_position.xy - u_size / 2.0;

  position = rotate(position, PI/4);
  vec4 u_border_radius = vec4(1.,1.,1.,1.);
  vec2 half_size = u_size / 2.0 + u_border_thickness;

  float border_radius_left = position.y > 0.0 ? u_border_radius.x : u_border_radius.y;
  float border_radius_right = position.y > 0.0 ? u_border_radius.z : u_border_radius.w;
  float border_radius = position.x < 0.0 ? border_radius_left : border_radius_right;
  
  float y_offset = 5 * u_scale;//-10; //u_active == true ? 11. : 4; // 15 for down, 7 for up

  float thumb = sdBox(position, vec2(2 * u_scale, 5 * u_scale), vec2(0, 6 * u_scale-y_offset));
  float top = sdBox(position, vec2(4 * u_scale, 2 * u_scale), vec2(0, 11 * u_scale-y_offset));
  float pinShaft = sdBox(position, vec2(0.1 * u_scale, 3 * u_scale), vec2(0, -3 * u_scale-y_offset));
  //float pinPoint = sdTriangleIsosceles(position, vec2(-2, 10), vec2(0.0, -13-y_offset));

  position.y += y_offset;
  //position.x -= 1;
  float center = sdCutDisk(position, 5. * u_scale, 1. * u_scale);
  
  float res; // result
  //res = thumb;
  res = center;
  res = min(res, thumb);
  res = min(res, top);
  res = min(res, pinShaft);
  //res =  min(res, pinPoint);

  float width = .5;

  res = u_active == true ? res : abs(res) - width;

//res = min(res, pinShaft);

position = gl_FragCoord.xy - u_position.xy - u_size / 2.0;
vec2 b = half_size;
vec4 r = vec4(2.);

// float border = abs(sdRoundedBox(position, b, r)) - width;
// res = min(res, border);
  
float _Smoothness = 1.;

vec4 col = Color;
col = mix(vec4(Color.xyz, 0.), col, smoothstep(_Smoothness, -_Smoothness, res));
//col = mix(vec4(Color.xyz, 1.), col, smoothstep(-_Smoothness, _Smoothness, pinShaft));
fragColor = col;

// fragColor = Color; // Output to screen
// fragColor.a = mix(fragColor.a, 0.0, smoothstep(-_Smoothness, _Smoothness, res));

// fragColor.a = mix(fragColor.a, 0.0, step(0., pinShaft));

}



// void main()
// {

//     //vec2 u_position = vec2(278, 720);

//     float u_border_thickness = 0.;
//     vec2 u_size = vec2(16.0, 16.0);

//     vec2 position = gl_FragCoord.xy - u_position.xy - u_size / 2.0;
//     vec2 half_size = u_size / 2.0 + u_border_thickness;
//     //half_size.y = 5.;

//     vec4 u_border_radius = vec4(1.,1.,1.,1.);

//     float border_radius_left = position.y > 0.0 ? u_border_radius.x : u_border_radius.y;
//     float border_radius_right = position.y > 0.0 ? u_border_radius.z : u_border_radius.w;
//     float border_radius = position.x < 0.0 ? border_radius_left : border_radius_right;

//     float dist_outside = rect_sdf(position, half_size, border_radius);
//     //float outside_mask = smoothstep(-1.0, 1.0, dist_outside * 1.5);
//     //fragColor = mix(vec4(1, 0, 0, 1.0), vec4(1, 0, 0, 0.0), step(0., dist_outside));
//     if (u_border_thickness > 0.0)
//     {
//         vec4 u_border_color = vec4(1., 0., 0. , 1.);
//         float dist_inside = dist_outside + u_border_thickness;
//         float inside_mask = smoothstep(-1.0, 1.0, dist_inside * 1.5);
//         fragColor = mix(Color, u_border_color, inside_mask);
//     }
//     else
//     {
//         fragColor = Color;
//     }
    
//     // vec3 col = (dist_outside>0.0) ? vec3(0.9,0.6,0.3) : vec3(0.65,0.85,1.0);
    
// 	// col = mix( col, vec3(1.0), 1.0-smoothstep(0.0,0.01,abs(dist_outside)) );
//     // fragColor = vec4(col, 1.0);
//     fragColor.a = mix(fragColor.a, 0.0, step(0., dist_outside));
// }