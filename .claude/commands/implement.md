# 구현 시작

plan.md를 기반으로 feature branch를 생성하고 구현을 진행한다.

## 전제 조건
- `specs/[feature-name]/spec.md` + `plan.md` 모두 존재하고 사용자 확인 완료

## 실행 절차

### 1. Branch 생성
```bash
git checkout -b feat/[feature-name] main
```

### 2. Spec/Plan 커밋
```bash
git add specs/[feature-name]/
git commit -m "docs: [feature-name] spec/plan 문서"
```
- 코드 변경 전, 문서만 먼저 커밋

### 3. 구현
- plan.md의 Step 순서대로 구현
- 각 Step 완료 시 검증 수행
- TodoWrite로 진행 상황 추적

### 4. 검증
- `npm run build` 통과 확인
- spec/plan 문서에 변경사항 반영 (필요 시)

### 5. 완료 체크리스트
구현 커밋 전 반드시 확인:
- [ ] `npm run build` 통과
- [ ] 디버그 코드 제거 (console.log, early return, 테스트용 하드코딩 등)
- [ ] spec/plan 문서 최신 상태 반영

### 6. 구현 커밋
```bash
git add [수정된 파일들]
git commit -m "feat: [구현 내용 요약]"
```

### 7. Main 병합
```bash
git checkout main
git merge --no-ff feat/[feature-name]
```
- **`--no-ff` 필수** — merge commit으로 브랜치 히스토리 보존

### 8. 정리
```bash
git branch -d feat/[feature-name]
```
