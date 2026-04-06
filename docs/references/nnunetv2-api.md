# nnUNetv2 Python API 참고 자료

## 이 문서의 목적
에이전트가 InferenceService를 구현할 때 참고해야 할
nnUNetv2의 핵심 API 사용법을 정리한다.

---

## nnUNetPredictor 기본 사용법

### 최소 코드 (파일 기반 inference)

```python
from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
import torch

# 1. Predictor 생성
predictor = nnUNetPredictor(
    tile_step_size=0.5,          # 타일 오버랩 비율 (0.5 = 50%)
    use_gaussian=True,           # 가우시안 중요도 가중치 사용
    use_mirroring=True,          # TTA (Test Time Augmentation)
    perform_everything_on_device=True,  # GPU에서 모든 처리
    device=torch.device('cuda', 0),
    verbose=False,
    verbose_preprocessing=False,
    allow_tqdm=False             # tqdm 비활성화 (우리가 자체 progress 사용)
)

# 2. 모델 초기화 (GPU에 로드)
predictor.initialize_from_trained_model_folder(
    model_training_output_dir='/path/to/nnUNet_results/Dataset001_Liver/nnUNetTrainer__nnUNetPlans__3d_fullres',
    use_folds=(0, 1, 2, 3, 4),     # 주의: tuple이어야 함, list 아님
    checkpoint_name='checkpoint_best.pth'
)

# 3. Inference 실행
predictor.predict_from_files(
    list_of_lists_or_source_folder='/path/to/input/',
    output_folder='/path/to/output/',
    save_probabilities=False,
    overwrite=True,
    num_processes_preprocessing=1,
    num_processes_segmentation_export=1
)
```

### 인메모리 inference (P2에서 검토)

```python
import nibabel as nib
import numpy as np

# NIfTI 로드
img = nib.load('case_0000.nii.gz')
data = img.get_fdata()  # shape: (x, y, z), dtype: float64

# properties 딕셔너리 준비
properties = {
    'sitk_stuff': {
        'spacing': img.header.get_zooms()[:3],
        'origin': img.affine[:3, 3].tolist(),
        'direction': img.affine[:3, :3].flatten().tolist(),
    },
    'spacing': list(img.header.get_zooms()[:3]),
}

# 인메모리 예측
# data shape: (channels, x, y, z) — 채널 차원 추가 필요
data_with_channel = data[np.newaxis, ...]  # (1, x, y, z)
result = predictor.predict_single_npy_array(
    input_image=data_with_channel,
    image_properties=properties,
    segmentation_previous_stage=None,
    output_file_truncated=None,   # None이면 파일 저장 안 함
    save_or_return_probabilities=False
)
# result: numpy array, shape (x, y, z), dtype int
```

---

## nnUNet_results 디렉토리 구조 상세

```
$nnUNet_results/
└── Dataset001_Liver/
    └── nnUNetTrainer__nnUNetPlans__3d_fullres/
        ├── fold_0/
        │   ├── checkpoint_best.pth      # 최적 성능 checkpoint
        │   ├── checkpoint_final.pth     # 마지막 epoch checkpoint
        │   ├── debug.json               # 학습 설정 상세
        │   ├── progress.png             # 학습 곡선 그래프
        │   └── training_log_*.txt       # 학습 로그
        ├── fold_1/
        ├── fold_2/
        ├── fold_3/
        ├── fold_4/
        ├── dataset.json                 # ★ 레이블 정보
        ├── plans.json                   # ★ 전처리/네트워크 설정
        ├── dataset_fingerprint.json     # 데이터셋 통계
        ├── postprocessing.json          # 후처리 설정 (선택)
        └── crossval_results_folds_0_1_2_3_4/
            └── summary.json             # 교차검증 결과
```

### dataset.json 핵심 필드

```json
{
    "channel_names": {
        "0": "CT"
    },
    "labels": {
        "background": 0,
        "liver": 1,
        "liver_tumor": 2,
        "portal_vein": 3,
        "hepatic_vein": 4
    },
    "numTraining": 131,
    "file_ending": ".nii.gz"
}
```

- `labels`: 세그멘테이션 클래스 이름 → ID 매핑. **우리 앱에서 이것만 사용**
- `channel_names`: 입력 모달리티. CT는 항상 `{"0": "CT"}`
- `file_ending`: 항상 `.nii.gz`

### plans.json 핵심 필드 (참고용)

```json
{
    "configurations": {
        "3d_fullres": {
            "patch_size": [128, 128, 128],
            "batch_size": 2,
            "UNet_class_name": "PlainConvUNet",
            "spacing": [0.8, 0.8, 0.8],
            "normalization_schemes": ["CTNormalization"],
            "n_seg_heads": 1
        }
    }
}
```

---

## 파일명 규칙

nnUNet은 입력 파일에 엄격한 이름 규칙을 요구한다:

```
{CASE_ID}_{MODALITY_ID}.nii.gz

예:
case_001_0000.nii.gz    # 모달리티 0 (CT)
case_001_0001.nii.gz    # 모달리티 1 (있는 경우)
```

- `CASE_ID`: 자유 문자열 (예: "case_001", "patient_abc")
- `MODALITY_ID`: 4자리 숫자, 0부터 시작 (CT 단일이면 항상 "0000")
- dataset.json의 `channel_names` 키와 매칭

**우리 앱에서의 처리**:
사용자가 `liver_ct_scan.nii.gz`를 업로드하면,
Backend에서 자동으로 `{image_id}_0000.nii.gz`로 심볼릭 링크를 생성한다.

---

## 자주 발생하는 에러와 해결

### RuntimeError: CUDA out of memory
**원인**: GPU VRAM 부족
**해결**: design-docs/gpu-memory-management.md의 OOM 대응 전략 참고
- use_mirroring=False로 재시도
- tile_step_size 증가로 재시도

### FileNotFoundError: checkpoint_best.pth
**원인**: 학습이 완료되지 않은 fold
**해결**: ModelService에서 checkpoint 존재 여부를 사전 확인

### ValueError: expected input to be 4D or 5D
**원인**: 입력 데이터 shape이 잘못됨
**해결**: (x, y, z) → (1, x, y, z)로 채널 차원 추가

### RuntimeError: input image and target have different shapes
**원인**: 입력 파일의 spacing이 plans.json과 너무 다른 경우
**해결**: nnUNet 전처리가 자동으로 resampling하므로 보통 발생하지 않음.
발생 시 입력 파일의 무결성 확인.

---

## 참고 자료 링크

- nnUNetv2 GitHub: https://github.com/MIC-DKFZ/nnUNet
- nnUNetv2 inference 문서: GitHub README의 "How to use nnU-Net" 섹션
- nnUNetPredictor 소스코드: `nnunetv2/inference/predict_from_raw_data.py`
