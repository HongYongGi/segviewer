# CLAUDE.md — SegViewer Repository Harness

## 프로젝트 한 줄 요약
nnUNetv2 기반 CT 의료영상 다중 클래스 세그멘테이션 뷰어 웹앱 (연구실 내부용)

## 프로젝트 개요
연구실 팀원(5~15명)이 브라우저에서 NIfTI CT 영상을 업로드하고,
nnUNet 모델로 세그멘테이션을 실행하며, 2D/3D로 시각화하고,
브러시/지우개로 편집한 뒤 NIfTI로 저장하는 내부 전용 도구.

---

## 기술 스택 (반드시 준수)

### Backend
- **FastAPI** (Python 3.10+)
- **nnUNetv2** 공식 `nnUNetPredictor` — 자체 전/후처리 금지
- nibabel, numpy, SimpleITK, PyTorch+CUDA
- asyncio 기반 task queue (Celery/Redis 아님)
- CORS: `allow_origins=["*"]` (내부망 전용)

### Frontend
- **React 18+** TypeScript (any 타입 금지)
- **Cornerstone3D** (@cornerstonejs/core, @cornerstonejs/tools)
- **Zustand** (Redux/MobX 금지)
- axios, Vite
- Tailwind CSS, 다크 테마 기본

### 인프라
- Docker Compose (한 줄 실행)
- 단일 GPU 서버 전제
- DB 없음 — 파일시스템 기반
- 인증/인가 없음 (내부망 전용)

---

## 디렉토리 구조

```
segviewer/
├── CLAUDE.md              # 이 파일 (에이전트 harness)
├── backend/
│   └── app/
│       ├── main.py        # FastAPI 앱 + CORS + 커스텀 헤더
│       ├── config.py      # pydantic-settings 기반 설정
│       ├── routers/       # API 엔드포인트 (/api/images, /api/models, ...)
│       ├── services/      # 비즈니스 로직 (ImageService, InferenceService, ...)
│       └── utils/         # 유틸리티
├── frontend/
│   └── src/
│       ├── App.tsx
│       ├── api/           # axios 클라이언트
│       ├── components/    # Layout, Toolbar, Sidebar, ...
│       ├── viewers/       # ViewerGrid, SliceViewport, VolumeViewport
│       ├── editors/       # BrushEditor, EraserEditor, UndoManager
│       ├── stores/        # Zustand 스토어
│       ├── types/         # TypeScript 타입 정의
│       └── utils/         # arrayBuffer, colormap, ...
├── docker-compose.yml
├── .env.example
├── .gitignore
└── docs/                  # 설계 문서
    ├── design-docs/       # 설계 결정과 근거 (왜?)
    ├── product-specs/     # 기능 스펙 (무엇?)
    ├── exec-plans/        # 실행 계획 (언제, 어떻게?)
    └── references/        # 기술 참고자료
```

---

## 핵심 원칙 (우선순위 순)

1. **데이터 무결성**: NIfTI 헤더(affine, spacing) 보존, CT HU 값 변환 금지
2. **nnUNet 파이프라인 존중**: 공식 nnUNetPredictor만 사용, 자체 전/후처리 금지
3. **연구자의 시간**: 업로드 → 결과 확인 클릭 3번 이내, 합리적 기본값
4. **단순함**: 모놀리식, DB 없음, 최소 추상화
5. **동작하는 것 먼저**: P0 MVP 우선, 과도한 최적화보다 정확한 동작

---

## 절대 하지 말 것 (DO NOT)

1. nnUNet training 코드 건드리지 말 것
2. weight 파일 수정/삭제/이동 금지
3. 환자 데이터 외부 전송 금지 (외부 API 호출 금지)
4. Backend에서 HTML 렌더링 금지 (Backend=API, Frontend=시각화)
5. Frontend에서 파일시스템 직접 접근 금지
6. CT HU 원본 값 저장 단계에서 변환 금지
7. nnUNet 전/후처리 자체 구현 금지
8. Redux/MobX 등 과도한 상태관리 사용 금지
9. DB(PostgreSQL, MySQL 등) 도입 금지
10. 인증/인가 시스템 구현 금지

---

## 로드맵

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 0 | 프로젝트 기반 세팅 (Docker, FastAPI 뼈대, React 뼈대) | 완료 |
| Phase 1 | MVP (업로드, 2D 뷰어, W/L, 모델 목록, inference, 오버레이) | 완료 |
| Phase 2 | 3D 렌더링 + 브러시/지우개 편집 | 완료 |
| Phase 3 | 편의기능 (다운로드, 히스토리, GPU 모니터링) | 완료 |

---

## 문서 참조 맵

작업별로 어떤 문서를 읽어야 하는지 안내한다.

### 전체 방향 이해
- `docs/design-docs/core-beliefs.md` — 설계 철학
- `docs/product-specs/index.md` — 기능 목록 및 우선순위
- `docs/product-specs/PRODUCT_SENSE.md` — 제품 판단 기준

### Backend 작업
- `docs/design-docs/ARCHITECTURE.md` — 시스템 구조, 레이어 설계
- `docs/design-docs/nnunet-integration.md` — nnUNet 통합 전략
- `docs/design-docs/data-transfer-strategy.md` — NIfTI 데이터 전송
- `docs/design-docs/gpu-memory-management.md` — GPU 메모리 관리
- `docs/references/nnunetv2-api.md` — nnUNetPredictor API 참고

### Frontend 작업
- `docs/design-docs/ARCHITECTURE.md` — Frontend 레이어 설계
- `docs/design-docs/frontend-stack.md` — 기술 스택 결정 근거
- `docs/references/cornerstone3d.md` — Cornerstone3D 사용법
- `docs/product-specs/DESIGN.md` — UI/UX 디자인 가이드
- `docs/product-specs/FRONTEND.md` — Frontend 코딩 규칙

### 기능별 스펙
- `docs/product-specs/image-upload-and-view.md` — 영상 업로드 + 뷰어 + W/L
- `docs/product-specs/inference-pipeline.md` — 모델 목록 + inference 실행
- `docs/product-specs/segmentation-overlay.md` — 오버레이 + 표시/숨김 + 3D 표면
- `docs/product-specs/segmentation-editor.md` — 브러시/지우개 + Undo/Redo + 저장
- `docs/product-specs/model-management.md` — 모델 메모/태그 (P2)

### 실행 계획
- `docs/exec-plans/PLANS.md` — 전체 로드맵
- `docs/exec-plans/phase-0-foundation.md` ~ `phase-3-polish.md`

### 품질 및 안정성
- `docs/product-specs/QUALITY_SCORE.md` — 품질 기준
- `docs/product-specs/RELIABILITY.md` — 에러 처리 가이드
- `docs/product-specs/SECURITY.md` — 보안 가이드
- `docs/design-docs/tech-debt-tracker.md` — 기술 부채 추적

---

## API 규칙 요약

- 모든 엔드포인트 prefix: `/api/`
- 에러 응답 포맷: `{ "error": "CODE", "message": "설명", "detail": {} }`
- 바이너리 데이터: `application/octet-stream` + 커스텀 헤더 (`X-Image-Shape`, `X-Image-Dtype`, ...)
- 볼륨 데이터: Little-endian, Float32, C-contiguous
- 세그멘테이션 데이터: Little-endian, Uint8
- 진행률: WebSocket (`/ws/inference/{job_id}`)

---

## 환경변수 (`.env`)

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| NNUNET_RESULTS_PATH | 필수 | - | nnUNet_results 디렉토리 경로 |
| UPLOAD_DIR | 선택 | ./uploads | 업로드 파일 저장 경로 |
| RESULTS_DIR | 선택 | ./results | inference 결과 저장 경로 |
| MAX_UPLOAD_SIZE_MB | 선택 | 500 | 최대 업로드 크기 (MB) |
| MAX_CACHED_MODELS | 선택 | 2 | GPU에 캐싱할 최대 모델 수 |
| GPU_DEVICE_INDEX | 선택 | 0 | 사용할 GPU 인덱스 |
| LOG_LEVEL | 선택 | INFO | 로그 레벨 |

---

## 코딩 규칙

### Python (Backend)
- 함수 50줄 이내
- 타입 힌트 필수
- `from nnunetv2` import는 **오직 InferenceService에서만**
- 에러 응답은 통일된 JSON 포맷

### TypeScript (Frontend)
- `any` 타입 금지
- 함수형 컴포넌트만 사용
- Props는 interface로 정의
- 컴포넌트 150줄 이내
- Cornerstone3D 초기화는 useEffect에서, cleanup 필수
