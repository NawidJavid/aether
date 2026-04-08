// 'position' is injected by Three.js from the geometry's position attribute
attribute vec3 targetPos;
attribute float jitter;

uniform float u_time;
uniform float u_morphProgress;
uniform float u_audioAmplitude;
uniform float u_pointSize;
uniform vec3 u_mousePos;
uniform float u_mouseRadius;

varying float v_intensity;

//
// Ashima Arts 3D Simplex Noise
// https://github.com/ashima/webgl-noise
// Copyright (C) 2011 Ashima Arts. All rights reserved.
// Distributed under the MIT License.
//

vec3 mod289(vec3 x) {
  return x - floor(x * (1.0 / 289.0)) * 289.0;
}

vec4 mod289(vec4 x) {
  return x - floor(x * (1.0 / 289.0)) * 289.0;
}

vec4 permute(vec4 x) {
  return mod289(((x * 34.0) + 10.0) * x);
}

vec4 taylorInvSqrt(vec4 r) {
  return 1.79284291400159 - 0.85373472095314 * r;
}

float snoise(vec3 v) {
  const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);

  // First corner
  vec3 i  = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);

  // Other corners
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);

  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;

  // Permutations
  i = mod289(i);
  vec4 p = permute(permute(permute(
             i.z + vec4(0.0, i1.z, i2.z, 1.0))
           + i.y + vec4(0.0, i1.y, i2.y, 1.0))
           + i.x + vec4(0.0, i1.x, i2.x, 1.0));

  // Gradients: 7x7 points over a square, mapped onto an octahedron.
  float n_ = 0.142857142857; // 1.0/7.0
  vec3  ns = n_ * D.wyz - D.xzx;

  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);

  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);

  vec4 x = x_ * ns.x + ns.yyyy;
  vec4 y = y_ * ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);

  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);

  vec4 s0 = floor(b0) * 2.0 + 1.0;
  vec4 s1 = floor(b1) * 2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));

  vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;

  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);

  // Normalise gradients
  vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
  p0 *= norm.x;
  p1 *= norm.y;
  p2 *= norm.z;
  p3 *= norm.w;

  // Mix final noise value
  vec4 m = max(0.6 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m * m, vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3)));
}

// Curl of a noise field — divergence-free vector field for organic motion
vec3 curlNoise(vec3 p) {
    const float e = 0.1;
    vec3 dx = vec3(e, 0.0, 0.0);
    vec3 dy = vec3(0.0, e, 0.0);
    vec3 dz = vec3(0.0, 0.0, e);

    float x = snoise(p + dy) - snoise(p - dy) - snoise(p + dz) + snoise(p - dz);
    float y = snoise(p + dz) - snoise(p - dz) - snoise(p + dx) + snoise(p - dx);
    float z = snoise(p + dx) - snoise(p - dx) - snoise(p + dy) + snoise(p - dy);

    return normalize(vec3(x, y, z) / (2.0 * e));
}

void main() {
    // Stagger morph progress per particle so they don't move in sync
    float t = clamp((u_morphProgress - jitter * 0.4) / 0.6, 0.0, 1.0);
    // Smoothstep easing
    float eased = t * t * (3.0 - 2.0 * t);

    vec3 morphed = mix(position, targetPos, eased);

    // Curl noise turbulence — per-particle explosion-and-settle, ramped to avoid frame-snap
    float noiseStrength = 0.05 + (1.0 - eased) * smoothstep(0.0, 0.15, u_morphProgress) * 0.18;
    vec3 noiseOffset = curlNoise(morphed * 1.5 + u_time * 0.15) * noiseStrength;

    vec3 finalPos = morphed + noiseOffset;

    // Mouse repulsion — 3D sphere, push particles to edge
    vec3 toParticle = finalPos - u_mousePos;
    float dist = length(toParticle);
    if (dist < u_mouseRadius && dist > 0.001) {
        vec3 pushDir = toParticle / dist;
        float pushDist = u_mouseRadius - dist;
        finalPos += pushDir * pushDist * 1.1;
    }

    vec4 mvPosition = modelViewMatrix * vec4(finalPos, 1.0);
    gl_Position = projectionMatrix * mvPosition;

    gl_PointSize = u_pointSize * (2.0 / -mvPosition.z) * (1.0 + u_audioAmplitude * 0.3);

    // Brighten particles at the rim of the repulsion zone
    float mouseGlow = (dist > u_mouseRadius && dist < u_mouseRadius * 2.0) ? (1.0 - (dist - u_mouseRadius) / u_mouseRadius) * 0.25 : 0.0;
    v_intensity = 0.55 + u_audioAmplitude * 0.25 + jitter * 0.1 + mouseGlow;
}
