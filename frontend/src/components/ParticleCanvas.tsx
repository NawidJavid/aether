import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { createRenderer } from '../particle/renderer';
import { ParticleSystem } from '../particle/particleSystem';
import { AudioAnalyzer } from '../particle/audioAnalyzer';
import { PlaybackScheduler } from '../playback/scheduler';
import { useStore } from '../store';

export function ParticleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const manifest = useStore((s) => s.manifest);
  const audioElement = useStore((s) => s.audioElement);

  // Persist AudioContext + source across StrictMode double-mounts.
  // createMediaElementSource can only be called once per <audio> element.
  const audioRef = useRef<{
    ctx: AudioContext;
    source: MediaElementAudioSourceNode;
    element: HTMLAudioElement;
  } | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    const { scene, camera, composer, dispose } = createRenderer(canvasRef.current);
    const particles = new ParticleSystem(30000);
    scene.add(particles.mesh);

    let analyzer: AudioAnalyzer | null = null;
    let scheduler: PlaybackScheduler | null = null;

    if (audioElement && manifest) {
      if (!audioRef.current || audioRef.current.element !== audioElement) {
        audioRef.current?.ctx.close();
        const ctx = new AudioContext();
        const source = ctx.createMediaElementSource(audioElement);
        source.connect(ctx.destination);
        audioRef.current = { ctx, source, element: audioElement };
      }

      analyzer = new AudioAnalyzer(audioRef.current.ctx, audioRef.current.source);

      scheduler = new PlaybackScheduler(particles, manifest);
      scheduler.preload('').then(() => {
        useStore.setState({ ready: true, scheduler });
      });
    }

    // Mouse interaction: raycast to z=0 plane in world space
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2(999, 999);
    const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
    const intersection = new THREE.Vector3();

    const onMouseMove = (e: MouseEvent) => {
      const rect = canvasRef.current!.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);
      if (raycaster.ray.intersectPlane(plane, intersection)) {
        particles.setMousePos(intersection.x, intersection.y, intersection.z);
      }
    };

    const onMouseLeave = () => {
      particles.clearMouse();
    };

    canvasRef.current.addEventListener('mousemove', onMouseMove);
    canvasRef.current.addEventListener('mouseleave', onMouseLeave);

    let frameId = 0;
    const startTime = performance.now();
    const render = () => {
      const elapsed = (performance.now() - startTime) / 1000;
      const amplitude = analyzer?.getAmplitude() ?? 0;
      particles.update(elapsed, amplitude);

      if (scheduler && audioElement) {
        scheduler.tick(audioElement.currentTime * 1000);
      }

      composer.render();
      frameId = requestAnimationFrame(render);
    };
    render();

    return () => {
      cancelAnimationFrame(frameId);
      canvasRef.current?.removeEventListener('mousemove', onMouseMove);
      canvasRef.current?.removeEventListener('mouseleave', onMouseLeave);
      scene.remove(particles.mesh);
      dispose();
    };
  }, [manifest, audioElement]);

  return <canvas ref={canvasRef} className="w-full h-full block" />;
}
