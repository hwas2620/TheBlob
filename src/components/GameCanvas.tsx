import React, { useRef, useEffect, useState, useCallback } from 'react';
import { useGameLoop, spawnWaterEffect, getCamera, setCamera, getZoom, setZoom } from '../hooks/useGameLoop';
import { useGameStore } from '../store/gameStore';
import { MAP_WIDTH, MAP_HEIGHT } from '../simulation/PhysarumSimulation';
import { UI, ZOOM, FRAGMENT } from '../config';

export const GameCanvas: React.FC = () => {
  const glCanvasRef = useRef<HTMLCanvasElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({
    width: UI.CANVAS_DEFAULT_WIDTH,
    height: UI.CANVAS_DEFAULT_HEIGHT
  });
  const isDraggingRef = useRef(false);
  const didDragRef = useRef(false); // 실제 드래그가 발생했는지 (클릭 vs 드래그 구분)
  const dragStartRef = useRef({ x: 0, y: 0 });
  const camStartRef = useRef({ x: 0, y: 0 });

  // 터치 상태
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);
  const touchCamStartRef = useRef<{ x: number; y: number } | null>(null);
  const isTwoFingerRef = useRef(false);
  const lastPinchDistRef = useRef<number>(0);
  const lastPinchZoomRef = useRef<number>(1);

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

  // Handle mouse down - start drag (좌클릭/중클릭)
  const handleMouseDown = useCallback((event: React.MouseEvent<HTMLCanvasElement>) => {
    if (event.button === 0 || event.button === 1) {
      event.preventDefault();
      isDraggingRef.current = true;
      didDragRef.current = false;
      dragStartRef.current = { x: event.clientX, y: event.clientY };
      camStartRef.current = getCamera();
      console.log('[DRAG] Mouse down, camera:', camStartRef.current);
    }
  }, []);

  // Handle mouse move - drag
  const handleMouseMove = useCallback((event: React.MouseEvent<HTMLCanvasElement>) => {
    if (isDraggingRef.current) {
      const dx = event.clientX - dragStartRef.current.x;
      const dy = event.clientY - dragStartRef.current.y;
      // 일정 거리 이상 이동해야 드래그로 인식 (클릭과 구분)
      if (!didDragRef.current && Math.abs(dx) + Math.abs(dy) > UI.DRAG_THRESHOLD) {
        didDragRef.current = true;
        console.log('[DRAG] Started dragging, dx:', dx, 'dy:', dy);
      }
      if (didDragRef.current) {
        // 드래그 방향 반대로 카메라 이동 (줌 보정)
        const zoom = getZoom();
        const newX = camStartRef.current.x - dx / zoom;
        const newY = camStartRef.current.y - dy / zoom;
        const wrappedX = ((newX % MAP_WIDTH) + MAP_WIDTH) % MAP_WIDTH;
        const wrappedY = ((newY % MAP_HEIGHT) + MAP_HEIGHT) % MAP_HEIGHT;
        console.log(`[DRAG] Camera: (${wrappedX.toFixed(0)}, ${wrappedY.toFixed(0)})`);
        // 토러스 래핑
        setCamera(wrappedX, wrappedY);
      }
    }
  }, []);

  // Handle mouse up - end drag or left-click water spray + 조각 수집
  const handleMouseUp = useCallback((event: React.MouseEvent) => {
    if (isDraggingRef.current && !didDragRef.current && event.button === 0) {
      // 좌클릭 (드래그 없이) → 물뿌리기 + 조각 수집
      const canvas = overlayCanvasRef.current;
      if (canvas) {
        const rect = canvas.getBoundingClientRect();
        const screenX = event.clientX - rect.left;
        const screenY = event.clientY - rect.top;
        const zoom = getZoom();

        // 물뿌리기 (화면 좌표)
        if (moisture < maxMoisture) {
          spawnWaterEffect(screenX / zoom, screenY / zoom);
          addWater();
        }

        // 조각 수집 (월드 좌표로 비교, 줌 보정)
        if (gamePhase === 'sporeCollection') {
          const cam = getCamera();
          const worldX = cam.x + screenX / zoom;
          const worldY = cam.y + screenY / zoom;
          for (const fragment of fragments) {
            if (fragment.merged) continue;
            const dx = worldX - fragment.position.x;
            const dy = worldY - fragment.position.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < fragment.size + FRAGMENT.COLLECTION_RANGE) {
              collectFragment(fragment.id);
              break;
            }
          }
        }
      }
    }
    isDraggingRef.current = false;
    didDragRef.current = false;
  }, [moisture, maxMoisture, addWater, gamePhase, fragments, collectFragment]);

  // Handle wheel - zoom (네이티브 이벤트로 등록해야 passive: false 가능)
  useEffect(() => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const oldZoom = getZoom();
      const factor = event.deltaY < 0 ? ZOOM.FACTOR : 1 / ZOOM.FACTOR;
      const newZoom = Math.max(ZOOM.MIN, Math.min(ZOOM.MAX, oldZoom * factor));
      setZoom(newZoom);

      // 마우스 위치 기준 줌 (마우스 아래 월드 좌표 유지)
      const rect = canvas.getBoundingClientRect();
      const mouseX = event.clientX - rect.left;
      const mouseY = event.clientY - rect.top;
      const cam = getCamera();
      const newCamX = cam.x + mouseX * (1 / oldZoom - 1 / newZoom);
      const newCamY = cam.y + mouseY * (1 / oldZoom - 1 / newZoom);
      setCamera(
        ((newCamX % MAP_WIDTH) + MAP_WIDTH) % MAP_WIDTH,
        ((newCamY % MAP_HEIGHT) + MAP_HEIGHT) % MAP_HEIGHT
      );
    };
    canvas.addEventListener('wheel', onWheel, { passive: false });
    return () => canvas.removeEventListener('wheel', onWheel);
  }, []);

  // Prevent context menu on right click
  const handleContextMenu = useCallback((event: React.MouseEvent) => {
    event.preventDefault();
  }, []);

  // Touch handlers
  const handleTouchStart = useCallback((event: React.TouchEvent<HTMLCanvasElement>) => {
    if (event.touches.length === 2) {
      // 2손가락: 중심점 저장
      event.preventDefault();
      isTwoFingerRef.current = true;

      // 두 손가락 중심점
      const centerX = (event.touches[0].clientX + event.touches[1].clientX) / 2;
      const centerY = (event.touches[0].clientY + event.touches[1].clientY) / 2;
      touchStartRef.current = { x: centerX, y: centerY };
      touchCamStartRef.current = getCamera();

      // 초기 거리와 줌 저장
      const dx = event.touches[0].clientX - event.touches[1].clientX;
      const dy = event.touches[0].clientY - event.touches[1].clientY;
      lastPinchDistRef.current = Math.sqrt(dx * dx + dy * dy);
      lastPinchZoomRef.current = getZoom();
    } else if (event.touches.length === 1) {
      // 1손가락: 물뿌리기 준비
      event.preventDefault();
      isTwoFingerRef.current = false;
      const touch = event.touches[0];
      touchStartRef.current = { x: touch.clientX, y: touch.clientY };
    }
  }, []);

  const handleTouchMove = useCallback((event: React.TouchEvent<HTMLCanvasElement>) => {
    if (event.touches.length === 2 && isTwoFingerRef.current && touchStartRef.current && touchCamStartRef.current) {
      event.preventDefault();

      // 현재 거리 계산
      const dx = event.touches[0].clientX - event.touches[1].clientX;
      const dy = event.touches[0].clientY - event.touches[1].clientY;
      const currentDist = Math.sqrt(dx * dx + dy * dy);

      // 두 손가락 중심점
      const centerX = (event.touches[0].clientX + event.touches[1].clientX) / 2;
      const centerY = (event.touches[0].clientY + event.touches[1].clientY) / 2;

      // 핀치 줌: 거리 변화율로 줌 적용
      if (lastPinchDistRef.current > 0) {
        const scale = currentDist / lastPinchDistRef.current;
        const newZoom = Math.max(ZOOM.MIN, Math.min(ZOOM.MAX, lastPinchZoomRef.current * scale));
        setZoom(newZoom);

        // 팬: 중심점 이동으로 카메라 이동
        const centerDx = centerX - touchStartRef.current.x;
        const centerDy = centerY - touchStartRef.current.y;

        const newX = touchCamStartRef.current.x - centerDx / newZoom;
        const newY = touchCamStartRef.current.y - centerDy / newZoom;

        setCamera(
          ((newX % MAP_WIDTH) + MAP_WIDTH) % MAP_WIDTH,
          ((newY % MAP_HEIGHT) + MAP_HEIGHT) % MAP_HEIGHT
        );
      }
    }
  }, []);

  const handleTouchEnd = useCallback((event: React.TouchEvent<HTMLCanvasElement>) => {
    if (!isTwoFingerRef.current && event.changedTouches.length === 1 && touchStartRef.current) {
      // 1손가락 탭: 물뿌리기
      const touch = event.changedTouches[0];
      const canvas = overlayCanvasRef.current;
      if (canvas) {
        const rect = canvas.getBoundingClientRect();
        const screenX = touch.clientX - rect.left;
        const screenY = touch.clientY - rect.top;
        const zoom = getZoom();

        // 물뿌리기
        if (moisture < maxMoisture) {
          spawnWaterEffect(screenX / zoom, screenY / zoom);
          addWater();
        }

        // 조각 수집
        if (gamePhase === 'sporeCollection') {
          const cam = getCamera();
          const worldX = cam.x + screenX / zoom;
          const worldY = cam.y + screenY / zoom;
          for (const fragment of fragments) {
            if (fragment.merged) continue;
            const dx = worldX - fragment.position.x;
            const dy = worldY - fragment.position.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < fragment.size + FRAGMENT.COLLECTION_RANGE) {
              collectFragment(fragment.id);
              break;
            }
          }
        }
      }
    }

    touchStartRef.current = null;
    touchCamStartRef.current = null;
    isTwoFingerRef.current = false;
    lastPinchDistRef.current = 0;
    lastPinchZoomRef.current = 1;
  }, [moisture, maxMoisture, addWater, gamePhase, fragments, collectFragment]);

  // Initialize game loop (듀얼 캔버스: WebGL2 + Canvas2D 오버레이)
  useGameLoop({
    glCanvasRef,
    overlayCanvasRef,
    width: dimensions.width,
    height: dimensions.height,
  });

  return (
    <div
      ref={containerRef}
      className="w-full h-full overflow-hidden relative"
      onMouseLeave={() => { isDraggingRef.current = false; didDragRef.current = false; }}
    >
      {/* WebGL2 캔버스 (하단 - 블롭/페로몬/정맥/큐빅) */}
      <canvas
        ref={glCanvasRef}
        width={dimensions.width}
        height={dimensions.height}
        className="block absolute inset-0"
      />
      {/* Canvas2D 오버레이 (상단 - 영양분/핵/포자/물 이펙트/텍스트) */}
      <canvas
        ref={overlayCanvasRef}
        width={dimensions.width}
        height={dimensions.height}
        onMouseDown={(e) => { console.log('[EVENT] MouseDown'); handleMouseDown(e); }}
        onMouseMove={(e) => { if (isDraggingRef.current) console.log('[EVENT] MouseMove'); handleMouseMove(e); }}
        onMouseUp={handleMouseUp}
        onContextMenu={handleContextMenu}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        className="block absolute inset-0"
        style={{
          cursor: isDraggingRef.current
            ? 'grabbing'
            : 'url("data:image/svg+xml,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'32\' height=\'32\' viewBox=\'0 0 100 100\'><text y=\'.9em\' font-size=\'80\'>🚿</text></svg>") 16 16, auto'
        }}
      />
    </div>
  );
};
