# Phase 2: Advanced Visualization — P1 기능 (3D + 편집)

## 목표
MVP에 3D 볼륨 렌더링과 브러시/지우개 편집 기능을 추가하여,
ITK-SNAP 수준의 시각화 + 편집 환경을 웹에서 제공한다.

## 전제 조건
Phase 1이 완료되어 2D 슬라이스 뷰어 + inference + 오버레이가 동작하는 상태.

## 예상 소요: 1~2주

---

## 작업 목록 및 의존관계

```
2-1 3D 볼륨 렌더링       (Phase 1의 볼륨 로딩에 의존)
       ↓
2-2 세그멘테이션 3D 표면   (2-1 + Phase 1의 세그멘테이션에 의존)

2-3 브러시/지우개 도구     (Phase 1의 세그멘테이션에 의존, 2-1과 병렬 가능)
       ↓
2-4 Undo/Redo           (2-3에 의존)
       ↓
2-5 편집 결과 저장        (2-3에 의존)
```

2-1/2-2(3D)와 2-3/2-4/2-5(편집)는 **병렬로 진행 가능**하다.

---

## 작업 상세

### 2-1. 3D 볼륨 렌더링
**참조 스펙**: product-specs/image-upload-and-view.md §4

#### 작업 내용
1. 2x2 레이아웃의 4번째 패널에 Cornerstone3D VolumeViewport 추가
2. Ray casting 볼륨 렌더링 구현
3. Transfer Function 프리셋 구현 (CT-Bone, CT-Soft-Tissue, CT-Lung)
4. 3D 인터랙션 구현 (회전, 줌, 팬)
5. 방향 표시 (Anterior/Posterior/Superior/Inferior 라벨)
6. 대용량 볼륨 다운샘플링 (512^3 이상일 때)

#### 핵심 난이도 포인트
- Cornerstone3D VolumeViewport 초기화가 StackViewport와 다름
- Transfer Function 설정이 Cornerstone3D에서 어떻게 노출되는지
  API 문서를 정확히 확인해야 함
- WebGL2 컨텍스트 관리: 3개 StackViewport + 1개 VolumeViewport = 4개
  동시에 관리하면 일부 GPU에서 컨텍스트 제한에 걸릴 수 있음

#### 완료 기준
- [ ] 4번째 패널에 CT 볼륨이 3D로 렌더링된다
- [ ] 마우스 드래그로 3D 회전이 가능하다
- [ ] Transfer Function 프리셋을 변경하면 렌더링이 변한다

---

### 2-2. 세그멘테이션 3D 표면 렌더링
**참조 스펙**: product-specs/segmentation-overlay.md §3

#### Backend 작업
1. Mesh 생성 API 구현
   - 각 클래스 바이너리 마스크에 Marching Cubes 적용
   - Laplacian smoothing (iterations=3)
   - Decimation (클래스당 최대 50k triangles)
2. `GET /api/segments/{result_id}/mesh?class_id=N` 엔드포인트
3. `GET /api/segments/{result_id}/mesh/all` 엔드포인트

#### Frontend 작업
1. Mesh 데이터를 3D viewport에 추가
2. 각 클래스별 색상 + 투명도 설정
3. 레이블 패널의 표시/숨김이 3D 표면에도 적용

#### 핵심 난이도 포인트
- Marching Cubes는 `skimage.measure.marching_cubes`로 구현 가능
- Mesh를 Frontend에 전달하는 바이너리 포맷 설계가 중요
- 클래스가 많으면(10+) mesh 생성에 시간이 걸리므로 비동기 처리 필요

#### 완료 기준
- [ ] 세그멘테이션 각 클래스가 3D 표면(mesh)으로 표시된다
- [ ] CT 볼륨 렌더링 위에 세그멘테이션 표면이 합성된다
- [ ] 클래스별 표시/숨김이 3D에서도 동작한다

---

### 2-3. 브러시/지우개 편집 도구
**참조 스펙**: product-specs/segmentation-editor.md §1

#### Frontend 작업 (Backend 작업 없음)
1. **도구 패널 UI 구현**
   - Brush / Eraser / Navigate 라디오 버튼
   - 브러시 크기 슬라이더 (1~50px)
   - 활성 레이블 표시

2. **Cornerstone3D BrushTool 연결**
   - BrushTool 등록 및 활성화
   - brushSize, activeSegmentIndex 바인딩
   - FILL_INSIDE_CIRCLE 전략 사용

3. **Eraser 구현**
   - BrushTool의 변형: activeSegmentIndex = 0
   - 별도 크기 설정 지원

4. **키보드 단축키 연결**
   - B: 브러시, E: 지우개, N/Esc: Navigate
   - [/]: 크기 조절, 1~9: 레이블 선택
   - Space 길게 누르기: 임시 Navigate

5. **커서 표시**
   - 브러시: 활성 레이블 색상의 반투명 원형
   - 지우개: 빨간색 테두리 원형
   - 크기에 따라 커서 크기 변경

6. **크로스 뷰포트 반영**
   - Axial에서 편집하면 Coronal/Sagittal에 즉시 반영
   - 3D 뷰에서는 편집 불가 (조회만)

#### 핵심 난이도 포인트
- Cornerstone3D의 BrushTool 설정이 버전마다 다를 수 있음
- 편집 후 다른 뷰포트의 렌더링을 명시적으로 갱신해야 함
- 큰 브러시(50px)로 빠르게 드래그하면 성능 이슈 가능

#### 완료 기준
- [ ] 브러시로 세그멘테이션 영역을 추가할 수 있다
- [ ] 지우개로 세그멘테이션 영역을 삭제할 수 있다
- [ ] 레이블을 선택하여 다른 클래스로 칠할 수 있다
- [ ] 브러시 크기를 조절할 수 있다
- [ ] 키보드 단축키가 동작한다
- [ ] 한 뷰포트에서 편집하면 다른 뷰포트에 즉시 반영된다

---

### 2-4. Undo/Redo
**참조 스펙**: product-specs/segmentation-editor.md §2

#### Frontend 작업 (Backend 작업 없음)
1. EditAction 인터페이스 정의 (변경된 복셀의 before/after 기록)
2. undoStack, redoStack 구현 (최대 20개)
3. 마우스 드래그 시작~종료를 하나의 action으로 기록
4. Ctrl+Z → undo, Ctrl+Shift+Z → redo 연결
5. Undo/Redo 버튼 UI (스택 비어있으면 비활성화)

#### 핵심 난이도 포인트
- 변경된 복셀만 저장하는 방식이어야 함 (전체 볼륨 스냅샷은 메모리 과다)
- 큰 브러시로 많은 복셀을 한 번에 편집하면 action 크기가 커질 수 있음
- Cornerstone3D의 segmentation 데이터에서 변경 전 값을 미리 읽어야 함

#### 완료 기준
- [ ] Ctrl+Z로 마지막 편집을 되돌릴 수 있다
- [ ] Ctrl+Shift+Z로 되돌린 편집을 다시 적용할 수 있다
- [ ] 새 편집 시 redo 스택이 초기화된다
- [ ] 20개 초과 시 가장 오래된 이력이 삭제된다

---

### 2-5. 편집 결과 저장
**참조 스펙**: product-specs/segmentation-editor.md §3

#### Backend 작업
1. `PUT /api/segments/{result_id}` 엔드포인트 구현
   - raw bytes 수신 → numpy array 변환
   - shape 일치 검증, 값 범위 검증
   - 원본 affine으로 NIfTI 저장
   - 기존 파일 백업 (최대 5개)
2. metadata.json의 `edited` 필드 업데이트

#### Frontend 작업
1. [Save] 버튼 (또는 Ctrl+S)
2. 확인 다이얼로그
3. 전체 세그멘테이션 볼륨을 ArrayBuffer로 직렬화 → PUT 전송
4. 미저장 편집 경고 (다른 영상 로드 시, 탭 닫기 시)
5. 저장 완료 토스트 메시지

#### 완료 기준
- [ ] 편집된 세그멘테이션을 저장하면 Backend에 NIfTI로 저장된다
- [ ] 저장된 NIfTI의 affine/spacing이 원본과 동일하다
- [ ] 미저장 편집이 있을 때 경고가 표시된다
- [ ] 백업 파일이 생성된다

---

## Phase 2 완료 후 상태

Phase 1(MVP) + Phase 2가 끝나면:
1. ✅ 2D 슬라이스 뷰어 + 3D 볼륨 렌더링
2. ✅ nnUNet inference + 결과 오버레이
3. ✅ 세그멘테이션 3D 표면
4. ✅ 브러시/지우개 편집 + Undo/Redo
5. ✅ 편집 결과 NIfTI 저장

**이 시점에서 ITK-SNAP을 대체하는 수준의 뷰어가 완성된다.**
