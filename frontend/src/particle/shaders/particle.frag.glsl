varying float v_intensity;
uniform vec3 u_color;

void main() {
    vec2 uv = gl_PointCoord - 0.5;
    float dist = length(uv);
    if (dist > 0.5) discard;

    // Smooth alpha falloff with strong center
    float alpha = pow(1.0 - dist * 2.0, 2.5);

    vec3 color = u_color * v_intensity;
    gl_FragColor = vec4(color, alpha);
}
