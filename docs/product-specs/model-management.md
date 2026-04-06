# 모델 관리 스펙 (P2)

## §1. 모델 메모/태그

### 개요
연구실 내에서 여러 nnUNet 모델을 운용할 때,
각 모델의 성능이나 특성을 메모로 기록해둘 수 있다.
nnUNet_results 자체는 읽기 전용이므로, 메모는 별도 JSON 파일로 관리한다.

### 메모 저장 위치
```
project-root/
└── model_notes/
    └── Dataset001_Liver__nnUNetTrainer__nnUNetPlans__3d_fullres.json
```

### 메모 포맷
```json
{
  "dataset": "Dataset001_Liver",
  "configuration": "3d_fullres",
  "notes": "5-fold ensemble Dice 0.95. 작은 종양(< 1cm)에서 성능 저하.",
  "tags": ["production", "liver", "high-accuracy"],
  "created_at": "2025-01-10T09:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z",
  "author": "홍팀장"
}
```

### API 엔드포인트

#### GET /api/models/{dataset_id}/{configuration}/notes
#### PUT /api/models/{dataset_id}/{configuration}/notes
**Request**:
```json
{
  "notes": "5-fold ensemble Dice 0.95. 작은 종양(< 1cm)에서 성능 저하.",
  "tags": ["production", "liver", "high-accuracy"],
  "author": "홍팀장"
}
```

### UI
- 모델 선택 드롭다운에서 ℹ️ 아이콘 클릭 시 메모 확인/편집
- 태그가 있는 모델은 목록에서 태그 뱃지 표시
- "production" 태그가 있으면 모델명 옆에 ★ 표시
