# 세그멘테이션 오버레이 스펙

## §1. 오버레이 표시

### 개요
nnUNet inference 결과(정수 레이블 볼륨)를 원본 CT 영상 위에
반투명 컬러 오버레이로 표시한다. 각 정수 값은 하나의 클래스를 의미하며,
dataset.json의 labels 매핑에 따라 이름과 색상을 부여한다.

### 세그멘테이션 데이터 구조
- **형태**: 원본 CT와 동일한 shape의 3D numpy array
- **데이터 타입**: uint8 (클래스 수 < 256) 또는 uint16
- **값의 의미**: 각 복셀의 값 = 클래스 ID
  - 0: background (표시하지 않음)
  - 1~N: 각 장기/병변 클래스

### 오버레이 렌더링 규칙
1. background (값=0)인 복셀은 **투명**으로 처리 (오버레이하지 않음)
2. 나머지 클래스는 해당 색상으로 **반투명** 오버레이
3. 오버레이와 원본 CT는 정확히 같은 좌표에 정렬 (affine 일치)
4. 윈도우/레벨 변경은 CT 영상에만 적용, 오버레이 색상에는 영향 없음

### 기본 컬러 팔레트
클래스 ID 순서대로 아래 색상을 자동 배정한다.
background(0)는 항상 건너뛴다.

| 순서 | 색상 이름 | RGB | 용도 예시 |
|------|----------|-----|----------|
| 1 | Red | (255, 0, 0) | 첫 번째 클래스 |
| 2 | Blue | (0, 0, 255) | 두 번째 클래스 |
| 3 | Green | (0, 255, 0) | 세 번째 클래스 |
| 4 | Yellow | (255, 255, 0) | 네 번째 클래스 |
| 5 | Cyan | (0, 255, 255) | 다섯 번째 클래스 |
| 6 | Magenta | (255, 0, 255) | 여섯 번째 클래스 |
| 7 | Orange | (255, 165, 0) | 일곱 번째 클래스 |
| 8 | Purple | (128, 0, 255) | 여덟 번째 클래스 |
| 9 | Lime | (128, 255, 0) | 아홉 번째 클래스 |
| 10 | Pink | (255, 128, 128) | 열 번째 클래스 |
| 11+ | 자동 생성 | HSV 균등 분할 | 추가 클래스 |

11개 이상 클래스가 있으면 HSV 색공간에서 Hue를 균등 분할하여 자동 생성한다.
생성 공식: `H = (class_id * 137.508) % 360, S = 0.8, V = 0.9`
(golden angle 기반으로 인접 클래스 간 색상 차이 최대화)

### 투명도 조절

#### 전체 투명도 슬라이더
- **위치**: 레이블 패널 상단
- **범위**: 0% (완전 투명, CT만 보임) ~ 100% (완전 불투명, CT 안 보임)
- **기본값**: 50%
- **적용 방식**: Cornerstone3D segmentation representation의 global alpha

#### 클래스별 투명도 (P2)
- 각 클래스 항목 옆에 개별 투명도 슬라이더
- 기본값: 전체 투명도를 따름
- 개별 설정 시 전체 슬라이더와 독립

### Cornerstone3D 구현 가이드
```
1. SegmentationDisplayTool 활성화
2. segmentationId를 생성하고 labelmap 데이터를 등록
3. segmentation representation을 각 viewport에 추가
4. colorLUT에 위 컬러 팔레트를 설정
5. global config에서 renderOutline=true, outlineWidth=1 설정
   (세그멘테이션 경계선 표시)
```

---

## §2. 클래스별 표시/숨김

### 개요
레이블 패널에서 각 세그멘테이션 클래스를 개별적으로
표시하거나 숨길 수 있다. 특정 장기만 집중적으로 보고 싶을 때 사용.

### 레이블 패널 UI

#### 패널 위치
- 우측 사이드바의 상단 영역
- 접기/펼치기 가능 (▼ 토글)

#### 각 클래스 항목 구성
```
┌────────────────────────────────────────┐
│ [✓] 🟥 Liver                    80%   │  ← 체크박스 + 색상 + 이름 + 복셀비율
│ [✓] 🟦 Liver Tumor              3%    │
│ [✓] 🟩 Portal Vein             12%    │
│ [ ] 🟨 Hepatic Vein             5%    │  ← 체크 해제 = 숨김
│                                       │
│ [전체 투명도] ████████░░ 50%          │
│ [전체 표시] [전체 숨기기]              │
└────────────────────────────────────────┘
```

#### 표시되는 정보
| 요소 | 설명 |
|------|------|
| 체크박스 | 표시/숨김 토글 (기본: 모두 선택) |
| 색상 사각형 | 해당 클래스의 오버레이 색상 (클릭 시 색상 변경 피커) |
| 클래스 이름 | dataset.json labels에서 가져온 이름 |
| 복셀 비율 | 해당 클래스가 차지하는 비율 (%) |

#### 인터랙션
- **체크박스 클릭**: 해당 클래스 표시/숨김 즉시 반영
- **색상 사각형 클릭**: 색상 피커 팝업 → 색상 변경 (P2)
- **클래스 이름 클릭**: 브러시 편집 시 활성 레이블로 선택 (§ segmentation-editor)
- **[전체 표시] 버튼**: 모든 클래스 체크박스 ON
- **[전체 숨기기] 버튼**: 모든 클래스 체크박스 OFF
- **background(0)**: 패널에 표시하지 않음

#### 복셀 비율 계산
```python
# Backend 또는 Frontend에서 계산
total_voxels = np.prod(segmentation.shape)
for class_id in range(1, num_classes):
    count = np.sum(segmentation == class_id)
    ratio = count / total_voxels * 100
    # 0.01% 미만이면 "<0.01%"로 표시
```

---

## §3. 세그멘테이션 3D 표면 렌더링 (P1)

### 개요
3D 뷰포트에서 각 세그멘테이션 클래스를 3D 표면(mesh)으로 렌더링한다.
레이블 패널의 표시/숨김 설정이 3D에도 동일하게 적용된다.

### 렌더링 방식
1. **Mesh 생성**: 각 클래스의 바이너리 마스크에 Marching Cubes 알고리즘 적용
2. **스무딩**: Laplacian smoothing (iterations=3) 적용하여 계단 현상 제거
3. **Decimation**: 폴리곤 수를 클래스당 최대 50,000 triangles로 제한
4. **색상**: 2D 오버레이와 동일한 컬러 사용
5. **투명도**: 기본 0.7 (약간 반투명), 개별 조절 가능 (P2)

### 성능 최적화
- Mesh 생성은 **Backend에서 수행**하고 결과를 Frontend에 전달
- 전달 포맷: vertices + faces (binary)
- 볼륨이 256^3 이상이면 2x 다운샘플링 후 mesh 생성
- mesh 생성은 비동기로 수행 (inference 완료 후 백그라운드)

### API 엔드포인트

#### GET /api/segments/{result_id}/mesh?class_id=1
**Response Headers**:
```
Content-Type: application/octet-stream
X-Mesh-Vertices-Count: 15234
X-Mesh-Faces-Count: 30456
X-Mesh-Format: float32-vertices,uint32-faces
```
**Response Body**:
```
[vertices: float32 × 3 × num_vertices][faces: uint32 × 3 × num_faces]
```

#### GET /api/segments/{result_id}/mesh/all
모든 클래스의 mesh를 한 번에 반환 (JSON wrapper):
```json
{
  "meshes": {
    "1": { "url": "/api/segments/{result_id}/mesh?class_id=1", "vertex_count": 15234 },
    "2": { "url": "/api/segments/{result_id}/mesh?class_id=2", "vertex_count": 8901 }
  }
}
```

---

## §4. 세그멘테이션 결과 다운로드 (P2)

### 개요
세그멘테이션 결과(편집 전 또는 편집 후)를 NIfTI 파일로 다운로드한다.

### 다운로드 옵션
| 옵션 | 설명 |
|------|------|
| 전체 레이블맵 | 모든 클래스가 포함된 단일 NIfTI (정수 레이블) |
| 개별 클래스 바이너리 | 선택한 클래스만 0/1 바이너리 마스크 NIfTI |
| 원본 + 오버레이 스크린샷 | 현재 뷰의 PNG 스크린샷 (P2) |

### API 엔드포인트

#### GET /api/segments/{result_id}/download
**Query Parameters**:
| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| format | string | "nifti" | "nifti" 만 지원 (추후 확장 가능) |
| class_id | int | null | 지정 시 해당 클래스만 바이너리 마스크로 |

**Response**: .nii.gz 파일 다운로드
```
Content-Type: application/gzip
Content-Disposition: attachment; filename="segmentation_result_abc456.nii.gz"
```

### 다운로드 파일 규칙
- **affine**: 원본 CT의 affine과 동일해야 함
- **spacing**: 원본 CT의 spacing과 동일해야 함
- **dtype**: uint8 (클래스 < 256) 또는 uint16
- **파일명**: `{original_filename}_seg_{model_name}_{timestamp}.nii.gz`

---

## 세그멘테이션 볼륨 API (공통)

### GET /api/segments/{result_id}/volume
세그멘테이션 전체 볼륨을 바이너리로 반환 (Frontend 로딩용).

**Response Headers**:
```
Content-Type: application/octet-stream
X-Seg-Shape: 512,512,128
X-Seg-Dtype: uint8
X-Seg-Num-Classes: 5
X-Seg-Labels: background:0,liver:1,tumor:2,vessel:3,hepatic_vein:4
```
**Response Body**: Raw bytes (uint8, C-contiguous)

### GET /api/segments/{result_id}/metadata
```json
{
  "result_id": "result-abc-456",
  "image_id": "a1b2c3d4-...",
  "shape": [512, 512, 128],
  "num_classes": 5,
  "labels": {
    "background": 0,
    "liver": 1,
    "liver_tumor": 2,
    "portal_vein": 3,
    "hepatic_vein": 4
  },
  "voxel_counts": {
    "0": 28311552,
    "1": 4200000,
    "2": 150000,
    "3": 850000,
    "4": 106000
  },
  "model": {
    "dataset": "Dataset001_Liver",
    "configuration": "3d_fullres"
  },
  "created_at": "2025-01-15T10:35:00Z",
  "edited": false,
  "edited_at": null
}
```
