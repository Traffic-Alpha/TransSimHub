#version 150

in vec3 skybox_pos;
out vec4 color;

uniform vec3 sky_horizon_color;
uniform vec3 sky_zenith_color;

// City-builder style sky: stable, low-detail gradient.
// This avoids photoreal HDR horizons/reflections that look odd against low-poly roads.
void main() {
  vec3 d = normalize(skybox_pos);
  float t = smoothstep(-0.10, 0.72, d.z);
  vec3 sky = mix(sky_horizon_color, sky_zenith_color, t);
  color = vec4(sky, 1.0);
}
