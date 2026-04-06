# Phase 1: MVP Core — P0 핵심 기능

## 목표
사용자가 NIfTI 파일을 업로드하고, nnUNet 모델을 선택하여 inference를 실행하고,
세그멘테이션 결과를 2D 슬라이스 뷰어에서 오버레이로 확인할 수 있는 상태까지.

**이 Phase가 끝나면 앱이 "사용 가능한" 상태가 된다.**

## 왜 이 순서인가
각 작업의 의존관계를 따라 순서를 정했다:
```
1-1 NIfTI 업로드/저장   (독립, Frontend/Backend 동시 작업 가능)
       ↓
1-2 2D 슬라이스 뷰어    (업로드된 볼륨 데이터 필요)
       ↓
1-3 윈도우/레벨         (뷰어가 있어야 W/L 적용 가능)
       ↓
1-4 모델 목록 조회      (독립, Backend만 작업)
       ↓
1-5 Inference 실행     (업로드 + 모델 선택이 모두 필요)
       ↓
1-6 세그멘테이션 오버레이 (inference 결과 + 뷰어 둘 다 필요)
```

## 예상 소요: 1~2주

---

## 작업 상세

### 1-1. NIfTI 파일 업로드 (Backend + Frontend)
**참조 스펙**: product-specs/image-upload-and-view.md §1

#### Backend 작업
1. `POST /api/images/upload` 엔드포인트 구현
2. 파일 검증 로직 구현 (확장자, nibabel.load, 3D 확인, 파일 크기)
3. RAS+ 변환 (`nibabel.as_closest_canonical`)
4. `uploads/{image_id}/` 에 original.nii.gz + canonical.nii.gz 저장
5. metadata.json 생성 (shape, spacing, affine, dtype, hu_range)
6. `GET /api/images/{image_id}/metadata` 엔드포인트 구현

#### Frontend 작업
1. 파일 업로드 버튼 + 드래그앤드롭 영역 구현
2. 업로드 진행률 바 (axios onUploadProgress)
3. 업로드 성공 시 메타데이터 패널에 정보 표시
4. 에러 발생 시 사용자 친화적 메시지 표시

#### 테스트 방법
```bash
# Backend 단독 테스트
curl -X POST http://localhost:8000/api/images/upload \
  -F "file=@test_ct.nii.gz"
# → { "image_id": "...", "metadata": { ... } } 확인

# 에러 케이스
curl -X POST http://localhost:8000/api/images/upload \
  -F "file=@not_a_nifti.txt"
# → 400 INVALID_NIFTI_FORMAT 확인
```

#### 완료 기준
- [ ] .nii.gz 파일을 업로드하면 image_id와 메타데이터가 반환된다
- [ ] 잘못된 파일을 업로드하면 적절한 에러 메시지가 반환된다
- [ ] uploads/ 디렉토리에 original + canonical 파일이 저장된다
- [ ] Frontend에서 업로드 후 메타데이터가 표시된다

---

### 1-2. 2D 슬라이스 뷰어 (Frontend 중심)
**참조 스펙**: product-specs/image-upload-and-view.md §2

#### Backend 작업
1. `GET /api/images/{image_id}/volume` 엔드포인트 구현
   - canonical.nii.gz를 로드하여 numpy array → raw bytes 변환
   - 커스텀 헤더(X-Image-Shape, X-Image-Dtype, X-Image-Spacing) 설정
2. `GET /api/images/{image_id}/slice` 엔드포인트 구현 (보조용)

#### Frontend 작업
1. **Cornerstone3D 초기화**
   - cornerstoneInit() 호출 (WASM loader 설정)
   - RenderingEngine 생성
   - 3개 StackViewport 생성 (axial, coronal, sagittal)

2. **볼륨 로딩**
   - `/api/images/{image_id}/volume` 에서 ArrayBuffer 수신
   - 커스텀 헤더에서 shape, dtype 파싱
   - `Float32Array(buffer)` → Cornerstone3D Volume 생성
   - 3개 viewport에 각 방향의 슬라이스 렌더링

3. **기본 인터랙션**
   - 마우스 휠: 슬라이스 이동
   - 각 뷰포트 하단 슬라이더: 슬라이스 위치 표시/조절
   - 슬라이스 번호 표시: 좌측 상단 "Slice: 64/128"

4. **크로스헤어 동기화**
   - 한 뷰포트에서 클릭 시 world coordinate 계산
   - 나머지 2개 뷰포트의 슬라이스 위치 업데이트
   - 크로스헤어 라인 렌더링 (점선)

5. **방향 라벨 표시**
   - Axial: A/P/R/L
   - Coronal: S/I/R/L
   - Sagittal: S/I/A/P

#### 핵심 난이도 포인트
- **Cornerstone3D 초기화가 까다롭다**: WASM loader, dicomParser 등
  여러 의존성을 올바르게 초기화해야 함. OHIF Viewer의 초기화 코드를 참고.
- **볼륨 데이터 변환**: Backend에서 받은 raw bytes를
  Cornerstone3D가 기대하는 형식으로 변환하는 과정에서
  byte order, array shape이 맞지 않으면 영상이 뒤집히거나 깨짐.
  **반드시 작은 테스트 볼륨(64^3)으로 먼저 검증.**

#### 테스트 방법
1. 알려진 CT 파일(예: BTCV dataset의 CT)을 업로드
2. Axial 뷰에서 복부 해부학 구조가 올바른 방향인지 확인
   - 간(Liver)이 우측(화면 좌측)에 있는지
   - 척추(Spine)가 후방(화면 하단)에 있는지
3. 크로스헤어 동기화: Axial에서 간을 클릭하면
   Coronal/Sagittal에서도 간 위치로 이동하는지

#### 완료 기준
- [ ] 업로드된 영상이 3개 뷰포트에 올바른 방향으로 표시된다
- [ ] 마우스 휠로 슬라이스 이동이 된다
- [ ] 크로스헤어가 세 뷰포트 간 동기화된다
- [ ] 슬라이스 번호가 정확히 표시된다

---

### 1-3. 윈도우/레벨 조절
**참조 스펙**: product-specs/image-upload-and-view.md §3

#### Frontend 작업 (Backend 작업 없음)
1. CT 프리셋 드롭다운 구현 (Abdomen, Lung, Bone, Brain, Liver, Mediastinum)
2. 기본 프리셋: Abdomen (W:400, L:40)
3. 좌클릭 드래그로 W/L 실시간 조절
4. 현재 W/L 값 표시
5. 세 뷰포트 W/L 동기화

#### 구현 가이드
```typescript
// Cornerstone3D에서 W/L 설정
viewport.setVOI({ lower: level - width/2, upper: level + width/2 });
viewport.render();

// 프리셋 적용
const presets = {
  abdomen: { width: 400, level: 40 },
  lung: { width: 1500, level: -600 },
  bone: { width: 2000, level: 400 },
  // ...
};
```

#### 완료 기준
- [ ] 프리셋 드롭다운에서 선택하면 영상 밝기/대비가 즉시 변경된다
- [ ] Lung 프리셋에서 폐가 잘 보이고, Bone에서 뼈가 잘 보인다
- [ ] 마우스 드래그로 W/L을 자유롭게 조절할 수 있다

---

### 1-4. 모델 목록 조회
**참조 스펙**: product-specs/inference-pipeline.md §1

#### Backend 작업
1. `ModelService` 구현
   - nnUNet_results 디렉토리 재귀 스캔
   - Dataset/Trainer/Plans/Configuration 파싱
   - dataset.json에서 labels 추출
   - fold별 checkpoint 존재 확인
2. `GET /api/models/` 엔드포인트 구현
3. `GET /api/models/refresh` 엔드포인트 구현
4. 앱 시작 시 자동 스캔 + 캐시

#### Frontend 작업
1. 모델 선택 드롭다운 구현 (Dataset → Configuration → Fold)
2. 모델 정보 팝오버 (클래스 수, 클래스 목록, fold 수)
3. 모델이 없을 때 "nnUNet_results에 모델이 없습니다" 안내

#### 테스트 방법
```bash
# nnUNet_results 구조가 올바르게 파싱되는지
curl http://localhost:8000/api/models/
# → models 배열에 각 Dataset/Configuration이 나열되는지 확인
# → labels 딕셔너리가 올바른지 확인
```

#### 완료 기준
- [ ] nnUNet_results의 모든 모델이 자동으로 탐지된다
- [ ] dataset.json의 labels가 정확히 추출된다
- [ ] checkpoint가 없는 fold는 목록에서 제외된다
- [ ] Frontend에서 Dataset → Configuration → Fold 선택이 가능하다

---

### 1-5. Inference 실행
**참조 스펙**: product-specs/inference-pipeline.md §2

#### Backend 작업
1. `InferenceService` 구현
   - nnUNetPredictor 초기화 및 캐싱
   - 입력 파일 준비 (심볼릭 링크 + 파일명 규칙 적용)
   - `predict_from_files()` 호출
   - 결과 NIfTI 저장
2. 비동기 작업 큐 구현 (asyncio.Queue + worker)
3. `POST /api/inference/run` 엔드포인트
4. `GET /api/inference/{job_id}/status` 엔드포인트
5. WebSocket `/ws/inference/{job_id}` 진행률 전달

#### Frontend 작업
1. [Run Inference] 버튼 구현
2. 진행률 바 + 단계 텍스트 표시
3. WebSocket 연결하여 실시간 상태 수신
4. 완료 시 자동으로 세그멘테이션 로딩 트리거

#### 핵심 난이도 포인트
- **nnUNetPredictor 초기화**: `initialize_from_trained_model_folder()`의
  매개변수를 정확히 맞춰야 함. 특히 `use_folds` 형식이 tuple이어야 함.
- **비동기 처리**: inference는 동기 코드(PyTorch)인데 FastAPI는 비동기이므로
  `asyncio.to_thread()`로 감싸야 함. 이 과정에서 progress callback 전달이
  까다로울 수 있음.
- **파일명 규칙**: nnUNet은 `{CASE_ID}_0000.nii.gz` 형태를 요구함.
  이걸 자동으로 만들어주는 유틸리티가 필요.

#### 테스트 방법
1. 알려진 nnUNet 모델(학습 완료, 성능 확인 완료)로 테스트
2. CLI에서 같은 모델로 inference한 결과와 웹앱 결과를 비교
   - `nibabel.load(web_result).get_fdata()` == `nibabel.load(cli_result).get_fdata()`
   - 결과가 완전히 동일해야 함 (bit-exact)
3. 두 번째 inference에서 모델 캐싱이 동작하는지 확인 (로딩 시간 측정)

#### 완료 기준
- [ ] 업로드된 영상에 대해 inference가 성공적으로 실행된다
- [ ] 결과가 CLI에서 돌린 것과 동일하다 (bit-exact)
- [ ] 두 번째 실행 시 모델 로딩을 건너뛴다 (캐싱 동작)
- [ ] 진행률이 실시간으로 Frontend에 표시된다
- [ ] GPU OOM 발생 시 적절한 에러 메시지가 표시된다

---

### 1-6. 세그멘테이션 오버레이
**참조 스펙**: product-specs/segmentation-overlay.md §1, §2

#### Backend 작업
1. `GET /api/segments/{result_id}/volume` 엔드포인트 구현
   - 세그멘테이션 NIfTI를 uint8 raw bytes로 반환
2. `GET /api/segments/{result_id}/metadata` 엔드포인트 구현

#### Frontend 작업
1. **세그멘테이션 데이터 로딩**
   - `/api/segments/{result_id}/volume` 에서 수신
   - `Uint8Array(buffer)` → Cornerstone3D Segmentation 생성
   - Segmentation representation을 각 viewport에 추가

2. **컬러맵 설정**
   - dataset.json의 labels에 따라 색상 자동 배정
   - Cornerstone3D colorLUT 설정

3. **레이블 패널 구현**
   - 우측 사이드바에 클래스 목록 표시
   - 각 클래스: 체크박스 + 색상 + 이름 + 복셀 비율(%)
   - 체크박스 토글 → 해당 클래스 표시/숨김

4. **전체 투명도 슬라이더**
   - 0~100% 범위
   - 기본값 50%
   - 실시간 반영

#### 완료 기준
- [ ] inference 완료 후 세그멘테이션이 컬러 오버레이로 표시된다
- [ ] 각 클래스가 구분 가능한 고유 색상을 갖는다
- [ ] 체크박스로 개별 클래스를 숨기고 표시할 수 있다
- [ ] 투명도 슬라이더가 실시간으로 동작한다
- [ ] 레이블 이름이 dataset.json의 이름과 일치한다

---

## Phase 1 완료 = MVP 완성

Phase 1이 끝나면 다음이 가능하다:
1. ✅ NIfTI CT 파일을 브라우저에서 업로드
2. ✅ 2D 슬라이스로 Axial/Coronal/Sagittal 확인
3. ✅ CT 윈도우/레벨 프리셋으로 최적 표시
4. ✅ nnUNet 모델 선택 + inference 실행
5. ✅ 세그멘테이션 결과를 컬러 오버레이로 확인
6. ✅ 클래스별 표시/숨김 토글

**이 시점에서 연구실 내부 사용을 시작할 수 있다.**
3D 렌더링, 브러시 편집 등은 Phase 2에서 추가한다.
