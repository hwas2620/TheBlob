import { useEffect, useState } from 'react';
import { GameCanvas } from './components/GameCanvas';
import { StatsPanel } from './components/StatsPanel';
import { UpgradePanel } from './components/UpgradePanel';
import { ActionPanel } from './components/ActionPanel';
import { GeneticsPanel } from './components/GeneticsPanel';
import { Minimap } from './components/Minimap';
import { useGameStore } from './store/gameStore';
import { toggleCubicVisibility } from './hooks/useGameLoop';

function App() {
  const [offlineEarnings, setOfflineEarnings] = useState<number | null>(null);
  const [isClosing, setIsClosing] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [showCubic, setShowCubic] = useState(false);
  const { loadGame, blobState } = useGameStore();

  // 큐빅 표시 토글
  const handleCubicToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    const checked = e.target.checked;
    setShowCubic(checked);
    toggleCubicVisibility(checked);
  };

  // Load game on mount
  useEffect(() => {
    const earnings = loadGame();
    if (earnings > 0) {
      setOfflineEarnings(earnings);
      requestAnimationFrame(() => setIsVisible(true));

      // 3초 후 자동으로 사라짐
      setTimeout(() => {
        setIsClosing(true);
        setTimeout(() => {
          setOfflineEarnings(null);
          setIsClosing(false);
          setIsVisible(false);
        }, 300);
      }, 3000);
    }
  }, []);

  return (
    <div className="w-full h-full bg-black relative overflow-hidden">
      {/* Game Canvas - Full Screen Background */}
      <div className="absolute inset-0">
        <GameCanvas />
      </div>

      {/* UI Overlay */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Header */}
        <header className="pointer-events-auto p-4 flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-yellow-400 drop-shadow-lg flex items-center gap-2">
              <span className={blobState === 'dormant' ? 'grayscale' : ''}>🟡</span>
              The Blob
            </h1>
            <p className="text-xs text-yellow-600/80">황색망사점균 시뮬레이터</p>
          </div>
        </header>

        {/* Right Side - Stats */}
        <div className="absolute top-4 right-4 pointer-events-auto w-56">
          <StatsPanel />
        </div>

        {/* Left Side - Actions & Upgrades */}
        <div className="absolute top-20 left-4 pointer-events-auto w-64 space-y-3 max-h-[calc(100vh-6rem)] overflow-y-auto">
          <ActionPanel />
          <UpgradePanel />
          <GeneticsPanel />
        </div>

        {/* Footer Info */}
        <footer className="absolute bottom-4 left-1/2 -translate-x-1/2 text-center pointer-events-none">
          <p className="text-xs text-gray-600">
            💧 물을 주어 블롭을 깨우세요 • 🌾 영양분을 흡수하여 성장 • ✨ 포자화로 다음 스테이지 진행
          </p>
        </footer>

        {/* Bottom Right - Minimap & Toggle */}
        <div className="absolute bottom-4 right-4 pointer-events-auto space-y-2">
          <Minimap />
          <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showCubic}
              onChange={handleCubicToggle}
              className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-yellow-500 focus:ring-yellow-500"
            />
            큐빅 표시
          </label>
        </div>
      </div>

      {/* Offline Earnings Toast */}
      {offlineEarnings !== null && offlineEarnings > 0 && (
        <div
          className={`fixed top-6 left-1/2 -translate-x-1/2 z-50 transition-all duration-300 ease-out
            ${isVisible && !isClosing
              ? 'opacity-100 translate-y-0'
              : 'opacity-0 -translate-y-4'}`}
        >
          <div className="bg-gray-900/95 border border-yellow-500/50 rounded-xl px-6 py-4 flex items-center gap-4 shadow-lg backdrop-blur-sm">
            <span className="text-3xl">🌙</span>
            <div>
              <p className="text-yellow-400 text-sm font-medium">오프라인 수익</p>
              <p className="text-yellow-300 text-xl font-bold font-mono">+{offlineEarnings.toFixed(1)} ATP</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
