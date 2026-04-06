# PLANS.md — 전체 계획 요약

## 한 줄 요약
nnUNetv2 CT 세그멘테이션 뷰어. FastAPI + React + Cornerstone3D.
Phase 0(세팅) → Phase 1(MVP) → Phase 2(3D+편집) → Phase 3(편의기능).

---

## 로드맵 한눈에 보기

```
Phase 0 (1~2일)    Phase 1 (1~2주)      Phase 2 (1~2주)      Phase 3 (선택)
─────────────────────────────────────────────────────────────────────────
프로젝트 세팅       NIfTI 업로드          3D 볼륨 렌더링        다운로드
Docker 설정        2D 슬라이스 뷰어      세그멘테이션 3D 표면   히스토리
FastAPI 뼈대       윈도우/레벨           브러시/지우개          모델 메모
React 뼈대         모델 목록             Undo/Redo            최적화
                   Inference 실행       편집 저장              모니터링
                   오버레이 표시
                   ─────────────
                   ★ MVP 완성 ★
```

## 상세 계획
→ `docs/exec-plans/active/` 참조

## 기능 스펙
→ `docs/product-specs/` 참조

## 설계 결정
→ `docs/design-docs/` 참조
