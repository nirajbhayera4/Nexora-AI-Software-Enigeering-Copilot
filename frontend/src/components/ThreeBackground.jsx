import { useEffect, useRef } from 'react';

const COLORS = [0x2563eb, 0x14b8a6, 0xf59e0b];

/** A small, decorative WebGL scene shared by the landing and repository screens. */
export default function ThreeBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let disposed = false;
    let cleanupScene = () => {};

    const initialize = async () => {
      const THREE = await import('three');
      if (disposed) return;

      let renderer;
      try {
        renderer = new THREE.WebGLRenderer({
          canvas,
          alpha: true,
          antialias: false,
          powerPreference: 'low-power',
        });
      } catch {
        return;
      }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
    camera.position.z = 13;

    const group = new THREE.Group();
    scene.add(group);

    const objects = COLORS.map((color, index) => {
      const geometry = new THREE.IcosahedronGeometry(index === 1 ? 1.25 : 0.85, 1);
      const material = new THREE.MeshBasicMaterial({
        color,
        wireframe: true,
        transparent: true,
        opacity: 0.12,
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(index === 0 ? -6 : index === 1 ? 6 : 0, index === 2 ? -4 : 3, -2);
      mesh.rotation.set(index * 0.7, index * 0.45, index * 0.2);
      mesh.userData.speed = 0.00015 + index * 0.00007;
      group.add(mesh);
      return mesh;
    });

    const resize = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.25));
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.position.x = width < 640 ? 0 : 0.3;
      camera.updateProjectionMatrix();
    };

    let frameId;
    let lastFrame = 0;
    const render = (time = 0) => {
      frameId = undefined;
      if (document.hidden) return;
      if (!reducedMotion && time - lastFrame < 32) {
        frameId = window.requestAnimationFrame(render);
        return;
      }
      lastFrame = time;
      if (!reducedMotion) {
        objects.forEach((mesh) => {
          mesh.rotation.x += mesh.userData.speed;
          mesh.rotation.y += mesh.userData.speed * 1.4;
        });
        group.position.y = Math.sin(time * 0.00025) * 0.12;
      }
      renderer.render(scene, camera);
      if (!reducedMotion) frameId = window.requestAnimationFrame(render);
    };

    const onVisibilityChange = () => {
      if (document.hidden) {
        if (frameId !== undefined) window.cancelAnimationFrame(frameId);
        frameId = undefined;
      } else if (!reducedMotion && frameId === undefined) {
        frameId = window.requestAnimationFrame(render);
      }
    };

      resize();
      render();
      window.addEventListener('resize', resize, { passive: true });
      document.addEventListener('visibilitychange', onVisibilityChange);

      cleanupScene = () => {
        if (frameId !== undefined) window.cancelAnimationFrame(frameId);
        window.removeEventListener('resize', resize);
        document.removeEventListener('visibilitychange', onVisibilityChange);
        objects.forEach((mesh) => {
          mesh.geometry.dispose();
          mesh.material.dispose();
        });
        renderer.dispose();
      };
    };

    void initialize();
    return () => {
      disposed = true;
      cleanupScene();
    };
  }, []);

  return <canvas ref={canvasRef} className="three-background" aria-hidden="true" />;
}
