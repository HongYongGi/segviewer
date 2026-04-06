# ARCHITECTURE.md

## 시스템 구조 (High-Level)

```
┌─────────────────────────────────────────────────┐
│                Browser (React App)               │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ 2D Viewer│ │ 3D Viewer│ │ Seg Editor       │ │
│  │ (Axial/  │ │ (Volume  │ │ (Brush/Eraser)   │ │
│  │ Cor/Sag) │ │ Render)  │ │                  │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│         Cornerstone3D + VTK.js                   │
└─────────────────┬───────────────────────────────┘
                  │ REST API (JSON + ArrayBuffer)
                  │ WebSocket (progress updates)
┌─────────────────▼───────────────────────────────┐
│              FastAPI Backend                      │
│  ┌───────────────────────────────────────────┐   │
│  │ API Layer (Routers)                       │   │
│  │  /api/images/   → 업로드, 슬라이스, 볼륨   │   │
│  │  /api/models/   → 모델 목록 조회           │   │
│  │  /api/inference/ → 추론 실행, 진행상황     │   │
│  │  /api/segments/  → 결과 저장/조회/수정     │   │
│  └───────────────────┬───────────────────────┘   │
│  ┌───────────────────▼───────────────────────┐   │
│  │ Service Layer (비즈니스 로직)               │   │
│  │  ImageService    → NIfTI I/O, 메타데이터   │   │
│  │  ModelService    → nnUNet_results 스캔     │   │
│  │  InferenceService → nnUNetPredictor 관리   │   │
│  │  SegmentService  → 결과 CRUD              │   │
│  └───────────────────┬───────────────────────┘   │
│  ┌───────────────────▼───────────────────────┐   │
│  │ nnUNet Integration Layer                  │   │
│  │  nnUNetPredictor 인스턴스 관리             │   │
│  │  모델 로딩/캐싱 (GPU VRAM)                │   │
│  │  predict_from_raw_data 호출               │   │
│  └───────────────────────────────────────────┘   │
└─────────────────┬───────────────────────────────┘
                  │ 파일 읽기 (읽기 전용)
┌─────────────────▼───────────────────────────────┐
│            nnUNet_results/ (모델 weights)         │
│  Dataset001_Liver/                               │
│    nnUNetTrainer__nnUNetPlans__3d_fullres/        │
│      fold_0/ fold_1/ ... dataset.json            │
└─────────────────────────────────────────────────┘
```

---

## Backend 상세 레이어 설계

### 1. API Layer (FastAPI Routers)
**역할**: HTTP 요청/응답 처리, 입력 검증, 에러 응답 포맷팅

- 모든 엔드포인트는 `/api/` prefix를 사용한다
- 요청 검증은 Pydantic 모델로 수행한다
- 에러 응답은 통일된 JSON 포맷을 따른다:
  `{ "error": "ERROR_CODE", "message": "사람이 읽을 수 있는 설명", "detail": {} }`
- 바이너리 데이터(영상 볼륨, 슬라이스)는 `Response(content=bytes, media_type="application/octet-stream")`으로 반환
- 메타데이터는 커스텀 헤더로 함께 전달:
  `X-Image-Shape`, `X-Image-Dtype`, `X-Image-Spacing`

### 2. Service Layer (비즈니스 로직)
**역할**: 실제 로직 수행, Router에서 분리하여 테스트 가능하게 유지

- **ImageService**
  - NIfTI 로드: nibabel.load → affine, spacing, data array 추출
  - 슬라이스 추출: axis(0=axial, 1=coronal, 2=sagittal) + index → 2D array
  - 볼륨 전달: 전체 3D numpy array를 bytes로 직렬화
  - orientation 통일: 모든 영상을 RAS+ 좌표계로 변환 (nibabel.as_closest_canonical)

- **ModelService**
  - nnUNet_results 디렉토리 재귀 스캔
  - Dataset, Trainer, Plans, Configuration 조합 파싱
  - dataset.json에서 labels 딕셔너리 추출 (클래스 이름 + 개수)
  - fold별 checkpoint 존재 여부 확인

- **InferenceService**
  - nnUNetPredictor 인스턴스 생성 및 GPU 로딩
  - 모델 캐싱: 동일 모델 재요청 시 재로드 방지 (LRU 방식, 최대 2개 모델)
  - inference 작업 큐: 동시에 1개만 실행 (asyncio.Queue)
  - 진행률 추적: nnUNet의 verbose 출력을 파싱하거나 파일 기반 progress 전달

- **SegmentService**
  - 세그멘테이션 결과 NIfTI 저장 (원본 affine/spacing 보존)
  - 편집된 세그멘테이션 업데이트 (부분 슬라이스 단위 수신 → 전체 볼륨에 반영)
  - 결과 파일 목록 관리

### 3. nnUNet Integration Layer
**역할**: nnUNetv2 라이브러리와의 직접 인터페이스

- `nnUNetPredictor` 초기화 시 설정:
  ```python
  predictor = nnUNetPredictor(
      tile_step_size=0.5,
      use_gaussian=True,
      use_mirroring=True,  # TTA (Test Time Augmentation)
      perform_everything_on_device=True,  # GPU에서 모든 처리
      device=torch.device('cuda', 0),
      verbose=False,
      verbose_preprocessing=False,
      allow_tqdm=False  # tqdm 비활성화, 자체 progress 사용
  )
  ```
- 입력 파일 준비: 업로드된 파일을 nnUNet 규칙에 맞게 임시 디렉토리에 심볼릭 링크
- 결과 후처리: nnUNet의 postprocessing.json이 있으면 자동 적용

---

## Frontend 상세 레이어 설계

### 1. 2D Slice Viewer (P0)
- **Cornerstone3D VolumeViewport (ORTHOGRAPHIC)** 3개를 동시에 렌더링
  - StackViewport가 아닌 VolumeViewport를 사용하는 이유:
    세 방향 크로스헤어 동기화와 세그멘테이션 오버레이가
    VolumeViewport에서 더 자연스럽게 동작하며, 3D 뷰포트와
    동일한 볼륨 데이터를 공유할 수 있다.
- 각 viewport는 axial, coronal, sagittal 방향
- **크로스헤어 동기화**: 한 viewport에서 클릭하면 world coordinate를 계산하여
  나머지 2개 viewport의 슬라이스 인덱스를 업데이트
- **윈도우/레벨 프리셋** (CT Hounsfield Unit 기준):
  | 프리셋 | Window Width | Window Level |
  |--------|-------------|-------------|
  | Abdomen | 400 | 40 |
  | Lung | 1500 | -600 |
  | Bone | 2000 | 400 |
  | Brain | 80 | 40 |
  | Liver | 150 | 60 |
  | Mediastinum | 350 | 50 |
  | Custom | 사용자 입력 | 사용자 입력 |
- **마우스 인터랙션 (2D 슬라이스 뷰)**:
  - 좌클릭 드래그: 윈도우/레벨 조절 (좌우=width, 상하=level)
  - 우클릭 드래그: 팬
  - 휠: 슬라이스 이동
  - Ctrl+휠: 줌

### 2. 3D Volume Viewer (P1)
- **Cornerstone3D VolumeViewport** 사용
- **볼륨 렌더링**: Ray casting 방식
- **Transfer Function 프리셋**: CT Bone, CT Soft Tissue, CT Lung 등
- **세그멘테이션 3D 표면**: 각 클래스를 고유 컬러의 3D mesh로 표시
- **마우스 인터랙션 (3D 뷰 — 2D와 다름에 주의)**:
  - 좌클릭 드래그: 3D 회전 (2D에서는 W/L이지만 3D에서는 회전)
  - 우클릭 드래그: 팬 (2D와 동일)
  - 휠: 줌 (2D에서는 슬라이스 이동이지만 3D에서는 줌)

### 3. Segmentation Overlay
- **컬러맵**: 각 세그멘테이션 클래스에 고유 색상 할당
  - 색상은 dataset.json의 labels 순서에 따라 자동 배정
  - 기본 팔레트: segmentation-overlay.md에 정의된 10색 커스텀 팔레트
    (Red, Blue, Green, Yellow, Cyan, Magenta, Orange, Purple, Lime, Pink)
  - 11개 이상 클래스는 HSV golden angle 기반으로 자동 생성
  - 사용자가 개별 클래스 색상 변경 가능 (P2)
- **투명도**: 전체 오버레이 투명도 슬라이더 (0~100%)
- **클래스별 표시/숨김**: 체크박스로 개별 클래스 on/off
- **레이블 패널**: 우측 사이드바에 클래스 이름 + 색상 + 체크박스 목록

### 4. Segmentation Editor (P1)
- **Cornerstone3D Tools** 기반:
  - `BrushTool`: 원형 브러시, 크기 조절 가능 (1~50px)
  - `EraserTool`: 브러시와 동일하지만 레이블을 0(background)으로 설정
- **활성 레이블 선택**: 레이블 패널에서 클릭하여 현재 브러시가 칠할 클래스 선택
- **Undo/Redo**: 최근 20개 편집 이력 유지 (메모리 기반)
- **편집 저장**: "Save" 버튼 클릭 시 수정된 세그멘테이션 전체를 Backend에 전송
- **편집은 2D 슬라이스 뷰에서만 가능** (3D 뷰에서는 편집 불가, 조회만)

---

## 데이터 흐름 상세

### 영상 업로드 → 뷰어 표시
```
1. [Frontend] 사용자가 .nii.gz 파일 선택
2. [Frontend] POST /api/images/upload (multipart/form-data)
3. [Backend]  nibabel.load → 유효성 검사 (NIfTI인지, 3D인지, CT인지)
4. [Backend]  as_closest_canonical → RAS+ 변환
5. [Backend]  uploads/{image_id}/ 에 파일 저장
6. [Backend]  응답: { image_id, metadata: { shape, spacing, affine, dtype, hu_range } }
7. [Frontend] GET /api/images/{image_id}/volume (전체 볼륨 바이너리)
8. [Frontend] ArrayBuffer → Cornerstone3D Volume으로 변환
9. [Frontend] 3개 VolumeViewport(ORTHOGRAPHIC)에 axial/coronal/sagittal 표시
```

### Inference 실행
```
1. [Frontend] GET /api/models/ → 사용 가능한 모델 목록 수신
2. [Frontend] 사용자가 Dataset/Config/Fold 선택
3. [Frontend] POST /api/inference/run { image_id, model_config }
4. [Backend]  작업 큐에 추가, 즉시 { job_id, status: "queued" } 응답
5. [Backend]  큐에서 꺼내서 nnUNetPredictor 실행
6. [Frontend] WebSocket /ws/inference/{job_id} 로 진행률 수신
7. [Backend]  완료 시 결과 NIfTI를 results/{image_id}/{result_id}.nii.gz 에 저장
   (result_id는 job_id와 별개의 UUID. job_id는 작업 추적용, result_id는 결과 식별용)
8. [Frontend] 완료 알림 수신 → GET /api/segments/{result_id}/volume
9. [Frontend] 세그멘테이션 볼륨을 오버레이로 표시
```

### 세그멘테이션 편집 → 저장
```
1. [Frontend] 사용자가 레이블 패널에서 편집할 클래스 선택
2. [Frontend] 브러시/지우개 도구로 2D 슬라이스에서 편집
3. [Frontend] 편집 내역이 Cornerstone3D segmentation state에 반영
4. [Frontend] "Save" 클릭 → 전체 세그멘테이션 볼륨을 ArrayBuffer로 직렬화
5. [Frontend] PUT /api/segments/{result_id} (application/octet-stream)
6. [Backend]  바이너리 수신 → numpy array 변환 → 원본 affine으로 NIfTI 저장
7. [Backend]  응답: { result_id, updated_at, path }
```

---

## 핵심 기술 결정 사항

### NIfTI → Frontend 전달 방식
- **결정**: Backend에서 numpy array를 raw bytes(application/octet-stream)로 전달
- **이유**: JSON으로 3D array를 보내면 크기가 3-10x 증가하고 파싱이 느림
- **헤더 정보**: HTTP 커스텀 헤더로 shape, dtype, spacing 전달
- **바이트 순서**: Little-endian, Float32 (CT HU 값 보존)

### 모델 캐싱 전략
- **결정**: LRU 캐시, 최대 2개 모델을 GPU에 유지
- **이유**: 모델 로딩에 10-30초 소요, 같은 모델 반복 사용이 잦음
- **메모리 관리**: 새 모델 로드 시 가장 오래된 모델 해제 (torch.cuda.empty_cache)
- **캐시 키**: (dataset_id, trainer, plans, configuration) 튜플

### Inference 동시성
- **결정**: 한 번에 1개 inference만 실행, 나머지는 큐에 대기
- **이유**: GPU VRAM 제한 (대부분의 연구용 서버는 단일 GPU)
- **큐 방식**: asyncio.Queue (MVP), Celery+Redis (P2에서 필요 시)

### 세그멘테이션 편집 동기화
- **결정**: 편집은 Frontend에서 실시간 반영, 저장은 명시적 "Save" 클릭 시만
- **이유**: 매 브러시 스트로크마다 Backend 통신하면 지연이 발생
- **Undo**: Frontend 메모리에서만 관리 (Backend는 최종 저장본만 관리)
