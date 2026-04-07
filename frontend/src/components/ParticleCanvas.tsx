import { useEffect, useRef } from 'react';
import { createRenderer } from '../particle/renderer';
import { ParticleSystem } from '../particle/particleSystem';

const POINT_COUNT = 30000;
const MORPH_INTERVAL_MS = 3000;
const MORPH_DURATION_MS = 1500;

export function ParticleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    let active = true;
    const { scene, composer, dispose } = createRenderer(canvasRef.current);
    const particles = new ParticleSystem(POINT_COUNT);
    scene.add(particles.mesh);

    // Pre-generate target shapes
    const sphere = ParticleSystem.randomSphere(POINT_COUNT, 1.0);
    const cube = ParticleSystem.randomCube(POINT_COUNT, 1.6);
    const shapes = [cube, sphere];
    let shapeIndex = 0;

    let lastMorphTime = performance.now();
    let frameId = 0;
    const startTime = performance.now();

    const render = () => {
      if (!active) return;

      const now = performance.now();
      const elapsed = (now - startTime) / 1000;

      // Sine-wave audio amplitude stub
      const amplitude = Math.sin(elapsed * 2.0) * 0.5 + 0.5;

      // Trigger morph every MORPH_INTERVAL_MS
      if (now - lastMorphTime >= MORPH_INTERVAL_MS) {
        particles.morphTo(shapes[shapeIndex], MORPH_DURATION_MS);
        shapeIndex = (shapeIndex + 1) % shapes.length;
        lastMorphTime = now;
      }

      particles.update(elapsed, amplitude);
      composer.render();
      frameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      active = false;
      cancelAnimationFrame(frameId);
      scene.remove(particles.mesh);
      dispose();
    };
  }, []);

  return <canvas ref={canvasRef} className="w-full h-full block" />;
}
