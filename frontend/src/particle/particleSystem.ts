import * as THREE from 'three';
import vertexShader from './shaders/particle.vert.glsl?raw';
import fragmentShader from './shaders/particle.frag.glsl?raw';

export class ParticleSystem {
  readonly mesh: THREE.Points;
  private geometry: THREE.BufferGeometry;
  private material: THREE.ShaderMaterial;
  private currentPositions: Float32Array;
  private targetPositions: Float32Array;
  private morphStartTime = 0;
  private morphDuration = 1500;
  private isMorphing = false;

  readonly pointCount: number;

  constructor(pointCount: number = 30000) {
    this.pointCount = pointCount;
    this.geometry = new THREE.BufferGeometry();
    this.currentPositions = ParticleSystem.randomSphere(pointCount, 1.0);
    this.targetPositions = new Float32Array(this.currentPositions);

    const jitter = new Float32Array(pointCount);
    for (let i = 0; i < pointCount; i++) jitter[i] = Math.random();

    this.geometry.setAttribute(
      'position',
      new THREE.BufferAttribute(this.currentPositions, 3)
    );
    this.geometry.setAttribute(
      'targetPos',
      new THREE.BufferAttribute(this.targetPositions, 3)
    );
    this.geometry.setAttribute(
      'jitter',
      new THREE.BufferAttribute(jitter, 1)
    );

    this.material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms: {
        u_time: { value: 0 },
        u_morphProgress: { value: 1.0 },
        u_audioAmplitude: { value: 0.0 },
        u_pointSize: { value: 4.5 },
        u_color: { value: new THREE.Color(0x88bbff) },
      },
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });

    this.mesh = new THREE.Points(this.geometry, this.material);
    this.mesh.frustumCulled = false;
  }

  /**
   * Load a new target point cloud.
   * Triggers a morph from current → target.
   */
  morphTo(newTargetPositions: Float32Array, durationMs: number = 1500): void {
    // Snapshot current interpolated positions as the new start
    this.currentPositions.set(this.targetPositions);

    // Match length: if new array is different length, resample randomly
    if (newTargetPositions.length !== this.targetPositions.length) {
      this.targetPositions = this._resampleToLength(newTargetPositions, this.pointCount);
    } else {
      this.targetPositions.set(newTargetPositions);
    }

    const currentAttr = this.geometry.attributes.position as THREE.BufferAttribute;
    const targetAttr = this.geometry.attributes.targetPos as THREE.BufferAttribute;
    currentAttr.needsUpdate = true;
    targetAttr.array = this.targetPositions;
    targetAttr.needsUpdate = true;

    this.morphStartTime = performance.now();
    this.morphDuration = durationMs;
    this.isMorphing = true;
  }

  update(elapsedSeconds: number, audioAmplitude: number): void {
    this.material.uniforms.u_time.value = elapsedSeconds;
    this.material.uniforms.u_audioAmplitude.value = audioAmplitude;

    if (this.isMorphing) {
      const t = (performance.now() - this.morphStartTime) / this.morphDuration;
      this.material.uniforms.u_morphProgress.value = Math.min(1.0, t);
      if (t >= 1.0) this.isMorphing = false;
    }
  }

  static randomSphere(n: number, radius: number): Float32Array {
    const out = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = 2 * Math.PI * u;
      const phi = Math.acos(2 * v - 1);
      const r = radius * Math.cbrt(Math.random());
      out[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      out[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      out[i * 3 + 2] = r * Math.cos(phi);
    }
    return out;
  }

  static randomCube(n: number, size: number): Float32Array {
    const out = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      out[i * 3] = (Math.random() - 0.5) * size;
      out[i * 3 + 1] = (Math.random() - 0.5) * size;
      out[i * 3 + 2] = (Math.random() - 0.5) * size;
    }
    return out;
  }

  private _resampleToLength(input: Float32Array, targetLength: number): Float32Array {
    const inputCount = input.length / 3;
    const out = new Float32Array(targetLength * 3);
    for (let i = 0; i < targetLength; i++) {
      const srcIdx = Math.floor(Math.random() * inputCount);
      out[i * 3] = input[srcIdx * 3];
      out[i * 3 + 1] = input[srcIdx * 3 + 1];
      out[i * 3 + 2] = input[srcIdx * 3 + 2];
    }
    return out;
  }
}
