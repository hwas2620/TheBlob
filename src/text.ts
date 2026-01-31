// ============================================================
// The Blob — 텍스트 상수
// 모든 UI 텍스트를 한 곳에서 관리 (향후 다국어 지원 가능)
// ============================================================

export const TEXT = {
  // 앱 타이틀 & 부제
  APP_SUBTITLE: '황색망사점균 시뮬레이터',

  // 게임 가이드
  GAME_GUIDE: '💧 물을 주어 블롭을 깨우세요 • 🌾 영양분을 흡수하여 성장 • ✨ 포자화로 다음 스테이지 진행',

  // 토글 & 버튼
  TOGGLE_CUBIC: '[1] 큐빅 표시',
  TOGGLE_PARTICLES: '[2] 에이전트 표시',
  BTN_SAVE: '💾 저장',
  BTN_RESET: '🔄 초기화',
  BTN_WATER: '물 주기',
  BTN_WATER_FULL: '습도 충분',
  BTN_SPORULATE: '✨ 포자화',
  BTN_SPORULATE_IN_PROGRESS: '✨ 포자화 진행 중...',

  // 상태 메시지
  STATUS_DORMANT: '💤 휴면 중',
  STATUS_ACTIVE: '🌱 성장 중',
  STATUS_SPORULATING: '✨ 포자화 중',
  STATUS_FRAGMENT: '🔗 조각 수집 중',

  // 경고 & 안내
  WARNING_DORMANT: '⚠️ 휴면 상태 - 물을 주세요!',
  WARNING_LOW_BIOMASS: '바이오매스가 부족합니다!',
  INFO_SPORULATION_READY: '✨ 포자화 가능!',
  INFO_SPORULATION_CONDITION: '질량 {0} 필요',
  INFO_SPORULATION_DESCRIPTION: '새로운 생명으로 환생합니다',
  INFO_FRAGMENTS: '🔗 조각을 모으세요!',
  INFO_FRAGMENTS_HELP: '흩어진 블롭 조각을 클릭하거나 가까이 가세요',
  INFO_NUTRIENTS_DEPLETED: '모든 영양분 소진! 포자화를 고려해보세요.',

  // 토스트
  TOAST_OFFLINE_REWARD: '오프라인 수익',
  TOAST_SAVE_SUCCESS: '게임이 저장되었습니다!',

  // 확인 대화상자
  CONFIRM_RESET: '정말로 게임을 초기화하시겠습니까? 모든 진행 상황이 삭제됩니다.',

  // 스탯 패널
  STAT_SPORULATIONS: '🧬 {0}회 환생',
  STAT_BIOMASS: '🧫 질량',
  STAT_NUTRIENTS: '🌾 영양분',
  STAT_GENETICS: '🧬 유전자',
  STAT_FRAGMENTS_COUNT: '조각 수: {0}',

  // 업그레이드
  PANEL_UPGRADE: '⬆️ 업그레이드',
  UPGRADE_MOISTURE: '습도 유지',
  UPGRADE_MOISTURE_DESC: '습도 감소 속도 감소',
  UPGRADE_EXPANSION: '확장 속도',
  UPGRADE_EXPANSION_DESC: '촉수 성장 속도 증가',
  UPGRADE_ENZYME: '분해 효소',
  UPGRADE_ENZYME_DESC: '영양분 흡수 속도 증가',
  UPGRADE_AUTO_WATER: '자동 급수',
  UPGRADE_AUTO_WATER_DESC: '자동으로 물 주기',
  UPGRADE_SPORE_QUALITY: '포자 품질',
  UPGRADE_SPORE_QUALITY_DESC: '환생 보너스 증가',
  UPGRADE_MAX: 'MAX',
  UPGRADE_CHANCE: '{0}% 확률',
  UPGRADE_MULTIPLIER: 'x{0}',

  // 유전자 패널
  PANEL_GENETICS: '유전자 ({0} GP)',
  GENETICS_BIOMASS: '질량 부스트',
  GENETICS_BIOMASS_DESC: '시작 질량 +5',
  GENETICS_MOISTURE: '습도 부스트',
  GENETICS_MOISTURE_DESC: '시작 습도 +10',
  GENETICS_ATP: 'ATP 부스트',
  GENETICS_ATP_DESC: 'ATP 획득량 +10%',
  GENETICS_SPORULATIONS: '포자화 횟수: {0}',

  // 습도 바
  LABEL_MOISTURE: '💧 습도',

  // 자원 단위
  UNIT_ATP: 'ATP',

  // 화면 중앙 메시지
  SCREEN_DORMANT: '휴면 중 - 물을 주세요!',
  SCREEN_SPORULATING: '포자화 중...',

  // 콘솔 로그
  LOG_WAKE_UP: '블롭이 깨어났습니다!',
  LOG_GPU_SCENE_ACTIVE: 'GPU 씬 렌더러 활성화',
  LOG_GPU_SCENE_FAILED: 'GPU 씬 렌더러 초기화 실패:',
  LOG_WEBGL2_FALLBACK: 'WebGL2 사용 불가, CPU 폴백',
  LOG_INIT_COMPLETE: 'Jeff Jones 시뮬레이션 초기화 완료 (맵: {0}x{1}, GPU: {2})',
  LOG_GPU_STATUS_ON: '활성',
  LOG_GPU_STATUS_OFF: '비활성',
  LOG_SAVE_FAILED: 'Failed to load save:',
} as const;

// 텍스트 포맷 헬퍼 함수
export function formatText(template: string, ...args: (string | number)[]): string {
  return template.replace(/{(\d+)}/g, (match, index) => {
    const i = parseInt(index);
    return args[i] !== undefined ? String(args[i]) : match;
  });
}
