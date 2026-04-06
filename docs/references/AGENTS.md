# AGENTS.md

## 프로젝트 한 줄 요약
nnUNetv2 기반 CT 의료영상 다중 클래스 세그멘테이션 뷰어 웹앱 (연구실 내부용)

## 프로젝트 개요
연구실 내부 팀원들이 브라우저에서 NIfTI(.nii.gz) CT 영상을 업로드하고,
사전 학습된 nnUNet 모델로 실시간 다중 클래스 세그멘테이션을 수행하며,
결과를 2D 슬라이스(Axial/Coronal/Sagittal) + 3D 볼륨 렌더링으로 시각화하고,
브러시/지우개 도구로 픽셀 단위 편집까지 할 수 있는 내부 전용 도구.

### 핵심 사용 시나리오
1. 연구원이 CT .nii.gz 파일을 업로드한다
2. nnUNet_results에서 원하는 모델(Dataset/Trainer/Config)을 선택한다
3. GPU 서버에서 실시간 inference가 실행된다
4. 원본 CT 위에 다중 클래스 세그멘테이션이 컬러 오버레이로 표시된다
5. 필요 시 브러시/지우개로 세그멘테이션을 수정한다
6. 수정된 결과를 NIfTI로 저장/다운로드한다

---

## 기술 스택 (반드시 준수 — 임의로 변경 금지)

### Backend
- **프레임워크**: FastAPI (Python 3.10+)
- **Inference 엔진**: nnUNetv2 공식 `nnUNetPredictor` 클래스
- **영상 처리**: nibabel (NIfTI I/O), numpy, SimpleITK
- **GPU**: PyTorch + CUDA (torch.cuda 필수)
- **비동기 처리**: asyncio 기반 task queue (Celery는 P2에서 검토)
- **CORS**: FastAPI CORSMiddleware (연구실 내부망이므로 allow_origins=["*"])

### Frontend
- **프레임워크**: React 18+ with TypeScript
- **의료영상 뷰어**: Cornerstone3D (@cornerstonejs/core, @cornerstonejs/tools)
- **3D 렌더링**: Cornerstone3D VolumeViewport + VTK.js (내부 의존)
- **상태관리**: Zustand 또는 React Context (Redux 사용 금지 — 과도한 보일러플레이트)
- **HTTP 통신**: axios
- **빌드**: Vite

### 인프라
- **배포 환경**: 연구실 내부 GPU 서버 (로컬 네트워크)
- **컨테이너**: Docker Compose (backend + frontend 분리)
- **리버스 프록시**: nginx (선택)

---

## 핵심 원칙

### 1. 데이터 무결성 (최우선)
- NIfTI 헤더의 affine matrix, spacing(pixdim), orientation(qform/sform)을
  어떤 처리 단계에서도 절대 손상시키지 않는다
- 세그멘테이션 결과 저장 시 원본 영상의 affine/spacing을 그대로 복사한다
- CT Hounsfield Unit 값을 임의로 클리핑하거나 정규화하지 않는다
  (윈도우/레벨은 **표시 단계에서만** 적용)

### 2. nnUNet 파이프라인 존중
- 자체 inference 로직(전처리/후처리/앙상블)을 절대 구현하지 않는다
- 반드시 nnUNetv2의 `nnUNetPredictor` 클래스를 사용한다
- nnUNet이 요구하는 파일명 규칙({CASE_ID}_0000.nii.gz)을 자동 적용한다
- dataset.json의 labels 딕셔너리를 세그멘테이션 클래스 이름의 유일한 소스로 사용한다

### 3. Weight 관리 정책
- 모든 weight는 환경변수 `nnUNet_results`가 가리키는 경로에서 읽는다
- 표준 경로: `nnUNet_results/Dataset{ID}_{Name}/nnUNetTrainer__nnUNetPlans__{config}/`
- weight 파일을 복사/이동/수정/삭제하지 않는다 (읽기 전용 취급)
- 모델 목록은 디렉토리 구조를 스캔하여 동적으로 생성한다

### 4. 관심사 분리
- Backend: inference 실행, NIfTI 파일 I/O, 메타데이터 추출 (API만 제공)
- Frontend: 시각화, 편집 UI, 사용자 인터랙션 (파일시스템 직접 접근 금지)
- Backend에서 HTML을 렌더링하지 않는다
- Frontend에서 Python 코드를 실행하지 않는다

### 5. 단순함 우선
- 불필요한 추상화 계층을 만들지 않는다
- ORM을 사용하지 않는다 (DB 없이 파일시스템 기반으로 시작)
- 마이크로서비스로 분리하지 않는다 (모놀리식 Backend 유지)
- 설정은 환경변수와 .env 파일로 관리한다

---

## 디렉토리 구조

```
project-root/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 앱 엔트리포인트
│   │   ├── config.py            # 환경변수, 경로 설정
│   │   ├── routers/
│   │   │   ├── images.py        # /api/images/* 엔드포인트
│   │   │   ├── inference.py     # /api/inference/* 엔드포인트
│   │   │   ├── models.py        # /api/models/* 엔드포인트
│   │   │   └── segments.py      # /api/segments/* 엔드포인트
│   │   ├── services/
│   │   │   ├── image_service.py     # NIfTI 로드/저장/변환
│   │   │   ├── inference_service.py # nnUNet predictor 래핑
│   │   │   ├── model_service.py     # 모델 탐색/목록
│   │   │   └── segment_service.py   # 세그멘테이션 결과 관리
│   │   └── utils/
│   │       ├── nifti_utils.py   # NIfTI 헤더/데이터 유틸
│   │       └── gpu_utils.py     # GPU 메모리 관리
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api/                 # Backend API 호출 래퍼
│   │   ├── components/          # 공통 UI 컴포넌트
│   │   ├── viewers/             # 2D/3D 뷰어 모듈
│   │   ├── editors/             # 브러시/지우개 편집 도구
│   │   ├── stores/              # 상태 관리
│   │   └── types/               # TypeScript 타입 정의
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
├── .env                         # nnUNet_results 경로 등
├── uploads/                     # 업로드된 NIfTI 임시 저장
├── results/                     # 세그멘테이션 결과 저장
├── AGENTS.md
├── ARCHITECTURE.md
└── docs/
```

---

## 절대 하지 말 것 (DO NOT)

1. nnUNet의 training 코드를 건드리지 말 것
2. weight 파일을 수정/삭제/이동하지 말 것
3. 환자 데이터를 외부 네트워크로 전송하지 말 것
4. Backend에서 직접 HTML을 렌더링하지 말 것
5. Frontend에서 직접 파일시스템에 접근하지 말 것
6. CT HU 원본 값을 저장 단계에서 변환하지 말 것
7. nnUNet의 전처리/후처리를 자체 구현하지 말 것
8. Redux, MobX 등 과도한 상태관리 라이브러리를 도입하지 말 것
9. DB(PostgreSQL, MongoDB 등)를 도입하지 말 것 (파일시스템 기반)
10. 인증/인가 시스템을 구현하지 말 것 (내부망 전용)

---

## 문서 구조 안내
- `ARCHITECTURE.md` → 시스템 구조, 레이어 설계, 데이터 흐름
- `docs/product-specs/` → 기능별 상세 스펙 (API 포맷, UI 동작, 에러 처리)
- `docs/design-docs/` → 설계 철학, 핵심 기술 결정 근거
- `docs/exec-plans/` → 구현 단계별 계획, 작업 순서
- `docs/references/` → 외부 라이브러리 참고 자료
