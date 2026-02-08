/**
 * TheBlob 성능 벤치마크
 * Puppeteer MCP를 활용한 자동화된 성능 측정
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// 벤치마크 설정
const BENCHMARK_CONFIGS = [
  {
    name: '기본 설정 (100k 에이전트)',
    agentCount: 100000,
    sensorDistance: 9,
    expectedFPS: 60
  },
  {
    name: '경량 설정 (50k 에이전트)',
    agentCount: 50000,
    sensorDistance: 9,
    expectedFPS: 60
  },
  {
    name: '고부하 설정 (150k 에이전트)',
    agentCount: 150000,
    sensorDistance: 15,
    expectedFPS: 50
  }
];

const DURATION_MS = 10000; // 10초간 측정
const URL = 'http://localhost:5173';

async function runBenchmark() {
  console.log('=== TheBlob 성능 벤치마크 시작 ===\n');

  const browser = await puppeteer.launch({
    headless: 'new',
    args: [
      '--disable-gpu-vsync',
      '--disable-frame-rate-limit',
      '--disable-blink-features=AutomationControlled'
    ]
  });

  const results = [];

  try {
    for (const config of BENCHMARK_CONFIGS) {
      console.log(`\n📊 ${config.name}`);
      console.log(`   에이전트: ${config.agentCount.toLocaleString()}, 센서거리: ${config.sensorDistance}`);

      const page = await browser.newPage();
      await page.setViewport({ width: 1920, height: 1080 });

      // 페이지 로드
      await page.goto(URL, { waitUntil: 'networkidle0' });

      // 설정 적용 및 성능 측정
      const metrics = await page.evaluate(async (cfg, duration) => {
        // config.ts 값 오버라이드 (전역 변수로 노출 필요)
        if (window.overrideConfig) {
          window.overrideConfig({
            AGENT_COUNT: cfg.agentCount,
            AGENT_SENSOR_DISTANCE: cfg.sensorDistance
          });
        }

        // 게임 초기화 대기
        await new Promise(r => setTimeout(r, 2000));

        // FPS 측정
        const fps = [];
        const frameTimes = [];
        let lastTime = performance.now();
        let frameCount = 0;

        const measureFrame = () => {
          const now = performance.now();
          const delta = now - lastTime;

          if (delta > 0) {
            fps.push(1000 / delta);
            frameTimes.push(delta);
          }

          lastTime = now;
          frameCount++;
        };

        // 프레임 측정 시작
        const startTime = performance.now();
        while (performance.now() - startTime < duration) {
          await new Promise(resolve => {
            requestAnimationFrame(() => {
              measureFrame();
              resolve();
            });
          });
        }

        // 통계 계산
        const avgFPS = fps.reduce((a, b) => a + b, 0) / fps.length;
        const minFPS = Math.min(...fps);
        const maxFPS = Math.max(...fps);
        const p95FPS = fps.sort((a, b) => b - a)[Math.floor(fps.length * 0.05)];
        const p99FPS = fps.sort((a, b) => b - a)[Math.floor(fps.length * 0.01)];

        // 메모리 사용량
        const memory = performance.memory ? {
          usedJSHeapSize: (performance.memory.usedJSHeapSize / 1024 / 1024).toFixed(2),
          totalJSHeapSize: (performance.memory.totalJSHeapSize / 1024 / 1024).toFixed(2)
        } : null;

        return {
          frameCount,
          avgFPS: avgFPS.toFixed(2),
          minFPS: minFPS.toFixed(2),
          maxFPS: maxFPS.toFixed(2),
          p95FPS: p95FPS.toFixed(2),
          p99FPS: p99FPS.toFixed(2),
          avgFrameTime: (frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length).toFixed(2),
          memory
        };
      }, config, DURATION_MS);

      // 결과 출력
      console.log(`   평균 FPS: ${metrics.avgFPS}`);
      console.log(`   최소 FPS: ${metrics.minFPS}`);
      console.log(`   P95 FPS:  ${metrics.p95FPS}`);
      console.log(`   평균 프레임 시간: ${metrics.avgFrameTime}ms`);
      if (metrics.memory) {
        console.log(`   메모리 사용: ${metrics.memory.usedJSHeapSize}MB / ${metrics.memory.totalJSHeapSize}MB`);
      }

      // 성능 회귀 검증
      const passed = parseFloat(metrics.avgFPS) >= config.expectedFPS;
      console.log(`   ${passed ? '✅ 통과' : '❌ 실패'} (기준: ${config.expectedFPS} FPS)`);

      results.push({
        config: config.name,
        ...config,
        metrics,
        passed
      });

      await page.close();

      // 다음 테스트 전 대기
      await new Promise(r => setTimeout(r, 1000));
    }

  } finally {
    await browser.close();
  }

  // 결과 저장
  const report = {
    timestamp: new Date().toISOString(),
    duration: DURATION_MS,
    results,
    summary: {
      total: results.length,
      passed: results.filter(r => r.passed).length,
      failed: results.filter(r => !r.passed).length
    }
  };

  const reportPath = path.join(__dirname, 'benchmark-results.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

  console.log(`\n=== 벤치마크 완료 ===`);
  console.log(`총 ${report.summary.total}개 테스트 중 ${report.summary.passed}개 통과`);
  console.log(`결과 저장: ${reportPath}\n`);

  // 실패 시 exit code 1
  if (report.summary.failed > 0) {
    process.exit(1);
  }
}

// 실행
runBenchmark().catch(err => {
  console.error('벤치마크 실패:', err);
  process.exit(1);
});
