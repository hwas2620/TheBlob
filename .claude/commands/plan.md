# Plan 작성

spec.md를 기반으로 `specs/[feature-name]/plan.md` 구현 계획을 작성한다.

## 전제 조건
- `specs/[feature-name]/spec.md`가 이미 존재하고 사용자 확인 완료

## 실행 절차

### 1. Spec 확인
- 해당 spec.md를 읽고 요구사항 재확인
- 관련 코드를 상세 분석 (수정 대상 파일, 함수, 의존성)

### 2. plan.md 작성

`specs/[feature-name]/plan.md` 파일을 아래 구조로 작성:

```markdown
# [기능명] 구현 계획

## 수정 파일
| 파일 | 변경 내용 |
|------|----------|
| ...  | ...      |

## 구현 단계

### Step 1: [제목]
- 변경 내용 상세
- 파일: `path/to/file.ts`

### Step 2: [제목]
- ...
- 의존: Step 1

### Step N: 검증
- `npm run build` 통과
- 동작 확인 방법

## 의존성 그래프 (선택)
Step 1 → Step 2 → Step 3
                 ↘ Step 4

## 위험 요소 (선택)
- 주의할 점, 잠재적 문제
```

### 3. 사용자 확인
- 작성한 plan을 사용자에게 보여주고 확인 요청
- 수정 요청이 있으면 반영
- **다음 단계**: `/implement` 스킬로 구현 시작
