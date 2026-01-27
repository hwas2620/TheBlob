import React, { useRef, useEffect, useState, useCallback } from 'react';
import { useGameLoop, spawnWaterEffect, getCamera, setCamera } from '../hooks/useGameLoop';
import { useGameStore } from '../store/gameStore';
import { MAP_WIDTH, MAP_HEIGHT } from '../simulation/PhysarumSimulation';

export const GameCanvas: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const camStartRef = useRef({ x: 0, y: 0 });

  const { fragments, collectFragment, gamePhase, addWater, moisture, maxMoisture } = useGameStore();

  // Handle resize (뷰포트 크기만 변경, 맵은 고정)
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const { clientWidth, clientHeight } = containerRef.current;
        setDimensions({ width: clientWidth, height: clientHeight });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  // Handle mouse down - start drag (우클릭/중클릭)
  const handleMouseDown = useCallback((event: React.MouseEvent<HTMLCanvasElement>) => {
    if (event.button === 1 || event.button === 2) {
      event.preventDefault();
      isDraggingRef.current = true;
      dragStartRef.current = { x: event.clientX, y: event.clientY };
      camStartRef.current = getCamera();
    }
  }, []);

  // Handle mouse move - drag
  const handleMouseMove = useCallback((event: React.MouseEvent<HTMLCanvasElement>) => {
    if (isDraggingRef.current) {
      const dx = event.clientX - dragStartRef.current.x;
      const dy = event.clientY - dragStartRef.current.y;
      // 드래그 방향 반대로 카메라 이동 (직관적)
      const newX = camStartRef.current.x - dx;
      const newY = camStartRef.current.y - dy;
      // 토러스 래핑
      setCamera(
        ((newX % MAP_WIDTH) + MAP_WIDTH) % MAP_WIDTH,
        ((newY % MAP_HEIGHT) + MAP_HEIGHT) % MAP_HEIGHT
      );
    }
  }, []);

  // Handle mouse up - end drag
  const handleMouseUp = useCallback(() => {
    isDraggingRef.current = false;
  }, []);

  // Prevent context menu on right click
  const handleContextMenu = useCallback((event: React.MouseEvent) => {
    event.preventDefault();
  }, []);

  // Handle click on canvas (left click only)
  const handleClick = useCallback(
    (event: React.MouseEvent<HTMLCanvasElement>) => {
      if (event.button !== 0) return;

      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const screenX = event.clientX - rect.left;
      const screenY = event.clientY - rect.top;

      // 화면 좌표 → 월드 좌표
      const cam = getCamera();
      const worldX = cam.x + screenX;
      const worldY = cam.y + screenY;

      // 물방울 이펙트 (화면 좌표에 생성)
      if (moisture < maxMoisture) {
        spawnWaterEffect(screenX, screenY);
        addWater();
      }

      // 조각 수집 (월드 좌표로 비교)
      if (gamePhase === 'sporeCollection') {
        for (const fragment of fragments) {
          if (fragment.merged) continue;

          const dx = worldX - fragment.position.x;
          const dy = worldY - fragment.position.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < fragment.size + 15) {
            collectFragment(fragment.id);
            break;
          }
        }
      }
    },
    [gamePhase, fragments, collectFragment, addWater, moisture, maxMoisture]
  );

  // Initialize game loop
  useGameLoop({
    canvasRef,
    width: dimensions.width,
    height: dimensions.height,
  });

  return (
    <div
      ref={containerRef}
      className="w-full h-full overflow-hidden"
      onMouseLeave={handleMouseUp}
    >
      <canvas
        ref={canvasRef}
        width={dimensions.width}
        height={dimensions.height}
        onClick={handleClick}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onContextMenu={handleContextMenu}
        className="block"
        style={{
          cursor: isDraggingRef.current
            ? 'grabbing'
            : 'url("data:image/svg+xml,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'32\' height=\'32\' viewBox=\'0 0 100 100\'><text y=\'.9em\' font-size=\'80\'>🚿</text></svg>") 16 16, auto'
        }}
      />
    </div>
  );
};
