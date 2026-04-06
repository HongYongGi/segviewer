# NIfTI 데이터 전송 전략

## 핵심 질문
> 3D 볼륨 데이터(100MB+)를 Backend에서 Frontend로 어떻게 전달할 것인가?

## 결론
**Raw bytes(application/octet-stream)로 전체 볼륨을 전달하고,
메타데이터는 HTTP 커스텀 헤더로 함께 보낸다.**

---

## 배경: 왜 이것이 중요한 문제인가

CT 볼륨의 일반적인 크기를 계산해보자:

| 해상도 | 복셀 수 | Float32 크기 | gzip 압축 후 |
|--------|---------|-------------|-------------|
| 256×256×64 | 4.2M | 16 MB | ~5 MB |
| 512×512×128 | 33.6M | 128 MB | ~40 MB |
| 512×512×256 | 67.1M | 256 MB | ~80 MB |
| 512×512×512 | 134.2M | 512 MB | ~160 MB |

연구에서 흔히 쓰는 512×512×128 해상도의 경우 **128MB의 데이터**를
Backend → Frontend로 전달해야 한다. 이 크기의 데이터를 어떻게 보내느냐에 따라
페이지 로딩 시간이 2초일 수도, 30초일 수도 있다.

---

## 검토한 방법들

### 방법 1: JSON으로 전달
```json
{
  "shape": [512, 512, 128],
  "data": [[-1024, -1024, -1023, ...], [...], ...]
}
```

**문제점**:
- JSON은 텍스트 포맷이므로 숫자 하나당 평균 6~8 bytes (부호 포함)
- Float32(4 bytes)보다 **2배 이상 크다**
- 512×512×128 기준: 바이너리 128MB → JSON 약 300~400MB
- JSON 파싱 자체도 대용량에서 매우 느리다 (수 초)
- ❌ **부적합** — 대용량 의료영상에는 사용 불가

### 방법 2: Base64 인코딩
```json
{
  "shape": [512, 512, 128],
  "dtype": "float32",
  "data_base64": "AAAAAAAAAP8AAAD/..."
}
```

**문제점**:
- Base64는 바이너리를 텍스트로 변환하므로 크기가 33% 증가
- 128MB → 170MB + JSON 오버헤드
- 인코딩/디코딩 과정이 CPU를 많이 사용
- ❌ **부적합** — JSON보다는 낫지만 여전히 비효율적

### 방법 3: Raw bytes + 커스텀 헤더 ← 우리의 선택
```
HTTP/1.1 200 OK
Content-Type: application/octet-stream
X-Image-Shape: 512,512,128
X-Image-Dtype: float32
X-Image-Spacing: 0.75,0.75,2.5
X-Image-ByteOrder: little

[128MB raw bytes]
```

**장점**:
- 데이터 크기가 최소 (원본 numpy array 그대로)
- 추가 인코딩/디코딩 불필요
- Frontend에서 `ArrayBuffer → Float32Array(buffer)` 한 줄로 변환
- HTTP 표준 스펙을 따르므로 범용적

### 방법 4: 슬라이스 단위로 쪼개서 전달
```
GET /api/images/{id}/slice?axis=axial&index=0
GET /api/images/{id}/slice?axis=axial&index=1
...
GET /api/images/{id}/slice?axis=axial&index=127
```

**문제점**:
- 128개 슬라이스 → 128번의 HTTP 요청 → 오버헤드 큼
- 3개 축 × 최대 512 슬라이스 = 최대 1,536번 요청 가능
- Cornerstone3D VolumeViewport는 전체 볼륨이 메모리에 있어야 동작
- ❌ **주 전달 방식으로는 부적합** (보조 용도로만 사용: 단일 슬라이스 미리보기 등)

### 방법 5: 파일 다운로드 (NIfTI 그대로)
Frontend에서 원본 .nii.gz를 직접 다운로드하고,
JavaScript로 NIfTI를 파싱하는 방법이다.

**장점**:
- gzip 압축 상태로 전달하므로 전송량이 가장 작음 (40MB)
- nifti-reader-js 같은 라이브러리 존재

**단점**:
- NIfTI 파싱을 JavaScript에서 해야 하므로 복잡도 증가
- RAS+ 변환, affine 처리를 Frontend에서 해야 함 (데이터 무결성 원칙 위반 가능)
- Backend와 Frontend에서 NIfTI 처리 로직이 중복됨

**판단**: 전송량 면에서는 최적이지만, "데이터 처리는 Backend에서"라는
관심사 분리 원칙에 위배된다. P2에서 최적화 옵션으로 재검토.

---

## 최종 결정: Raw bytes + 커스텀 헤더

### 전송 포맷 상세

#### 볼륨 데이터 (CT 원본)
```
바이트 순서: Little-endian
데이터 타입: Float32 (4 bytes per voxel)
배열 순서: C-contiguous (row-major)
       → data[z][y][x] 순서로 flatten

예: shape=(512, 512, 128)이면
    총 바이트 = 512 × 512 × 128 × 4 = 134,217,728 bytes
    
    메모리 레이아웃:
    [z=0, y=0, x=0] [z=0, y=0, x=1] ... [z=0, y=0, x=511]
    [z=0, y=1, x=0] [z=0, y=1, x=1] ... [z=0, y=1, x=511]
    ...
    [z=127, y=511, x=0] ... [z=127, y=511, x=511]
```

#### 세그멘테이션 데이터
```
바이트 순서: Little-endian
데이터 타입: Uint8 (1 byte per voxel) — 클래스 < 256일 때
배열 순서: C-contiguous (CT와 동일)

예: shape=(512, 512, 128)이면
    총 바이트 = 512 × 512 × 128 × 1 = 33,554,432 bytes (32MB)
```

#### 커스텀 헤더 명세
| 헤더 | 값 형식 | 예시 | 설명 |
|------|--------|------|------|
| X-Image-Shape | 쉼표 구분 정수 | 512,512,128 | numpy shape (z,y,x 아닌 x,y,z 순) |
| X-Image-Dtype | 문자열 | float32 | numpy dtype 이름 |
| X-Image-Spacing | 쉼표 구분 실수 | 0.75,0.75,2.5 | mm 단위 복셀 크기 |
| X-Image-ByteOrder | 문자열 | little | 바이트 순서 |
| X-Image-Affine | 쉼표 구분 실수 16개 | 0.75,0,...,1 | 4x4 행렬을 1D로 flatten |

### Frontend에서의 사용
```typescript
// 볼륨 데이터 수신 및 변환 (의사 코드)
const response = await fetch(`/api/images/${imageId}/volume`);
const buffer = await response.arrayBuffer();

const shape = response.headers.get('X-Image-Shape')
  .split(',').map(Number);  // [512, 512, 128]
const dtype = response.headers.get('X-Image-Dtype');  // "float32"

// ArrayBuffer → TypedArray
const volumeData = new Float32Array(buffer);

// Cornerstone3D Volume에 데이터 주입
// volumeData를 Cornerstone3D의 imageData로 설정
```

---

## 대용량 볼륨 대응 전략

### 문제
512×512×512 볼륨이면 512MB다. 이걸 한 번에 전송하면:
- 전송 시간: 로컬 네트워크(1Gbps) 기준 ~4초
- 브라우저 메모리: 512MB + 렌더링 버퍼 → 1GB 이상 필요
- 일부 브라우저는 메모리 한도 초과로 크래시 가능

### 해결: 다운샘플링 + Progressive Loading

**1단계: 다운샘플된 볼륨으로 즉시 표시**
```
GET /api/images/{id}/volume?downsample=2
→ 256×256×64 = 16MB 전송
→ 1~2초 내에 대략적인 영상 확인 가능
```

**2단계: 원본 해상도로 백그라운드 교체**
```
GET /api/images/{id}/volume  (원본)
→ 전송 완료 후 뷰어의 데이터를 원본으로 교체
→ 사용자는 대기 없이 바로 탐색 시작, 해상도만 나중에 올라감
```

### 다운샘플링 기준
| 전체 복셀 수 | 다운샘플 팩터 | 결과 크기 |
|-------------|-------------|----------|
| < 64M (256³) | 1 (없음) | 그대로 |
| 64M ~ 256M | 2 | 원본의 1/8 |
| 256M ~ 1G | 4 | 원본의 1/64 |
| > 1G | 8 | 원본의 1/512 |

다운샘플링 방법: `scipy.ndimage.zoom(data, 1/factor, order=1)`
(order=1 = bilinear, CT에서 충분한 품질)

---

## gzip 압축 검토

### HTTP Content-Encoding: gzip
FastAPI에서 GZipMiddleware를 활성화하면 응답을 자동 gzip 압축할 수 있다.

| 데이터 | 원본 | gzip 후 | 압축률 |
|--------|------|---------|--------|
| CT 볼륨 (512×512×128, float32) | 128MB | ~45MB | 65% |
| 세그멘테이션 (512×512×128, uint8) | 32MB | ~2MB | 94% |

세그멘테이션은 대부분의 복셀이 0(background)이므로 압축률이 매우 높다.

### 결정
- **세그멘테이션**: gzip 적용 (압축률 90%+, 효과 극대)
- **CT 볼륨**: MVP에서는 gzip 미적용 (CPU 부하 vs 전송 시간 트레이드오프)
  - 로컬 네트워크에서 128MB 전송은 ~1초 (1Gbps 기준)
  - gzip 압축에 2~3초 소요 → 오히려 느려질 수 있음
  - P2에서 조건부 적용 검토 (네트워크 속도에 따라)
