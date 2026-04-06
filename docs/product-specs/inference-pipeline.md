# nnUNet Inference Pipeline 스펙

## §1. 모델 목록 조회

### 개요
nnUNet_results 디렉토리를 스캔하여 사용 가능한 모델 조합
(Dataset / Trainer / Plans / Configuration / Fold)을 자동으로 탐지하고,
Frontend에 목록으로 제공한다. 사용자가 수동으로 모델을 등록할 필요가 없다.

### nnUNet_results 표준 디렉토리 구조
```
$nnUNet_results/
├── Dataset001_Liver/
│   └── nnUNetTrainer__nnUNetPlans__3d_fullres/
│       ├── fold_0/
│       │   ├── checkpoint_best.pth
│       │   └── checkpoint_final.pth
│       ├── fold_1/
│       ├── fold_2/
│       ├── fold_3/
│       ├── fold_4/
│       ├── dataset.json           ← 레이블 정보 (핵심)
│       ├── plans.json
│       ├── dataset_fingerprint.json
│       └── postprocessing.json    ← 후처리 설정 (있으면 적용)
├── Dataset002_Kidney/
│   ├── nnUNetTrainer__nnUNetPlans__2d/
│   └── nnUNetTrainer__nnUNetPlans__3d_fullres/
└── ...
```

### 디렉토리 파싱 규칙

#### Dataset 탐지
- `$nnUNet_results/` 하위 디렉토리 중 `Dataset{ID}_{Name}` 패턴 매칭
- 정규식: `^Dataset(\d{3,4})_(.+)$`
- ID와 Name 분리하여 저장

#### Trainer/Plans/Configuration 탐지
- Dataset 하위 디렉토리 중 `{Trainer}__{Plans}__{Configuration}` 패턴 매칭
- 정규식: `^(.+?)__(.+?)__(.+)$`
- 일반적인 값: Trainer=`nnUNetTrainer`, Plans=`nnUNetPlans`, Config=`2d`/`3d_fullres`/`3d_lowres`/`3d_cascade_fullres`

#### Fold 탐지
- Configuration 하위 디렉토리 중 `fold_{N}` 패턴 매칭
- 각 fold에 `checkpoint_best.pth` 또는 `checkpoint_final.pth`가 존재하는지 확인
- checkpoint가 없는 fold는 목록에서 제외 (학습 미완료)

#### Labels 추출
- `dataset.json`의 `"labels"` 딕셔너리에서 클래스 이름과 ID를 추출
- 예: `{"background": 0, "liver": 1, "tumor": 2, "vessel": 3}`
- 이 정보가 세그멘테이션 컬러맵과 레이블 패널의 유일한 소스

### 모델 목록 캐싱
- 앱 시작 시 한 번 전체 스캔 후 캐시
- `GET /api/models/refresh` 호출 시 재스캔
- 파일 시스템 변경 감지(watchdog)는 P2에서 검토

### API 엔드포인트

#### GET /api/models/
**Response (200)**:
```json
{
  "models": [
    {
      "dataset_id": "001",
      "dataset_name": "Liver",
      "full_dataset_name": "Dataset001_Liver",
      "configurations": [
        {
          "trainer": "nnUNetTrainer",
          "plans": "nnUNetPlans",
          "configuration": "3d_fullres",
          "available_folds": [0, 1, 2, 3, 4],
          "has_postprocessing": true,
          "labels": {
            "background": 0,
            "liver": 1,
            "liver_tumor": 2,
            "portal_vein": 3,
            "hepatic_vein": 4
          },
          "num_classes": 5,
          "checkpoint_type": "best"
        }
      ]
    },
    {
      "dataset_id": "002",
      "dataset_name": "Kidney",
      "full_dataset_name": "Dataset002_Kidney",
      "configurations": [
        {
          "trainer": "nnUNetTrainer",
          "plans": "nnUNetPlans",
          "configuration": "2d",
          "available_folds": [0, 1, 2],
          "has_postprocessing": false,
          "labels": {
            "background": 0,
            "kidney": 1,
            "kidney_tumor": 2,
            "kidney_cyst": 3
          },
          "num_classes": 4,
          "checkpoint_type": "best"
        },
        {
          "trainer": "nnUNetTrainer",
          "plans": "nnUNetPlans",
          "configuration": "3d_fullres",
          "available_folds": [0, 1, 2, 3, 4],
          "has_postprocessing": true,
          "labels": {
            "background": 0,
            "kidney": 1,
            "kidney_tumor": 2,
            "kidney_cyst": 3
          },
          "num_classes": 4,
          "checkpoint_type": "best"
        }
      ]
    }
  ],
  "nnunet_results_path": "/data/nnUNet_results",
  "scanned_at": "2025-01-15T10:30:00Z"
}
```

#### GET /api/models/refresh
**Response (200)**:
```json
{
  "message": "모델 목록을 다시 스캔했습니다.",
  "model_count": 5,
  "scanned_at": "2025-01-15T10:35:00Z"
}
```

### 에러 처리
| 상황 | 처리 방식 |
|------|----------|
| nnUNet_results 환경변수 미설정 | 앱 시작 실패 + 로그에 설정 안내 |
| nnUNet_results 경로가 존재하지 않음 | 앱 시작 실패 + 경로 확인 안내 |
| 경로 존재하지만 비어있음 | 빈 목록 반환 + Frontend에서 "모델 없음" 안내 |
| dataset.json 파싱 실패 | 해당 모델만 건너뛰기 + 경고 로그 |
| checkpoint 파일 누락 | 해당 fold만 제외 + 경고 로그 |

### Frontend UI: 모델 선택

#### 선택 흐름
```
1. 상단 툴바의 [Model ▼] 드롭다운 클릭
2. 1단계: Dataset 선택 (예: "001 - Liver")
3. 2단계: Configuration 선택 (예: "3d_fullres")
   → Trainer와 Plans가 하나뿐이면 자동 선택, 여럿이면 추가 드롭다운
4. 3단계: Fold 선택 (기본: "All folds (ensemble)")
   → 개별 fold 선택도 가능 (빠른 추론용)
5. 선택 완료 → [Run Inference] 버튼 활성화
```

#### 모델 정보 표시
선택된 모델 옆에 작은 정보 아이콘(ℹ️) → 클릭 시 팝오버:
- 클래스 수: 5
- 클래스 목록: background, liver, tumor, ...
- Configuration: 3d_fullres
- 사용 가능한 Fold: 0, 1, 2, 3, 4
- 후처리 적용 여부: Yes

---

## §2. Inference 실행

### 개요
사용자가 모델을 선택하고 "Run Inference" 버튼을 클릭하면,
Backend에서 nnUNetPredictor를 통해 세그멘테이션을 실행한다.
실행 중 진행률을 실시간으로 Frontend에 전달한다.

### 사용자 시나리오
```
1. 영상이 로드되고 모델이 선택된 상태
2. [Run Inference] 버튼 클릭
3. 버튼이 비활성화되고 "Running..." 텍스트로 변경
4. 프로그레스 바가 나타남 (0% → 100%)
5. 단계별 상태 텍스트:
   - "모델 로딩 중..." (첫 실행 시, 캐시되면 건너뜀)
   - "전처리 중..."
   - "추론 중... (Fold 0/5)"
   - "후처리 중..."
   - "완료!"
6. 완료 시 세그멘테이션 오버레이가 자동으로 표시
7. [Run Inference] 버튼 다시 활성화
```

### Backend Inference 처리 흐름

#### 1단계: 요청 수신 및 큐잉
```python
# POST /api/inference/run 수신
# 1. 이미 실행 중인 inference가 있으면 큐에 추가
# 2. 큐가 비어있으면 즉시 실행
# 3. 즉시 job_id 반환 (비동기 실행)
```

#### 2단계: 입력 파일 준비
```python
# nnUNet은 특정 파일명 규칙을 요구한다
# 원본: uploads/{image_id}/canonical.nii.gz
# nnUNet 입력: temp/{job_id}/case_0000_0000.nii.gz
# → 심볼릭 링크로 생성 (복사 방지)
#
# 파일명 규칙: {CASE_ID}_{MODALITY_ID}.nii.gz
# CT 단일 모달리티이므로 modality_id는 항상 0000
```

#### 3단계: nnUNetPredictor 초기화/캐시 확인
```python
# 캐시 키: (dataset_id, trainer, plans, configuration)
# 캐시에 있으면 → 기존 predictor 재사용 (10-30초 절약)
# 캐시에 없으면 → 새로 생성:
#   predictor = nnUNetPredictor(
#       tile_step_size=0.5,
#       use_gaussian=True,
#       use_mirroring=True,     # TTA 활성화 (정확도↑, 속도↓)
#       perform_everything_on_device=True,  # GPU에서 모든 처리
#       device=torch.device('cuda', 0),
#       verbose=False,
#       verbose_preprocessing=False,
#       allow_tqdm=False
#   )
#   predictor.initialize_from_trained_model_folder(
#       model_training_output_dir=model_path,
#       use_folds=selected_folds,        # (0,1,2,3,4) 또는 단일 fold
#       checkpoint_name='checkpoint_best.pth'
#   )
```

#### 4단계: Inference 실행
```python
# predictor.predict_from_files(
#     list_of_lists_or_source_folder=input_dir,
#     output_folder=output_dir,
#     save_probabilities=False,
#     overwrite=True,
#     num_processes_preprocessing=1,
#     num_processes_segmentation_export=1
# )
#
# 또는 인메모리 방식:
# predictor.predict_single_npy_array(
#     input_image=numpy_array,
#     image_properties=properties_dict,
#     ...
# )
```

#### 5단계: 후처리
```python
# postprocessing.json이 있으면 nnUNet 자체 후처리 적용
# 예: 작은 연결 컴포넌트 제거, 특정 클래스 간 overlap 해결
```

#### 6단계: 결과 저장
```python
# 결과 NIfTI를 results/{image_id}/{result_id}.nii.gz 에 저장
# 메타데이터: results/{image_id}/{result_id}_meta.json
# {
#   "image_id": "...",
#   "model": { "dataset": "...", "config": "...", ... },
#   "created_at": "...",
#   "labels": { "background": 0, "liver": 1, ... },
#   "inference_time_seconds": 45.2
# }
```

### 진행률 전달: WebSocket

#### WebSocket 엔드포인트
```
WS /ws/inference/{job_id}
```

#### 메시지 포맷 (Backend → Frontend)
```json
{
  "job_id": "xyz-123",
  "status": "running",
  "progress": 35,
  "stage": "inference",
  "stage_detail": "Fold 2/5",
  "elapsed_seconds": 12.5,
  "estimated_remaining_seconds": 23.0
}
```

#### 상태 값
| status | progress | 설명 |
|--------|----------|------|
| queued | 0 | 큐에 대기 중 (다른 inference 실행 중) |
| loading_model | 5 | 모델을 GPU에 로딩 중 |
| preprocessing | 15 | nnUNet 전처리 중 |
| inference | 20-85 | 추론 실행 중 (fold별 진행) |
| postprocessing | 90 | 후처리 적용 중 |
| saving | 95 | 결과 NIfTI 저장 중 |
| completed | 100 | 완료 |
| failed | -1 | 실패 |

#### 완료 메시지
```json
{
  "job_id": "xyz-123",
  "status": "completed",
  "progress": 100,
  "result_id": "result-abc-456",
  "inference_time_seconds": 45.2,
  "labels": {
    "background": 0,
    "liver": 1,
    "liver_tumor": 2
  }
}
```

#### 실패 메시지
```json
{
  "job_id": "xyz-123",
  "status": "failed",
  "progress": -1,
  "error": "GPU_OUT_OF_MEMORY",
  "message": "GPU 메모리가 부족합니다. 볼륨 크기를 줄이거나 다른 모델을 시도해주세요."
}
```

### GPU 관리 상세

#### 모델 캐싱 정책
- **캐시 크기**: 최대 2개 모델 (GPU VRAM 기준)
- **교체 정책**: LRU (Least Recently Used)
- **캐시 키**: (dataset_id, trainer, plans, configuration) 튜플
  - fold가 달라도 같은 모델이면 재사용 가능 (predictor.initialize에서 fold만 변경)
- **캐시 상태 API**: GET /api/inference/cache → 현재 캐시된 모델 목록

#### 메모리 해제
```python
# 모델 교체 시:
# 1. 기존 predictor의 network를 CPU로 이동
# 2. torch.cuda.empty_cache() 호출
# 3. gc.collect() 호출
# 4. 새 모델 로딩
```

#### 동시성 제어
- **정책**: 동시에 1개 inference만 실행
- **구현**: asyncio.Queue(maxsize=1) + 워커 태스크 1개
- **큐 대기**: 최대 5개 작업 대기 가능, 초과 시 INFERENCE_QUEUE_FULL(429) 반환
- **취소**: DELETE /api/inference/{job_id} → 큐에서 제거 (실행 중이면 취소 불가)

### API 엔드포인트

#### POST /api/inference/run
**Request**:
```json
{
  "image_id": "a1b2c3d4-...",
  "dataset_id": "001",
  "dataset_name": "Liver",
  "trainer": "nnUNetTrainer",
  "plans": "nnUNetPlans",
  "configuration": "3d_fullres",
  "folds": [0, 1, 2, 3, 4],
  "use_mirroring": true,
  "checkpoint": "best"
}
```

**Response (202 Accepted)**:
```json
{
  "job_id": "job-xyz-789",
  "status": "queued",
  "queue_position": 0,
  "websocket_url": "/ws/inference/job-xyz-789"
}
```

**에러**:
- 404: IMAGE_NOT_FOUND, MODEL_NOT_FOUND
- 409: INFERENCE_ALREADY_RUNNING (같은 image_id로 이미 실행 중)
- 429: INFERENCE_QUEUE_FULL

#### GET /api/inference/{job_id}/status
**Response (200)**:
```json
{
  "job_id": "job-xyz-789",
  "status": "running",
  "progress": 55,
  "stage": "inference",
  "stage_detail": "Fold 3/5",
  "elapsed_seconds": 25.0,
  "estimated_remaining_seconds": 20.0,
  "image_id": "a1b2c3d4-...",
  "model": {
    "dataset": "Dataset001_Liver",
    "configuration": "3d_fullres"
  }
}
```

#### DELETE /api/inference/{job_id}
**Response (200)**: 큐에서 제거됨
**Response (409)**: 이미 실행 중이라 취소 불가

#### GET /api/inference/cache
**Response (200)**:
```json
{
  "cached_models": [
    {
      "cache_key": "001_nnUNetTrainer_nnUNetPlans_3d_fullres",
      "dataset": "Dataset001_Liver",
      "configuration": "3d_fullres",
      "loaded_at": "2025-01-15T10:30:00Z",
      "last_used_at": "2025-01-15T10:35:00Z",
      "gpu_memory_mb": 2048
    }
  ],
  "gpu_total_mb": 24576,
  "gpu_used_mb": 4096,
  "gpu_free_mb": 20480
}
```

---

## §3. Inference 히스토리 (P2)

### 개요
이전에 실행한 inference 결과 목록을 조회하고,
과거 결과를 다시 불러올 수 있다.

### 히스토리 목록
- 영상별로 실행된 모든 inference 결과를 시간순 표시
- 각 항목에 표시: 모델명, 실행 시간, 클래스 수, 날짜
- 클릭 시 해당 세그멘테이션 결과를 오버레이로 로드

### API 엔드포인트

#### GET /api/inference/history?image_id={image_id}
**Response (200)**:
```json
{
  "results": [
    {
      "result_id": "result-abc-456",
      "job_id": "job-xyz-789",
      "image_id": "a1b2c3d4-...",
      "model": {
        "dataset": "Dataset001_Liver",
        "configuration": "3d_fullres",
        "folds": [0, 1, 2, 3, 4]
      },
      "labels": { "background": 0, "liver": 1, "liver_tumor": 2 },
      "inference_time_seconds": 45.2,
      "created_at": "2025-01-15T10:35:00Z",
      "edited": false
    }
  ]
}
```
