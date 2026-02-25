# 정맥 렌더링 개선 -- 전문가 토론

## 참가자
- Dr. 김점균 -- 균류학 전문가 (의뢰인)
- 박코드 -- WebGL2/셰이더 개발자
- 이헤시안 -- 이미지 처리 수학자
- 최로드맵 -- 프로젝트 기획자

---

## 파트 1: 의뢰 -- "이건 점균류가 아닙니다"

**Dr. 김점균**: (스크린을 한참 바라보다가 고개를 가로젓는다)

여러분, 이건 제 점균류가 아닙니다. 20년 동안 *Physarum polycephalum*을 매일 관찰해 온 사람으로서, 지금 화면에 보이는 건... 솔직히 말씀드리면, 노란 구름이에요. 안개. 수프요.

진짜 점균류의 정맥이 어떤지 아세요? (접사 사진을 꺼내며) 여기 보세요. 정맥은 **선**입니다. 촉수요. 본체 안에 박혀있는 수송관인데, 여기서 보면 밝은 노란색 실이 올리브색 본체 위에 선명하게 떠 보이죠. 경계가 칼로 자른 것 같아요. 맨눈으로 봐도 "아, 저기 정맥이다" 싶을 정도로 뚜렷합니다.

그런데 시뮬레이션을 보면... 정맥이라기보다 본체 전체가 약간 밝아졌다 어두워졌다 하는 것처럼 보입니다. 구조가 안 보여요. 분기도 안 보이고, 위계도 안 보이고. 그냥 흐릿한 노란 안개가 맥동할 뿐이에요.

**박코드**: 네, 김 박사님 지적이 정확합니다. 솔직하게 현재 상황을 설명드리겠습니다.

지금 정맥 셰이더(`veins.frag.glsl`)는 트레일맵에서 "능선(ridge)"을 검출해서 그리는 방식인데요. 문제는 정맥 셰이더에 입력되는 트레일맵이 이미 "죽" 상태라는 겁니다.

에이전트가 매 프레임 deposit을 뿌리면, `diffuse_decay.frag.glsl`에서 3x3 박스 블러를 **4번** 반복합니다. 이게 Jeff Jones 논문의 확산 모델이라 시뮬레이션 동역학에 필수인데, 문제는 이 과정에서 원래 2~5px 폭이었던 수송 채널이 8~13px 폭으로 퍼져버린다는 거예요.

거기에 정맥 셰이더가 또 한번 STEP=8 간격으로 3x3 블러를 추가로 돌려요. 그리고 STEP*2=16px 거리의 이웃과 비교해서 능선을 찾는데... 이미 퍼진 트레일맵에서 16px 떨어진 곳과의 차이가 얼마나 되겠습니까. 거의 없죠. 그래서 넓은 영역이 비슷한 ridge 값을 가지게 되고, 결과적으로 "구름"이 됩니다.

**Dr. 김점균**: 잠깐, 확산이 뭔지 정확히 짚고 넘어갑시다. 생물학적으로 확산은 **화학 신호의 전파**예요. 에이전트가 뿌린 페로몬이 주변으로 퍼지는 거죠. 이건 다른 에이전트가 "아, 저쪽에 동료가 있구나" 감지하는 데 쓰이는 겁니다.

그런데 정맥은 페로몬이 아니에요. 정맥은 **원형질 자체의 물리적 농축**입니다. 에이전트가 실제로 모여있는 곳, 원형질이 흐르는 통로 자체예요. 이걸 확산된 페로몬 맵에서 찾으려고 하니까, 비유하자면 향수 냄새가 퍼진 방에서 향수병 위치를 찾으려는 것과 같은 겁니다. 냄새는 퍼져 있지만, 병은 한 곳에 있잖아요.

**박코드**: 아... 그 비유가 핵심을 찌르는군요. 현재 시스템에서 에이전트 센서는 확산된 트레일맵을 읽어서 방향을 결정하는데, 이건 "향수 냄새를 맡고 이동하는" 올바른 동작이에요. 하지만 정맥 **렌더링**은 "향수병이 실제로 어디 있는지"를 보여줘야 하는 건데, 우리는 "퍼진 냄새의 농도"를 보여주고 있는 거군요.

**Dr. 김점균**: 정확합니다. 그래서 시뮬레이션이 아무리 잘 돌아가도, 렌더링이 확산된 맵을 보는 한 제 점균류처럼은 절대 보이지 않을 거예요.

한 가지 더요. 실제 점균류에서 정맥은 본체 위에 **3차원적으로 솟아** 있어요. 접사 사진을 보면 정맥 부분이 약간 융기해 있고, 주변보다 농축된 원형질이라 더 밝고 더 두꺼워요. 그래서 dark-field 촬영에서 정맥이 본체 대비 2~4배 밝게 나오는 거예요. 지금 시뮬레이션은 정맥이 본체에 "묻혀" 보이는데, 실제로는 반대로 **떠 보여야** 합니다.

**최로드맵**: 잠깐 정리하겠습니다. 김 박사님의 핵심 요구사항을 제가 제대로 이해했는지 확인할게요.

1. 정맥은 **가느다란 선**이어야 한다 (2~5px 폭, 면이 아님)
2. 경계가 **칼같이 선명**해야 한다 (blur/glow 없음, 1px 내 전환)
3. 본체 대비 **확실히 밝아야** 한다 (2~4배, "떠 보이는" 느낌)
4. **위계적 분기** 구조가 보여야 한다 (주정맥 -> 모세정맥)
5. 본체 가장자리에서 **돌출**해 "촉수" 느낌

맞습니까?

**Dr. 김점균**: 네, 정확합니다. 특히 1번과 2번이 가장 중요해요. 선이 아닌 것은 정맥이 아닙니다. 그리고 경계가 흐릿하면 잎맥이 아니라 수채화가 되어버리죠.

---

## 파트 2: 원인 분석 -- 왜 선이 구름이 되는가

**이헤시안**: 제가 수학적으로 왜 이런 일이 벌어지는지 설명해 드리겠습니다. 비전문가도 이해할 수 있게 해볼게요.

먼저 **확산이 선을 어떻게 파괴하는지** 직관적으로 설명하면요. 종이에 가는 펜으로 선을 긋고, 그 위에 물을 한 방울 떨어뜨렸다고 생각해 보세요. 잉크가 양옆으로 번지면서 선이 넓어지죠? 3x3 박스 블러 한 번이 물 한 방울이에요. 4번 반복하면 물을 네 번 뿌리는 겁니다.

수치로 말씀드리면, 3x3 박스 블러 한 번의 유효 가우시안 표준편차는 sigma 약 0.8px입니다. N번 반복하면 `sigma_total = 0.8 * sqrt(N)`이 되는데요:

```
1패스: sigma = 0.8px
2패스: sigma = 1.1px
4패스: sigma = 1.6px
```

가우시안 블러 후 선형 구조의 유효 폭 증가는 `원래 폭 + 2 * sigma * 2.35` (FWHM)입니다:

```
원래 2px 정맥 -> 4패스 후: 2 + 2*1.6*2.35 = 약 9.5px
원래 5px 주정맥 -> 4패스 후: 5 + 7.5 = 약 12.5px
```

즉, 에이전트가 만든 2~5px 수송 채널이 확산 후에는 **10~13px 폭의 뭉개진 언덕**이 됩니다. 이미 여기서 "선"은 사라진 거예요.

**박코드**: 그리고 정맥 셰이더가 이 상황을 더 악화시킵니다. 현재 코드를 보시면:

```glsl
// veins.frag.glsl, 21~30행
vec2 texel = (8.0 * zoomFactor) / u_mapSize;  // STEP=8

// 3x3 블러: 8px 간격으로 9개 샘플 평균
for (int dy = -1; dy <= 1; dy++) {
    for (int dx = -1; dx <= 1; dx++) {
        value += texture(u_trailMap, fract(trailUV + vec2(dx,dy) * texel)).r;
    }
}
value /= 9.0;
```

STEP=8이면 -8px, 0, +8px 위치에서 샘플링하는 거라 실질적으로 **16px 폭의 블러**예요. 이미 10~13px로 퍼진 데이터를 16px 범위로 한번 더 평균내는 겁니다.

그 다음 능선 검출:

```glsl
// 41~48행
vec2 farTexel = texel * 2.0;  // STEP*2 = 16px 거리
float avg = (right + left + up + down) * 0.25;
float ridge = value - avg;
```

**16px 떨어진** 4방향 이웃과 비교해서 "너 주변보다 높으면 능선이야"라고 판단하는데, 10~13px로 퍼진 언덕의 16px 이웃은 아직 같은 언덕 위예요. 차이가 거의 없습니다.

**이헤시안**: 수치로 검증해 보죠. 정상상태에서 에이전트 deposit이 `5`이고 decay가 `0.97`이면, 수송 채널 중심의 트레일 값은 약 `5 / (1 - 0.97) = 167`입니다.

확산 4패스 후 이 값이 반경 ~5px에 걸쳐 부드럽게 분포하면, 중심값이 약 150, 8px 떨어진 곳이 약 130, 16px 떨어진 곳이 약 110 정도라고 추정할 수 있어요.

현재 능선 검출의 결과:
```
ridge = center(150) - avg(110) = 40
relRidge = 40 / 150 = 0.267
ridgeStrength = smoothstep(0.2, 0.5, 0.267 * 3.0)
              = smoothstep(0.2, 0.5, 0.8) = 1.0
```

이건 주정맥 중심이니까 ridgeStrength가 1.0으로 나오지만, 문제는 **중심에서 5px 떨어진 곳도** 비슷한 값이 나온다는 겁니다:
```
5px 옆: value=140, 16px 이웃 avg=108
ridge = 32, relRidge = 32/140 = 0.229
ridgeStrength = smoothstep(0.2, 0.5, 0.229 * 3.0)
              = smoothstep(0.2, 0.5, 0.686) = 1.0
```

중심에서 10px 떨어진 곳도:
```
10px 옆: value=120, 16px 이웃 avg=100
ridge = 20, relRidge = 20/120 = 0.167
ridgeStrength = smoothstep(0.2, 0.5, 0.167 * 3.0)
              = smoothstep(0.2, 0.5, 0.5) = 0.5
```

보세요. 중심에서 10px까지 모두 유의미한 ridgeStrength를 가집니다. 원래 2~5px 폭이어야 할 정맥이 **20px 이상의 넓은 영역**으로 렌더링되는 거예요. 이게 "구름"의 정체입니다.

**박코드**: 게다가 하나 더 있어요. 현재 능선 검출은 **등방성(isotropic)**입니다. 상하좌우 4방향 이웃의 평균과 비교하니까, "이 픽셀이 주변보다 높은가?"만 봐요. "이 높은 영역이 선 형태인가, 둥근 형태인가?"는 전혀 구분 못 합니다.

직관적으로 설명하면, 산맥의 능선을 찾는 게 아니라 "여기가 평지보다 높은가?"만 보는 거예요. 그러면 산 전체가 "능선"으로 잡히죠. 진짜 원하는 건 "산등성이의 좁은 마루"인데.

**이헤시안**: 바로 그 점에서 **Hessian 행렬**이 필요한 겁니다. 직관적으로 말하면요, Hessian은 어떤 점에서의 "곡률"을 두 방향으로 분리해서 측정합니다.

산등성이(ridge)에 서 있다고 상상해 보세요:
- 등성이를 **따라가는** 방향: 완만 (곡률 작음)
- 등성이를 **가로지르는** 방향: 급경사 (곡률 큼, 음수)

Hessian의 두 고유값 lambda1, lambda2가 바로 이 두 방향의 곡률이에요:
- 능선(ridge): `|lambda1| >> |lambda2|` -- 한 방향으로만 급격히 꺾임
- 둥근 언덕(blob): `|lambda1| ~ |lambda2|` -- 모든 방향으로 비슷하게 꺾임
- 평지: `|lambda1| ~ |lambda2| ~ 0`

수식으로는:
```
dxx = (left + right - 2*center) / h^2
dyy = (up + down - 2*center) / h^2
dxy = (topRight + bottomLeft - topLeft - bottomRight) / (4*h^2)

lambda1 = 0.5*(dxx+dyy) + sqrt(0.25*(dxx-dyy)^2 + dxy^2)
lambda2 = 0.5*(dxx+dyy) - sqrt(0.25*(dxx-dyy)^2 + dxy^2)

ridgeness = -min(lambda1, lambda2)
```

`ridgeness`가 높으면 "여기는 선형 구조의 꼭대기다"라는 뜻이에요. 둥근 언덕은 자동으로 걸러집니다.

**Dr. 김점균**: 아, 그러니까 현재 방식은 "높은 곳"을 찾는 거고, Hessian은 "좁은 언덕 꼭대기"를 찾는 거군요. 정맥은 농축 원형질이 좁은 채널에 모여 있는 거니까, 후자가 맞겠네요.

**이헤시안**: 정확합니다. 그런데 여기서 중요한 점이 있어요. Hessian이 아무리 좋아도, **입력 데이터에 선이 존재해야** 선을 찾을 수 있습니다.

확산 4패스 후의 트레일맵에서는 원래 2~5px 정맥이 10~13px 폭의 부드러운 언덕으로 변했어요. Hessian을 적용하면 이 언덕의 "중심선"은 찾을 수 있지만, 그 중심선은 여전히 넓은 프로파일을 가져요. 1px 이내의 날카로운 경계는 **절대 복원 불가능**합니다.

비유하자면, 안경 없이 찍은 흐릿한 사진에서 sharpen 필터를 아무리 돌려도, 원본의 선명함에 도달하지 못하는 것과 같아요.

**박코드**: 결국 근본적인 해결을 위해서는 **확산 전의 원본 데이터**가 필요하다는 말씀이시죠?

**이헤시안**: 네. 김 박사님이 아까 정확히 짚으셨어요. 확산은 "페로몬 냄새의 전파"이고, 정맥은 "원형질 자체의 물리적 위치"입니다. 에이전트가 deposit을 뿌리고, 아직 확산이 일어나기 전의 상태 -- 이게 바로 "에이전트가 실제로 어디를 지나갔는가"의 직접적인 기록이에요.

이 미확산 데이터에서는:
- 수송 채널이 **원래 폭(2~5px)**을 유지
- 경계가 **날카로움** (에이전트가 있는 곳과 없는 곳의 차이가 뚜렷)
- Hessian STEP=1~2로 충분히 검출 가능

**Dr. 김점균**: 그러니까 해결책은 두 가지 맵을 따로 두는 거네요? 에이전트 센서용 확산 맵은 기존대로 유지하고, 정맥 렌더링용 미확산 맵을 별도로?

**박코드**: 네, 시뮬레이션에는 전혀 영향 없이 렌더링만 개선하는 방향이에요. 기술적으로 보면, `TrailMapGPU`에서 확산 전 상태를 별도 FBO에 복사해두면 됩니다.

---

## 파트 3: 해결책 논의 -- 어떻게 구현할 것인가

**최로드맵**: 자, 문제가 명확해졌으니 해결책을 구체적으로 논의해 봅시다. 수학자님이 정리해 주신 것처럼 핵심은 두 가지죠:

1. **미확산 트레일맵 분리** -- 정맥 검출의 입력 품질 확보
2. **Hessian ridge detection** -- 선형 구조만 정밀 추출

이 외에 블렌딩 변경(additive)도 있고요. 각각의 구현 방안을 논의해 봅시다.

**박코드**: 먼저 미확산 트레일맵부터요. 현재 `TrailMapGPU`의 파이프라인은:

```
매 프레임:
1. blendDeposits()  -- trail += deposit (에이전트가 뿌린 값 합산)
2. runDiffuseDecay() -- 3x3 블러 x 4패스 + 감쇠
```

미확산 맵을 만들려면, `blendDeposits()` 직후의 상태를 별도 텍스처에 보관하면 됩니다. 다만 여기서 고려할 점이 있어요.

**이헤시안**: 잠깐, `blendDeposits()` 이후면 이미 누적된 트레일에 새 deposit이 더해진 상태잖아요? 그러면 이전 프레임의 확산 결과 위에 새 deposit이 쌓인 건데... 이게 "미확산"이 맞나요?

**박코드**: 좋은 지적입니다. 엄밀히 말하면 "확산 전" 상태는 "이번 프레임의 deposit이 더해졌지만 이번 프레임의 확산은 아직 안 된" 상태예요. 이전 프레임의 확산 효과는 이미 반영되어 있죠.

하지만 실용적으로는 이것만으로도 충분합니다. 왜냐하면:
- 이번 프레임의 deposit은 에이전트가 실제로 있는 위치에 정확히 뿌려지므로, 수송 채널의 경계가 날카로움
- 이전 프레임의 확산 효과는 있지만, **이번 프레임에 한번 더 확산하기 전**이라 블러가 4패스 분 덜 됨
- 매 프레임 decay(0.97)가 적용되므로, 오래된 확산 효과는 빠르게 감쇠

더 깨끗한 방법은 **deposit만 별도로 누적**하는 건데요, 이러면 구조가 복잡해집니다. `blendDeposits()` 후 상태를 복사하는 게 가장 실용적이에요.

**이헤시안**: 동의합니다. 그리고 **감쇠(decay)**가 핵심 차이를 만들어요. 확산 맵에서는 값이 주변으로 퍼지면서 피크가 낮아지는데, 미확산 맵에서는 deposit + decay만 적용되니까 에이전트가 밀집한 곳의 피크가 **상대적으로 훨씬 뾰족**합니다. 이 뾰족한 프로파일이 Hessian으로 검출하기 훨씬 쉬워요.

구체적으로, 미확산 맵에서 정맥 프로파일의 단면을 보면:
- 중심 (에이전트 밀집): 높은 값 (예: 167)
- 경계에서 1~2px 벗어나면: 급격히 낮아짐 (예: 30~50)
- 이 급격한 전환이 Hessian에서 큰 음의 고유값을 만듦

**Dr. 김점균**: 사실 그게 실물의 물리적 구조와도 일치해요. 원형질 수송 채널은 경계가 뚜렷한 **튜브 구조**예요. 겔(gel) 상태의 외벽이 있고, 그 안에 솔(sol) 상태의 원형질이 흐르는데, 겔-솔 전환이 아주 좁은 영역에서 일어나거든요. 그래서 경계가 날카로운 거예요.

**박코드**: 좋습니다. 그러면 구현 측면에서 미확산 맵을 위해 필요한 것들을 정리하면:

1. **추가 R32F 텍스처 1장** (1500x1500, 약 9MB)
2. **추가 FBO 1개**
3. `blendDeposits()` 후 `glCopyTexSubImage2D` 또는 FBO간 blit으로 현재 상태를 복사
4. `SceneRenderer`에서 정맥 셰이더에 미확산 텍스처를 `uniform sampler2D`로 전달

메모리 비용은 9MB 추가로, 현재 핑퐁 텍스처 2장(18MB) 대비 50% 증가지만 절대적으로는 가볍습니다. 성능 비용은 매 프레임 1500x1500 텍스처 복사 한 번인데, `glBlitFramebuffer`나 `glCopyTexSubImage2D`는 GPU 내부 연산이라 매우 빠릅니다.

**이헤시안**: 성능 관련해서 한 가지 제안이 있어요. `blendDeposits()` 후 전체 맵을 복사하는 대신, **감쇠만 적용하고 확산은 안 한 버전**을 별도로 만드는 건 어떨까요?

```
현재: blendDeposits() -> [미확산 복사] -> runDiffuseDecay(4패스)
제안: blendDeposits() -> runDiffuseDecay(0패스, decay만) -> [감쇠 후 복사]
     -> runDiffuseDecay(4패스, 확산+감쇠)
```

아, 이러면 decay가 두 번 적용되니까 안 되겠네요. 그냥 `blendDeposits()` 직후 복사가 맞습니다.

**박코드**: 네. 그리고 실은 더 깔끔한 방법이 있어요. `runDiffuseDecay()`에서 **첫 번째 패스 전에** 현재 텍스처를 별도 텍스처에 복사하면, decay도 적용 안 된 순수한 "deposit 후" 상태를 캡처할 수 있습니다. 하지만 decay는 0.97이라 한 프레임 차이는 3%밖에 안 돼서, `blendDeposits()` 후든 `runDiffuseDecay()` 전이든 큰 차이 없습니다.

중요한 건 **확산 4패스가 적용되기 전**이라는 점이에요.

**최로드맵**: 미확산 맵 확보 방법이 정리된 것 같습니다. 이제 Hessian ridge detection은 어떻게 구현하나요?

**이헤시안**: 정맥 셰이더(`veins.frag.glsl`)를 전면 재작성해야 합니다. 현재 로직을 Hessian 기반으로 교체하는 거예요.

핵심 GLSL 코드는 이렇습니다:

```glsl
// 미확산 텍스처에서 Hessian 계산 (h = 1 or 2 픽셀)
float h = 1.0;  // STEP
vec2 dx = vec2(h / u_mapSize.x, 0.0);
vec2 dy = vec2(0.0, h / u_mapSize.y);

float center = texture(u_rawTrailMap, uv).r;
float left   = texture(u_rawTrailMap, fract(uv - dx)).r;
float right  = texture(u_rawTrailMap, fract(uv + dx)).r;
float up     = texture(u_rawTrailMap, fract(uv + dy)).r;
float down   = texture(u_rawTrailMap, fract(uv - dy)).r;

float dxx = (left + right - 2.0 * center) / (h * h);
float dyy = (up + down - 2.0 * center) / (h * h);

// 대각 샘플 (dxy 계산에 필요)
float topRight    = texture(u_rawTrailMap, fract(uv + dx + dy)).r;
float topLeft     = texture(u_rawTrailMap, fract(uv - dx + dy)).r;
float bottomRight = texture(u_rawTrailMap, fract(uv + dx - dy)).r;
float bottomLeft  = texture(u_rawTrailMap, fract(uv - dx - dy)).r;

float dxy = (topRight + bottomLeft - topLeft - bottomRight) / (4.0 * h * h);

// 고유값 계산
float trace = dxx + dyy;
float det = dxx * dyy - dxy * dxy;
float discriminant = max(trace * trace * 0.25 - det, 0.0);
float sqrtDisc = sqrt(discriminant);

float lambda1 = 0.5 * trace + sqrtDisc;
float lambda2 = 0.5 * trace - sqrtDisc;

// ridgeness: 큰 음의 고유값 = 능선
float ridgeness = -min(lambda1, lambda2);
```

텍스처 fetch 수는 총 **9개** (center + 상하좌우 4개 + 대각 4개). 현재 셰이더가 3x3 블러(9개) + 능선 검출(4개) = 13개를 쓰니까, 오히려 줄어듭니다.

**박코드**: 9개면 성능에 전혀 문제 없어요. 현재와 동일하거나 더 나은 수준이네요.

그런데 하나 신경 쓰이는 게, 미확산 맵에서 개별 에이전트의 deposit이 "점 노이즈"로 나타날 수 있지 않을까요? 확산이 안 됐으니까 에이전트 하나하나의 deposit이 개별 밝은 점으로 보일 수 있잖아요. Hessian이 이걸 "미세한 능선"으로 잡으면 노이즈가 될 텐데.

**이헤시안**: 좋은 질문이에요. 두 가지 대응이 있습니다.

첫째, 미확산 맵은 "순간 캡처"가 아니라 **누적된** 상태예요. `trail += deposit`이 매 프레임 쌓이고, decay(0.97)로 서서히 줄어드니까, 수송 채널에는 수십~수백 프레임에 걸쳐 에이전트가 반복 통과한 기록이 누적되어 있어요. 단일 에이전트의 deposit(5)에 비해 수송 채널의 누적 값(~167)이 훨씬 높으므로, 개별 deposit의 노이즈는 상대적으로 미미합니다.

둘째, 정말 노이즈가 문제라면, 미확산 맵에 **가벼운 1패스 블러**(sigma=0.5~0.8px)를 적용할 수 있어요. 4패스의 sigma=1.6px와 달리 1패스는 0.8px라 2px 폭의 구조를 충분히 보존합니다. 하지만 이건 실제로 시각적 테스트를 해보고 필요할 때만 추가하면 됩니다.

**Dr. 김점균**: 실물에서도 원형질 흐름에 미세한 요동이 있어요. 약간의 "거친" 느낌이 오히려 자연스러울 수 있습니다. 너무 매끈하면 CG처럼 보이거든요. 노이즈 제거는 보수적으로 접근하는 게 좋겠습니다.

**최로드맵**: 알겠습니다. 그러면 블렌딩 변경 -- additive blend -- 도 논의해 봅시다.

**박코드**: 현재 렌더링 순서는:

```
1. 배경 clearColor (8, 20, 10)
2. 페로몬 등고선: SRC_ALPHA, ONE_MINUS_SRC_ALPHA
3. blob_body: SRC_ALPHA, ONE_MINUS_SRC_ALPHA  (본체 알파 ~0.85)
4. veins: SRC_ALPHA, ONE_MINUS_SRC_ALPHA      <-- 여기를 변경
5. cubic_glow: SRC_ALPHA, ONE  (이미 additive)
```

정맥을 `SRC_ALPHA, ONE` (additive)으로 변경하면:
- 본체가 불투명(0.85)해도 정맥 색상이 **더해지므로** 본체 위에 떠 보임
- 본체 색 (0.86, 0.78, 0.24) + 정맥 색 (0.95, 0.88, 0.35) * alpha -> 밝아짐
- 큐빅 글로우가 이미 같은 방식이라 파이프라인에 일관성 있음

주의점은 포화(saturation)인데요, 정맥 색 + 본체 색이 1.0을 넘으면 화이트아웃이 됩니다. 하지만 GPU가 자동 클램프하고, 정맥의 alpha를 적절히 낮추면(0.85 -> 0.3~0.5) 문제없어요.

**Dr. 김점균**: 밝기 관점에서 보면, additive가 실물에 더 가까워요. 실제로 dark-field 현미경에서 정맥이 밝게 빛나는 건, 농축 원형질이 광학적으로 빛을 더 많이 산란시키기 때문이에요. 본체의 빛 + 정맥의 추가 빛이 합쳐지는 거죠. additive blend가 이 물리 모델에 정확히 대응합니다.

**이헤시안**: 수학적으로 보면, additive blend는 `result = existing + vein * alpha`이고, 기존 alpha blend는 `result = existing * (1-alpha) + vein * alpha`예요. 차이점은 alpha blend가 기존 색을 깎는다는 건데, 정맥이 본체를 "대체"하는 게 아니라 "위에 더해지는" 것이니까, additive가 물리적으로 맞아요.

**최로드맵**: 블렌딩 변경은 코드 한 줄 수정이니 리스크가 매우 낮겠네요. `SceneRenderer.ts` 271행의 `gl.blendFunc`만 바꾸면 됩니다.

**박코드**: 맞아요. 다만 additive로 바꾸면 현재의 alpha 파라미터들이 전부 재조정이 필요해요. additive는 같은 alpha에서 더 밝으니까, `MAJOR_ALPHA`를 0.85에서 0.3~0.5로 낮추고, 색상도 살짝 어둡게 할 필요가 있습니다. 하지만 이건 Phase 3의 Hessian 셰이더와 함께 한번에 튜닝하는 게 효율적이에요.

**Dr. 김점균**: 한 가지 강조하고 싶은 게 있어요. 아까 최 기획자님이 정리해 주신 5가지 요구사항 중 **1번(가느다란 선)과 2번(날카로운 경계)**이 가장 중요하다고 했는데, 이 두 가지는 **미확산 맵 없이는 절대 불가능**합니다.

additive blend나 파라미터 조정만으로는 "밝은 구름"은 만들 수 있어도 "선"은 못 만들어요. 넓게 퍼진 입력에서 좁은 선을 만드는 건 물리적으로 불가능하니까요. 미확산 맵이 **선결 조건**이라고 봅니다.

**이헤시안**: 전적으로 동의합니다. Phase 순서를 잘 정하는 게 중요한데, 미확산 맵 확보를 Phase 2로 미루기보다는...

**최로드맵**: 잠깐요. 현실적인 이유를 말씀드리겠습니다. Phase 1에서 additive blend + 파라미터 조정을 먼저 하는 이유가 있어요. 이건 **구현이 10분이면 끝나고, 즉시 시각적 차이를 확인**할 수 있거든요. "이 방향이 맞는지" 빠르게 검증하는 스프린트예요.

그리고 Phase 1의 결과물이 Phase 2/3의 기반이 되기도 해요. additive blend는 미확산 맵 + Hessian을 적용할 때도 계속 쓸 거니까요.

**이헤시안**: 음, 그것도 맞습니다. 하지만 Phase 1에서 "밝은 구름"이 나왔을 때, "이건 아직 구름이니까 실패다"가 아니라 "블렌딩은 이 방향이 맞다, 다음 단계로"라는 걸 명확히 해두어야 해요. Phase 1을 "최종 결과"로 착각하면 안 됩니다.

**최로드맵**: 맞습니다. Phase 1의 성공 기준을 명확히 하겠습니다.

**Dr. 김점균**: Phase 1의 결과가 "정맥이 본체 위에서 밝게 보인다"면 블렌딩은 성공, "정맥이 여전히 구름 형태다"면 예상대로. Phase 2에서 미확산 맵을 추가하면 형태가 개선되는 걸 확인하고, Phase 3에서 Hessian으로 마무리.

이해했습니다. 단계적 접근에 동의해요. 다만 Phase 2 없이 Phase 3를 건너뛰면 안 된다는 점은 확실히 해두고 싶습니다.

---

## 파트 4: 구현 계획 합의

**최로드맵**: 좋습니다. 지금까지의 논의를 기반으로 3단계 구현 계획을 정리하겠습니다. 각 Phase마다 변경 파일, 검증 기준, 위험 요소를 정리합니다.

### Phase 1: Additive Blend + 파라미터 조정

**목표**: 정맥이 본체 위에서 밝게 "떠 보이는" 효과 확보. 형태 개선은 기대하지 않음.

**변경 파일**:
- `src/gpu/SceneRenderer.ts` -- 정맥 블렌딩을 `SRC_ALPHA, ONE`으로 변경 (271행)
- `src/config.ts` -- VEINS 파라미터 조정:
  - `MAJOR_ALPHA`: 0.85 -> 0.4~0.5 (additive 보정)
  - `MINOR_ALPHA`: 0.15 -> 0.05~0.1 (모세정맥 노이즈 억제)
  - 색상 미세 조정 가능

**예상 공수**: 0.5일

**검증 기준**:
- 정맥이 본체 위에서 확실히 밝게 보임 (스크린샷 비교)
- 화이트아웃(포화) 없음
- 본체 가장자리에서 정맥이 배경 위에 빛남 ("촉수 돌출"의 시작)
- 기존 큐빅 글로우와 시각적 충돌 없음

**위험 요소**: 낮음. 블렌딩 변경은 정맥 레이어에만 영향.

**박코드**: Phase 1은 문제 없습니다. 코드 변경량이 극히 적고 되돌리기도 쉬워요.

---

### Phase 2: 미확산 트레일맵 분리

**목표**: 정맥 렌더링의 입력 데이터 품질을 근본적으로 개선. 확산 전 원본 데이터를 정맥 셰이더에 제공.

**변경 파일**:
- `src/gpu/TrailMapGPU.ts`:
  - 미확산 텍스처 1장 추가 (R32F, 1500x1500)
  - 미확산 FBO 1개 추가
  - `blendDeposits()` 직후 현재 텍스처를 미확산 텍스처로 복사하는 메서드 추가
  - `getCurrentRawTexture()` 접근자 추가
- `src/gpu/SceneRenderer.ts`:
  - `render()` 메서드에 `rawTrailTexture` 파라미터 추가
  - 정맥 렌더패스에서 미확산 텍스처를 `u_rawTrailMap`으로 바인딩
- `src/gpu/shaders/glsl/veins.frag.glsl`:
  - `uniform sampler2D u_rawTrailMap` 추가
  - 기존 3x3 블러를 제거하고, 미확산 텍스처에서 직접 샘플링
  - 능선 검출의 STEP을 8 -> 2로 축소
  - (아직 Hessian은 아님, 기존 center-avg 방식 유지하되 입력만 교체)
- `src/gpu/shaders/veins.ts`: 미확산 텍스처 관련 placeholder 추가
- `src/config.ts`: `VEINS.STEP`을 8 -> 2로 변경
- 게임 루프(`useGameLoop.ts` 등)에서 `rawTrailTexture`를 렌더러에 전달

**예상 공수**: 1~2일

**검증 기준**:
- 정맥이 확산 맵 대비 **확실히 좁아짐** (폭 비교)
- 정맥 경계가 날카로워짐 (이전의 부드러운 그라데이션 -> 뚜렷한 전환)
- 시뮬레이션 동역학에 영향 없음 (에이전트 행동 동일)
- 성능 저하 없음 (FPS 유지)
- 개별 에이전트 노이즈가 심하지 않음 (필요시 1패스 블러 추가)

**위험 요소**:
- 중간: FBO 관리 복잡도 증가. 텍스처 복사 타이밍이 중요 (확산 전에 해야 함)
- 낮음: 메모리 9MB 추가 (무시 가능)

**이헤시안**: Phase 2에서 한 가지 제안이요. STEP을 2로 줄이면 기존의 center-avg 방식으로도 상당한 개선이 있을 거예요. 미확산 맵 + STEP=2이면 검출 범위가 4px이 되는데, 2~5px 폭의 정맥에 거의 딱 맞습니다.

다만 이 단계에서도 "선 vs 면" 구분은 못 하기 때문에, 밀집 영역 중심부가 넓게 잡힐 수 있어요. 그래도 확산 맵 + STEP=8보다는 **압도적으로** 나을 겁니다.

**Dr. 김점균**: 실제로 80% 개선이 이 단계에서 나올 것 같아요. 입력 데이터가 깨끗하면 단순한 방법으로도 꽤 좋은 결과가 나오거든요. 마치 좋은 현미경이 있으면 단순한 염색으로도 구조가 잘 보이는 것처럼.

**박코드**: `TrailMapGPU`에서 텍스처 복사를 구현하는 두 가지 방법이 있는데:

1. **`glBlitFramebuffer`**: 가장 빠르지만, 소스와 대상의 포맷이 정확히 일치해야 함
2. **`glCopyTexSubImage2D`**: 현재 bound FBO에서 읽어서 텍스처에 복사. 약간 제약적

제가 보기에 1번이 깔끔합니다. `blendDeposits()` 후 현재 FBO를 READ_FRAMEBUFFER에 바인딩하고, 미확산 FBO를 DRAW_FRAMEBUFFER에 바인딩해서 blit하면 됩니다.

아니면 더 간단하게, **fullscreen quad + 단순 복사 셰이더**(passthrough)로 한 패스 그리는 것도 방법이에요. 이미 quad와 셰이더 인프라가 있으니까요. 성능 차이는 무시 가능합니다.

**최로드맵**: 두 방법 중 구현이 더 간단하고 확실한 걸로 갑시다.

**박코드**: `glBlitFramebuffer`가 가장 깔끔합니다. 셰이더 불필요, 코드 3줄이면 됩니다:

```typescript
// blendDeposits() 직후
gl.bindFramebuffer(gl.READ_FRAMEBUFFER, currentFbo);
gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, rawTrailFbo);
gl.blitFramebuffer(0, 0, width, height, 0, 0, width, height, gl.COLOR_BUFFER_BIT, gl.NEAREST);
```

---

### Phase 3: Hessian Ridge Detection

**목표**: 미확산 맵에서 선형 구조만 정밀 추출. "선 vs 면" 구분으로 구름 현상 근본 제거.

**변경 파일**:
- `src/gpu/shaders/glsl/veins.frag.glsl`: 전면 재작성
  - 3x3 블러, center-avg 능선 검출 제거
  - Hessian 행렬 기반 고유값 능선 검출으로 교체
  - 미확산 텍스처 기반 (Phase 2에서 확보)
  - 멀티스케일 선택적 적용 (h=1과 h=2에서 max)
  - ridgeness 기반 알파 계산 (이전의 4단계 곱셈 체인 단순화)
- `src/gpu/shaders/veins.ts`: placeholder 업데이트
- `src/config.ts`: VEINS 파라미터 재구성
  - `STEP` 제거 -> `HESSIAN_SCALE_1`, `HESSIAN_SCALE_2`
  - `RIDGE_SCALE` -> `RIDGENESS_THRESHOLD`, `RIDGENESS_SCALE`
  - `MAJOR_THRESHOLD` 유지, `MAJOR_ALPHA`/`MINOR_ALPHA` 재튜닝

**예상 공수**: 1~2일

**검증 기준**:
- 정맥 폭이 2~5px로 유지됨
- 경계가 1~2px 이내에서 전환됨
- 본체 중심의 넓은 고밀도 영역이 정맥으로 오검출되지 않음
- 분기 구조가 시각적으로 드러남
- 본체 대비 밝기 차이 2~4배

**위험 요소**:
- 중간: Hessian 파라미터 튜닝이 필요 (ridgeness threshold, scale)
- 낮음: 텍스처 fetch 수 동일 또는 감소 (성능 문제 없음)

**이헤시안**: Phase 3 셰이더의 핵심 구조를 좀 더 구체적으로 제안하겠습니다.

```glsl
// veins.frag.glsl (Phase 3 최종 형태 개요)

uniform sampler2D u_rawTrailMap;  // 미확산 텍스처
uniform sampler2D u_trailMap;     // 확산 텍스처 (본체 영역 마스킹용)

void main() {
    // 1. 본체 영역 마스킹 (확산 맵 기반)
    float bodyValue = texture(u_trailMap, trailUV).r;
    if (bodyValue < VEIN_MIN) { discard; }

    // 2. 미확산 맵에서 Hessian 계산
    // Scale 1 (h=1): 가느다란 정맥 검출
    float ridgeness1 = computeHessianRidge(u_rawTrailMap, trailUV, 1.0);
    // Scale 2 (h=2): 굵은 주정맥 검출 (선택적)
    float ridgeness2 = computeHessianRidge(u_rawTrailMap, trailUV, 2.0);
    float ridgeness = max(ridgeness1, ridgeness2);

    // 3. 강도 매핑 (간단하게)
    float intensity = smoothstep(threshold, threshold * 2.0, ridgeness);

    // 4. 맥동 + 색상 + 알파
    float alpha = intensity * layerAlpha * pulse;
    fragColor = vec4(veinColor, alpha);
}
```

멀티스케일을 쓰면 텍스처 fetch가 9(h=1) + 9(h=2) = 18개가 되는데, 이 중 center 1개는 공유 가능하고, 현실적으로 h=2 스케일의 대각 샘플을 h=1의 직교 샘플로 근사하면 추가 fetch를 줄일 수 있습니다. 하지만 18 fetches도 현대 GPU에서는 전혀 문제없어요.

**박코드**: 1500x1500 풀스크린에서 18 fetches... 문제 없습니다. 현재 셰이더보다 오히려 분기(if/discard)가 줄어서 더 빠를 수도 있어요.

한 가지 구현 팁을 드리자면, 멀티스케일은 처음에 단일 스케일(h=1)로 시작하고, 결과를 보면서 h=2를 추가하는 게 좋습니다. 미확산 맵에서 h=1 Hessian만으로도 상당히 좋은 결과가 나올 거예요.

**Dr. 김점균**: 멀티스케일이 중요한 이유가 하나 더 있어요. 실제 점균류에서 주정맥(약 3~5px)과 모세정맥(1~2px)의 폭이 다르거든요. h=1은 모세정맥에, h=2는 주정맥에 최적화되니까, 둘 다 잡으려면 멀티스케일이 맞습니다.

하지만 코드님 말씀처럼 처음에 h=1로 시작하는 게 맞아요. 한 번에 다 하면 튜닝이 복잡해지니까.

**최로드맵**: 좋습니다. 전체 구현 계획을 최종 정리합니다.

---

### 최종 합의 -- 3단계 구현 로드맵

```
Phase 1: Additive Blend (0.5일)
  목표: 정맥 밝기 개선, 본체 위에 "떠 보이는" 효과
  효과: 50% 개선 (블렌딩 + 밝기만, 형태는 그대로)
  변경: SceneRenderer.ts (1줄), config.ts (2~3 파라미터)
  위험: 매우 낮음

Phase 2: 미확산 트레일맵 분리 (1~2일)
  목표: 정맥 검출 입력 품질 근본 개선
  효과: 80% 개선 (정맥 폭 축소, 경계 선명화)
  변경: TrailMapGPU.ts, SceneRenderer.ts, veins.frag.glsl, config.ts
  위험: 중간 (FBO 관리, 텍스처 전달)

Phase 3: Hessian Ridge Detection (1~2일)
  목표: 선형 구조만 정밀 추출, 구름 현상 근본 제거
  효과: 95% 개선 (선 vs 면 구분, 2~5px 정맥)
  변경: veins.frag.glsl (전면 재작성), veins.ts, config.ts
  위험: 중간 (파라미터 튜닝)
```

**총 공수**: 3~5일
**누적 효과**: Phase 1(50%) -> Phase 2(80%) -> Phase 3(95%)

---

**Dr. 김점균**: 이 계획대로라면 제 점균류가 나올 것 같아요. Phase 2가 끝나면 한번 보여주세요. 그때 "아, 이건 내 점균류다!" 할 수 있을 것 같습니다.

한 가지만 부탁드릴게요. 매 Phase가 끝날 때마다 레퍼런스 이미지와 나란히 스크린샷 비교를 해주세요. 수치만으로는 판단이 어렵고, 결국 **눈으로 봐야** 알 수 있는 영역이거든요. 20년 동안 점균류를 봐 온 눈이 최종 검증 도구입니다.

**박코드**: 물론이죠. 각 Phase 완료 시 같은 시뮬레이션 상태에서 스크린샷을 찍어 비교하겠습니다. 줌인 뷰와 전체 뷰 양쪽 다.

**이헤시안**: 저도 각 Phase에서 ridgeness 분포의 히스토그램을 시각화해서 "수학적으로 잘 작동하는지" 확인하겠습니다. 값이 bimodal(능선과 비능선이 뚜렷이 분리)이면 성공, unimodal(전부 비슷한 값)이면 아직 개선이 필요한 거예요.

**최로드맵**: 완벽합니다. 그러면 Phase 1부터 시작하겠습니다. 모두 동의하시죠?

**전원**: 동의합니다.

---

## 부록: 기술 상세

### A. 파일별 변경 상세

| Phase | 파일 | 변경 내용 |
|-------|------|----------|
| 1 | `src/gpu/SceneRenderer.ts` | 271행: `ONE_MINUS_SRC_ALPHA` -> `ONE` |
| 1 | `src/config.ts` | `VEINS.MAJOR_ALPHA`: 0.85->0.4, `MINOR_ALPHA`: 0.15->0.08 |
| 2 | `src/gpu/TrailMapGPU.ts` | `rawTrailTex`, `rawTrailFbo` 추가, `captureRawTrail()` 메서드, `getCurrentRawTexture()` 접근자 |
| 2 | `src/gpu/SceneRenderer.ts` | `render()`에 `rawTrailTexture` 파라미터, 정맥 패스에서 바인딩 |
| 2 | `src/gpu/shaders/glsl/veins.frag.glsl` | `u_rawTrailMap` uniform 추가, 3x3 블러 제거, rawTrailMap에서 직접 샘플링 |
| 2 | `src/gpu/shaders/veins.ts` | 미확산 텍스처 uniform placeholder |
| 2 | `src/config.ts` | `VEINS.STEP`: 8->2 |
| 2 | 게임 루프 | `rawTrailTexture` 전달 |
| 3 | `src/gpu/shaders/glsl/veins.frag.glsl` | 전면 재작성: Hessian 고유값 ridge |
| 3 | `src/gpu/shaders/veins.ts` | 신규 placeholder (HESSIAN_SCALE 등) |
| 3 | `src/config.ts` | VEINS 파라미터 재구성 |

### B. 미확산 맵 텍스처 복사 타이밍

```
매 프레임 파이프라인:
  1. 에이전트 GPU 업데이트 (이동, 방향 결정)
  2. deposit 텍스처에 에이전트 deposit 기록
  3. blendDeposits()  -- trail += deposit
  4. ★ captureRawTrail()  -- 미확산 텍스처로 복사
  5. runDiffuseDecay(4패스) -- 확산 + 감쇠
  6. 렌더링 (본체: 확산맵, 정맥: 미확산맵)
```

### C. Hessian Ridge Detection -- GLSL 참조 구현

```glsl
float computeHessianRidge(sampler2D tex, vec2 uv, float h) {
    vec2 dx = vec2(h / u_mapSize.x, 0.0);
    vec2 dy = vec2(0.0, h / u_mapSize.y);

    float c  = texture(tex, uv).r;
    float l  = texture(tex, fract(uv - dx)).r;
    float r  = texture(tex, fract(uv + dx)).r;
    float u  = texture(tex, fract(uv + dy)).r;
    float d  = texture(tex, fract(uv - dy)).r;
    float tr = texture(tex, fract(uv + dx + dy)).r;
    float tl = texture(tex, fract(uv - dx + dy)).r;
    float br = texture(tex, fract(uv + dx - dy)).r;
    float bl = texture(tex, fract(uv - dx - dy)).r;

    float h2 = h * h;
    float dxx = (l + r - 2.0 * c) / h2;
    float dyy = (u + d - 2.0 * c) / h2;
    float dxy = (tr + bl - tl - br) / (4.0 * h2);

    float trace = dxx + dyy;
    float det = dxx * dyy - dxy * dxy;
    float disc = max(trace * trace * 0.25 - det, 0.0);

    float lambda1 = 0.5 * trace + sqrt(disc);
    float lambda2 = 0.5 * trace - sqrt(disc);

    // 큰 음의 고유값 = 능선
    return -min(lambda1, lambda2);
}
```

### D. 성능 예산

| 항목 | 현재 | Phase 2 | Phase 3 |
|------|------|---------|---------|
| 정맥 셰이더 tex fetch | 13 | 5~9 | 9~18 |
| 추가 메모리 | 0 | 9MB | 0 (Phase 2 포함) |
| 추가 GPU 복사 | 0 | 1회/프레임 (blit) | 0 |
| FPS 영향 | - | 무시 가능 | 무시 가능 |

### E. 롤백 전략

- Phase 1: `git revert` 한 커밋. SceneRenderer 블렌딩 한 줄 + config 파라미터.
- Phase 2: 미확산 텍스처/FBO 제거, 정맥 셰이더를 이전 버전으로 복원.
- Phase 3: 정맥 셰이더만 Phase 2 버전으로 되돌림.

각 Phase가 독립적이므로, 어느 단계에서든 이전 Phase로 안전하게 되돌릴 수 있음.
