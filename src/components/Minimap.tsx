import React, { useRef, useEffect, useState } from 'react';
import { getSimulation, setCamera, getZoom } from '../hooks/useGameLoop';
import { MAP_WIDTH, MAP_HEIGHT } from '../simulation/PhysarumSimulation';
import { UI } from '../config';

const MINIMAP_WIDTH = UI.MINIMAP_SIZE;
const MINIMAP_HEIGHT = UI.MINIMAP_SIZE;

export const Minimap: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);
  const [zoomLevel, setZoomLevel] = useState(1.0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 미니맵은 낮은 빈도로 업데이트 (성능 절약)
    const intervalId = setInterval(() => {
      const sim = getSimulation();
      if (sim && ctx) {
        sim.renderMinimap(ctx, MINIMAP_WIDTH, MINIMAP_HEIGHT);
      }
      // 줌 레벨 업데이트
      setZoomLevel(getZoom());
    }, UI.MINIMAP_UPDATE_INTERVAL);

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
    <div className="relative">
      {/* 줌 레벨 표시 (미니맵 위쪽) */}
      <div className="absolute -top-7 left-0 px-2 py-1 text-xs font-mono text-white/90 bg-black/70 backdrop-blur-sm rounded border border-gray-700/30">
        Zoom: {zoomLevel.toFixed(2)}x
      </div>
      {/* 미니맵 */}
      <div className="bg-black/40 backdrop-blur-sm border border-gray-700/30 rounded-lg overflow-hidden">
        <canvas
          ref={canvasRef}
          width={MINIMAP_WIDTH}
          height={MINIMAP_HEIGHT}
          onClick={handleClick}
          className="block cursor-pointer"
          style={{ width: MINIMAP_WIDTH, height: MINIMAP_HEIGHT }}
        />
      </div>
    </div>
  );
};
