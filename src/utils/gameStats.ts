// 게임 통계 수집 유틸리티
// 게임 밸런싱 데이터를 localStorage에 누적 저장

const STATS_KEY = 'the_blob_stats_v1';

// 세션 통계
export interface SessionStats {
  stageNumber: number;
  clearTimeSeconds: number;     // 스테이지 클리어 소요 시간
  nutrientsConsumed: number;    // 소비한 영양분 수
  peakBiomass: number;          // 최대 바이오매스
  sporulationCount: number;     // 포자화 횟수
  timestamp: number;
}

// 누적 통계
export interface GameStats {
  totalSessions: number;
  totalPlayTimeSeconds: number;
  highestStage: number;
  sessions: SessionStats[];     // 최근 50세션만 보관
}

const MAX_SESSIONS = 50;

// 누적 통계 로드
export function loadGameStats(): GameStats {
  try {
    const data = localStorage.getItem(STATS_KEY);
    if (data) {
      return JSON.parse(data) as GameStats;
    }
  } catch {
    // 파싱 실패 시 초기화
  }
  return {
    totalSessions: 0,
    totalPlayTimeSeconds: 0,
    highestStage: 1,
    sessions: [],
  };
}

// 세션 통계 기록
export function recordSessionStats(session: SessionStats) {
  const stats = loadGameStats();
  stats.totalSessions++;
  stats.totalPlayTimeSeconds += session.clearTimeSeconds;
  stats.highestStage = Math.max(stats.highestStage, session.stageNumber);
  stats.sessions.push(session);

  // 최근 세션만 보관
  if (stats.sessions.length > MAX_SESSIONS) {
    stats.sessions = stats.sessions.slice(-MAX_SESSIONS);
  }

  try {
    localStorage.setItem(STATS_KEY, JSON.stringify(stats));
  } catch {
    // 저장 실패 무시 (localStorage 용량 초과 등)
  }
}

// 스테이지별 평균 클리어 시간 조회
export function getAverageClearTime(stageNumber: number): number | null {
  const stats = loadGameStats();
  const stageSessions = stats.sessions.filter(s => s.stageNumber === stageNumber);
  if (stageSessions.length === 0) return null;
  const total = stageSessions.reduce((sum, s) => sum + s.clearTimeSeconds, 0);
  return total / stageSessions.length;
}
