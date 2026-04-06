# 영상 업로드 + 시각화 스펙

## §1. NIfTI 파일 업로드

### 개요
사용자가 브라우저에서 NIfTI(.nii, .nii.gz) 파일을 업로드하면,
Backend가 파일을 검증하고 저장한 뒤, 메타데이터를 반환한다.

### 사용자 시나리오
```
1. 사용자가 앱 메인 페이지에 접속한다
2. 화면 중앙 또는 상단에 "Upload NIfTI" 버튼이 있다
3. 버튼 클릭 → OS 파일 선택 다이얼로그 열림
4. .nii 또는 .nii.gz 파일을 선택한다
5. 업로드 진행률 바가 표시된다 (대용량 파일 고려)
6. 업로드 완료 → 자동으로 2D 슬라이스 뷰어에 영상 표시
7. 좌측 또는 하단에 메타데이터 패널 표시
```

### 지원 포맷
| 포맷 | 확장자 | 필수 여부 |
|------|--------|----------|
| NIfTI-1 | .nii | 필수 |
| NIfTI-1 (gzip) | .nii.gz | 필수 |
| NIfTI-2 | .nii | 선택 (P2) |

### 파일 검증 규칙 (Backend)
업로드된 파일에 대해 아래 순서대로 검증한다. 실패 시 즉시 에러 반환.

| 순서 | 검증 항목 | 에러 코드 | 설명 |
|------|----------|----------|------|
| 1 | 확장자 확인 | INVALID_NIFTI_FORMAT | .nii 또는 .nii.gz만 허용 |
| 2 | nibabel.load 성공 | INVALID_NIFTI_FORMAT | nibabel이 파싱할 수 없으면 거부 |
| 3 | 차원 확인 | NOT_3D_VOLUME | ndim == 3 이어야 함 (4D는 거부) |
| 4 | 파일 크기 | FILE_TOO_LARGE | 기본 500MB, 환경변수로 조정 가능 |
| 5 | 데이터 타입 | (경고만) | float16 이하이면 정밀도 경고 |

### 파일 저장 규칙
```
uploads/
  {image_id}/
    original.nii.gz          # 원본 파일 (항상 gzip으로 재저장)
    canonical.nii.gz          # RAS+ 변환된 버전 (뷰어에서 사용)
    metadata.json             # 메타데이터 캐시
```
- `image_id`: UUID v4 (예: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`)
- 원본 파일은 반드시 보존한다 (canonical은 별도 생성)
- RAS+ 변환: `nibabel.as_closest_canonical(img)` 적용

### 메타데이터 표시 항목
Frontend의 메타데이터 패널에 아래 정보를 표시한다:

| 항목 | 예시 | 설명 |
|------|------|------|
| 파일명 | liver_ct_001.nii.gz | 원본 파일명 |
| Shape | (512, 512, 128) | 볼륨 차원 (x, y, z) |
| Spacing | (0.75, 0.75, 2.5) mm | 복셀 크기 |
| Orientation | RAS+ | 원본 orientation (변환 전) |
| Data Type | float32 | numpy dtype |
| HU Range | [-1024, 3071] | 최솟값, 최댓값 |
| 파일 크기 | 45.2 MB | 원본 파일 크기 |
| Affine | 4x4 행렬 | 접기/펼치기 UI로 표시 |

### API 엔드포인트

#### POST /api/images/upload
**Request**:
```
Content-Type: multipart/form-data
Body: file=@liver_ct_001.nii.gz
```

**Response (200)**:
```json
{
  "image_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "filename": "liver_ct_001.nii.gz",
  "metadata": {
    "shape": [512, 512, 128],
    "spacing": [0.75, 0.75, 2.5],
    "orientation": "RAS",
    "dtype": "float32",
    "hu_range": [-1024, 3071],
    "file_size_bytes": 47413248,
    "affine": [[0.75, 0, 0, -192], [0, 0.75, 0, -192], [0, 0, 2.5, -160], [0, 0, 0, 1]]
  }
}
```

**에러 응답**:
- 400: INVALID_NIFTI_FORMAT, NOT_3D_VOLUME
- 413: FILE_TOO_LARGE

---

## §2. 2D 슬라이스 뷰어

### 개요
업로드된 CT 영상을 Axial, Coronal, Sagittal 세 방향의 2D 슬라이스로
동시에 표시한다. 세 뷰포트는 서로 동기화된다.

### 화면 레이아웃
```
┌─────────────────────────────────────────────────────┐
│ [Upload] [Model ▼] [Run Inference]    [Settings ⚙]  │ ← 상단 툴바
├──────────────┬──────────────┬───────────────────────┤
│              │              │                       │
│   Axial      │   Coronal    │   레이블 패널         │
│   (횡단면)    │   (관상면)    │   ├ 🟥 Liver         │
│              │              │   ├ 🟦 Kidney         │
│              │              │   ├ 🟩 Spleen         │
│              │              │   └ ...               │
├──────────────┼──────────────┤                       │
│              │              │   메타데이터 패널      │
│   Sagittal   │   3D View    │   ├ Shape: ...        │
│   (시상면)    │   (P1)       │   ├ Spacing: ...     │
│              │              │   └ HU Range: ...     │
│              │              │                       │
└──────────────┴──────────────┴───────────────────────┘
```
- **기본 레이아웃**: 2x2 그리드 (Axial, Coronal, Sagittal, 3D/빈칸)
- **우측 사이드바**: 레이블 패널 + 메타데이터 패널
- **반응형**: 최소 너비 1280px, 그 이하에서는 단일 뷰포트 + 탭 전환

### 슬라이스 뷰포트 상세

#### 각 뷰포트에 표시되는 정보
- **영상 슬라이스**: CT HU 값을 윈도우/레벨에 따라 그레이스케일로 표시
- **슬라이스 번호**: 좌측 상단에 "Slice: 64/128" 형태
- **방향 라벨**: 뷰포트 가장자리에 방향 표시
  - Axial: 상=A(Anterior), 하=P(Posterior), 좌=R(Right), 우=L(Left)
  - Coronal: 상=S(Superior), 하=I(Inferior), 좌=R(Right), 우=L(Left)
  - Sagittal: 상=S(Superior), 하=I(Inferior), 좌=A(Anterior), 우=P(Posterior)
- **크로스헤어**: 얇은 점선으로 현재 다른 두 뷰포트의 슬라이스 위치 표시
- **스케일바**: 우측 하단에 물리적 크기 스케일바 (spacing 기반)

#### 슬라이스 이동
- **마우스 휠**: 1칸씩 슬라이스 이동
- **Shift + 마우스 휠**: 10칸씩 빠른 이동
- **슬라이더**: 각 뷰포트 하단에 수평 슬라이더 (0 ~ max_slice)
- **직접 입력**: 슬라이스 번호 클릭 → 숫자 입력으로 점프

#### 크로스헤어 동기화
세 뷰포트는 하나의 world coordinate (x, y, z)를 공유한다.
- Axial 뷰포트에서 클릭 → (x, y) 결정 → Coronal의 x위치, Sagittal의 y위치 업데이트
- Coronal 뷰포트에서 클릭 → (x, z) 결정 → Axial의 x위치, Sagittal의 z위치 업데이트
- Sagittal 뷰포트에서 클릭 → (y, z) 결정 → Axial의 y위치, Coronal의 z위치 업데이트

#### 줌 & 팬
- **Ctrl + 마우스 휠**: 줌 인/아웃 (중심점은 마우스 커서 위치)
- **우클릭 드래그**: 팬 (영상 이동)
- **더블 클릭**: 줌/팬 리셋 (Fit to viewport)
- **줌 범위**: 0.5x ~ 10x
- **줌 동기화**: 세 뷰포트의 줌 레벨은 독립적 (동기화하지 않음)

### 영상 데이터 로딩 방식

#### 전체 볼륨 로딩 (기본)
```
Frontend → GET /api/images/{image_id}/volume
Backend  → canonical.nii.gz의 전체 3D array를 Float32 raw bytes로 반환
Frontend → ArrayBuffer → Float32Array → Cornerstone3D Volume 생성
```

#### 대용량 볼륨 대응 (shape의 곱 > 256^3 일 때)
```
Frontend → GET /api/images/{image_id}/volume?downsample=2
Backend  → 각 축을 2배 다운샘플링한 볼륨 반환
Frontend → 다운샘플된 볼륨으로 먼저 표시
Frontend → 백그라운드에서 원본 해상도 로딩 (progressive loading)
```

### API 엔드포인트

#### GET /api/images/{image_id}/volume
**Response Headers**:
```
Content-Type: application/octet-stream
X-Image-Shape: 512,512,128
X-Image-Dtype: float32
X-Image-Spacing: 0.75,0.75,2.5
X-Image-ByteOrder: little
```
**Response Body**: Raw bytes (Float32, little-endian, C-contiguous order)

**바이트 크기 계산**: shape[0] × shape[1] × shape[2] × 4 (float32)
예: 512 × 512 × 128 × 4 = 134,217,728 bytes (128MB)

#### GET /api/images/{image_id}/slice?axis=axial&index=64
**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| axis | string | 예 | "axial", "coronal", "sagittal" |
| index | int | 예 | 0-based 슬라이스 인덱스 |

**Response Headers**:
```
Content-Type: application/octet-stream
X-Slice-Shape: 512,512
X-Slice-Dtype: float32
```
**Response Body**: Raw bytes (2D array, Float32)

**에러**:
- 404: IMAGE_NOT_FOUND
- 400: index가 범위 밖

---

## §3. 윈도우/레벨 조절

### 개요
CT 영상은 Hounsfield Unit(HU) 값 범위가 넓어서 (-1024 ~ 3071+),
적절한 윈도우/레벨 설정 없이는 의미 있는 영상을 볼 수 없다.
윈도우/레벨은 **표시 단계에서만** 적용되며, 원본 HU 값은 절대 변경하지 않는다.

### 윈도우/레벨이란 (비전문가를 위한 설명)
- **Window Level (Center)**: "어떤 밝기를 중심으로 볼 것인가" — HU 40이면 물/연조직 중심
- **Window Width**: "얼마나 넓은 범위를 볼 것인가" — 좁으면 대비가 강함, 넓으면 부드러움
- **표시 공식**: pixel_value가 [level - width/2, level + width/2] 범위 밖이면 검정/흰색

### CT 프리셋
| 프리셋 | Window Width | Window Level | 용도 |
|--------|-------------|-------------|------|
| **Abdomen** (기본값) | 400 | 40 | 복부 장기 (간, 신장, 비장) |
| **Lung** | 1500 | -600 | 폐 실질 |
| **Bone** | 2000 | 400 | 뼈, 석회화 |
| **Brain** | 80 | 40 | 뇌 연조직 |
| **Liver** | 150 | 60 | 간 세부 (간암 등) |
| **Mediastinum** | 350 | 50 | 종격동, 림프절 |
| **Full Range** | (max-min) | (max+min)/2 | 전체 HU 범위 표시 |
| **Custom** | 사용자 입력 | 사용자 입력 | 직접 수치 지정 |

### UI 상세

#### 프리셋 드롭다운
- 위치: 상단 툴바 또는 각 뷰포트 상단
- 선택 시 세 뷰포트에 즉시 적용
- 현재 선택된 프리셋 이름 표시

#### 마우스 드래그 조절
- **좌클릭 + 드래그** (기본 도구가 W/L일 때):
  - 좌우 이동: Window Width 변경 (오른쪽으로 갈수록 넓어짐)
  - 상하 이동: Window Level 변경 (위로 갈수록 밝아짐)
- 드래그 중 현재 W/L 값을 뷰포트 하단에 실시간 표시
- 드래그 종료 시 프리셋 드롭다운이 "Custom"으로 변경

#### 수치 직접 입력
- W/L 값 표시 영역 클릭 → 텍스트 입력 가능
- 입력 형식: "W:400 L:40" 또는 별도 두 개 입력 필드
- 유효 범위: Width 1~10000, Level -1024~4000

### 기술 노트
- 윈도우/레벨은 Cornerstone3D의 `setVOI(windowWidth, windowCenter)` 사용
- 세 뷰포트의 W/L은 항상 동기화 (하나를 변경하면 나머지도 변경)
- W/L 변경은 Frontend에서만 처리 (Backend API 호출 없음)

---

## §4. 3D 볼륨 렌더링 (P1)

### 개요
2x2 레이아웃의 4번째 패널에 CT 볼륨의 3D 렌더링을 표시한다.
세그멘테이션이 있을 경우 3D 표면을 함께 렌더링한다.

### 렌더링 모드
| 모드 | 설명 | 용도 |
|------|------|------|
| **Volume Rendering** | Ray casting으로 반투명 볼륨 표시 | CT 전체 구조 파악 |
| **MIP** (Maximum Intensity Projection) | 최대값 투영 | 혈관, 뼈 강조 |
| **Surface + Volume** | 세그멘테이션 표면 + CT 볼륨 합성 | 세그멘테이션 확인 |

### Transfer Function 프리셋 (CT 전용)
| 프리셋 | 설명 |
|--------|------|
| CT-Bone | 뼈를 흰색 불투명, 연조직 반투명 |
| CT-Soft-Tissue | 연조직 강조, 뼈 반투명 |
| CT-Lung | 폐 공기-조직 경계 강조 |
| CT-Muscle | 근육 영역 강조 |
| Custom | 사용자가 HU 구간별 색상/투명도 지정 |

### 3D 인터랙션
- **좌클릭 드래그**: 3D 회전 (trackball 방식)
- **우클릭 드래그**: 팬
- **마우스 휠**: 줌 인/아웃
- **더블 클릭**: 시점 리셋 (정면 뷰)
- **키보드 단축키**: A(Anterior), P(Posterior), S(Superior), I(Inferior), L(Left), R(Right) → 해당 방향 정면 뷰로 이동

### 세그멘테이션 3D 표면
- 세그멘테이션 결과가 있을 때 각 클래스를 Marching Cubes로 mesh 생성
- 각 클래스별 색상은 2D 오버레이와 동일한 컬러맵 사용
- 클래스별 투명도 개별 조절 가능
- 레이블 패널의 표시/숨김 토글이 3D에도 동일하게 적용

### 성능 고려
- 볼륨 렌더링은 GPU 가속 필수 (WebGL2)
- 512^3 이상 볼륨은 다운샘플링 후 렌더링 (기본 256^3으로 리사이즈)
- 3D 표면 mesh는 decimation 적용하여 폴리곤 수 제한 (클래스당 최대 50k triangles)
- 렌더링 품질 옵션: Low(빠름) / Medium(기본) / High(느림)

### API 엔드포인트
3D 렌더링은 Frontend에서 수행하므로 추가 API 불필요.
볼륨 데이터는 §2의 /api/images/{image_id}/volume 재사용.
