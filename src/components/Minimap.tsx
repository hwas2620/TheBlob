import React, { useRef, useEffect } from 'react';
import { getSimulation, getCamera, setCamera } from '../hooks/useGameLoop';
import { MAP_WIDTH, MAP_HEIGHT } from '../simulation/PhysarumSimulation';

const MINIMAP_WIDTH = 150;
const MINIMAP_HEIGHT = 150;

export const Minimap: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const renderLoop = () => {
      const sim = getSimulation();
      if (sim) {
        sim.renderMinimap(ctx, MINIMAP_WIDTH, MINIMAP_HEIGHT);
      }
      animFrameRef.current = requestAnimationFrame(renderLoop);
    };

    // 미니맵은 낮은 빈도로 업데이트 (성능 절약)
    const intervalId = setInterval(() => {
      const sim = getSimulation();
      if (sim && ctx) {
        sim.renderMinimap(ctx, MINIMAP_WIDTH, MINIMAP_HEIGHT);
      }
    }, 500); // 0.5초마다

    return () => {
      clearInterval(intervalId);
      cancelAnimationFrame(animFrameRef.current);
    };
  }, []);

  const handleClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mx = event.clientX - rect.left;
    const my = event.clientY - rect.top;

    // 미니맵 클릭 → 카메라 이동
    const worldX = (mx / MINIMAP_WIDTH) * MAP_WIDTH - window.innerWidth / 2;
    const worldY = (my / MINIMAP_HEIGHT) * MAP_HEIGHT - window.innerHeight / 2;

    setCamera(
      ((worldX % MAP_WIDTH) + MAP_WIDTH) % MAP_WIDTH,
      ((worldY % MAP_HEIGHT) + MAP_HEIGHT) % MAP_HEIGHT
    );
  };

  return (
    <div className="bg-black/80 backdrop-blur-sm border border-gray-700/50 rounded-lg overflow-hidden">
      <canvas
        ref={canvasRef}
        width={MINIMAP_WIDTH}
        height={MINIMAP_HEIGHT}
        onClick={handleClick}
        className="block cursor-pointer"
        style={{ width: MINIMAP_WIDTH, height: MINIMAP_HEIGHT }}
      />
    </div>
  );
};
