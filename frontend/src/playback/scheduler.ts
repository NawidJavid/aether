import type { Manifest, ScheduledShape } from '../types';
import { ParticleSystem } from '../particle/particleSystem';

export class PlaybackScheduler {
  private firedIndices = new Set<number>();
  private shapes: ScheduledShape[];
  private pointClouds = new Map<string, Float32Array>();
  private particleSystem: ParticleSystem;

  constructor(particleSystem: ParticleSystem, manifest: Manifest) {
    this.particleSystem = particleSystem;
    this.shapes = manifest.shapes;
  }

  /** Pre-fetches all .bin files into memory before playback starts. */
  async preload(apiBaseUrl: string): Promise<void> {
    await Promise.all(
      this.shapes.map(async (s) => {
        const url = `${apiBaseUrl}${s.point_cloud_url}`;
        const resp = await fetch(url);
        const buf = await resp.arrayBuffer();
        this.pointClouds.set(s.point_cloud_url, new Float32Array(buf));
      }),
    );
  }

  /** Called every frame from the render loop. */
  tick(audioCurrentTimeMs: number): void {
    for (let i = 0; i < this.shapes.length; i++) {
      if (this.firedIndices.has(i)) continue;
      const shape = this.shapes[i];
      if (audioCurrentTimeMs >= shape.trigger_time_ms) {
        const cloud = this.pointClouds.get(shape.point_cloud_url);
        if (cloud) {
          this.particleSystem.morphTo(cloud, shape.morph_duration_ms);
        }
        this.firedIndices.add(i);
      }
    }
  }

  reset(): void {
    this.firedIndices.clear();
  }
}
