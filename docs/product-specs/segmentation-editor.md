# 세그멘테이션 편집 도구 스펙 (P1)

## §1. 브러시/지우개 편집

### 개요
사용자가 2D 슬라이스 뷰에서 브러시(칠하기)와 지우개(지우기) 도구로
세그멘테이션 결과를 픽셀 단위로 수정할 수 있다.
편집은 2D 뷰에서만 가능하며, 3D 뷰에서는 조회만 가능하다.

### 왜 편집이 필요한가 (배경 설명)
nnUNet은 최고 수준의 세그멘테이션 모델이지만, 100% 완벽한 결과를 내지는 않는다.
특히 다음 상황에서 수동 수정이 필요하다:
- 장기 경계가 불명확한 영역 (예: 간과 횡격막 경계)
- 작은 병변이 누락된 경우
- 다른 구조물이 잘못 포함된 경우 (false positive)
- 학습 데이터와 다른 해부학적 변이

### 도구 목록

#### 브러시 (Brush)
- **용도**: 특정 클래스의 영역을 추가 (칠하기)
- **동작**: 마우스 드래그 시 현재 활성 레이블(class_id)로 복셀 값 변경
- **형태**: 원형 브러시
- **크기**: 1~50px (슬라이더 또는 단축키로 조절)
- **활성 레이블**: 레이블 패널에서 선택된 클래스 (예: "Liver" → class_id=1)

#### 지우개 (Eraser)
- **용도**: 세그멘테이션 영역을 제거
- **동작**: 마우스 드래그 시 복셀 값을 0(background)으로 변경
- **형태**: 원형
- **크기**: 브러시와 독립적으로 1~50px 조절 가능
- **참고**: 지우개는 모든 클래스를 지운다 (선택적 지우기는 P2)

### 도구 전환 UI

#### 도구 패널
```
┌──────────────────────────────┐
│ 🖌️ Brush  | 🧹 Eraser | 🖱️ Navigate │ ← 도구 선택 (라디오 버튼 방식)
│                              │
│ Size: [●━━━━━━━━━━○] 10px   │ ← 브러시/지우개 크기 슬라이더
│                              │
│ Active Label: 🟥 Liver       │ ← 현재 브러시가 칠할 클래스
└──────────────────────────────┘
```

#### Navigate 도구
- 기본 도구: 편집 도구가 아닌 탐색 도구 (W/L, 슬라이스 이동, 팬, 줌)
- 편집 중이 아닐 때의 기본 상태
- 브러시/지우개 사용 중에도 키보드 단축키로 임시 전환 가능

### 키보드 단축키

| 키 | 동작 |
|----|------|
| **B** | 브러시 도구 활성화 |
| **E** | 지우개 도구 활성화 |
| **N** 또는 **Esc** | Navigate 도구 (편집 해제) |
| **[** | 브러시/지우개 크기 -1 |
| **]** | 브러시/지우개 크기 +1 |
| **Shift + [** | 브러시/지우개 크기 -5 |
| **Shift + ]** | 브러시/지우개 크기 +5 |
| **1~9** | 레이블 1~9 빠른 선택 (브러시 활성 레이블) |
| **Ctrl + Z** | Undo |
| **Ctrl + Shift + Z** | Redo |
| **Ctrl + S** | 세그멘테이션 저장 |
| **Space** (길게 누르기) | 임시로 Navigate 도구 전환 (놓으면 이전 도구로 복귀) |

### 활성 레이블 선택

#### 선택 방법
1. **레이블 패널에서 클릭**: 클래스 이름을 클릭하면 활성 레이블로 설정
   - 선택된 클래스는 하이라이트 표시 (진한 배경색)
   - background(0)는 선택 불가 (지우개를 사용)
2. **숫자 키**: 1~9로 빠르게 선택
3. **브러시 커서**: 현재 활성 레이블의 색상으로 브러시 커서 표시

#### 커서 표시
- **브러시 모드**: 활성 레이블 색상의 반투명 원형 (크기는 현재 설정)
- **지우개 모드**: 빨간색 테두리의 원형
- **Navigate 모드**: 기본 화살표 커서

### 편집 동작 상세

#### 브러시 칠하기
```
1. 사용자가 2D 슬라이스 위에서 마우스 좌클릭 + 드래그
2. 마우스 경로를 따라 원형 브러시 영역 내 모든 복셀이
   활성 레이블(class_id)로 변경된다
3. 변경은 현재 보고 있는 슬라이스에만 적용 (2D 편집)
4. 변경이 즉시 화면에 반영된다 (오버레이 업데이트)
5. 드래그 시작부터 종료(마우스 떼기)까지가 하나의 undo 단위
```

#### 지우개 지우기
```
1. 사용자가 2D 슬라이스 위에서 마우스 좌클릭 + 드래그
2. 마우스 경로를 따라 원형 영역 내 모든 복셀이 0(background)으로 변경
3. 다른 클래스 위를 지나가도 모두 0으로 변경 (선택적 지우기는 P2)
```

#### 편집 범위
- **슬라이스 단위**: 현재 보고 있는 2D 슬라이스에만 적용
- **3D 편집 없음**: 여러 슬라이스에 걸쳐 한 번에 편집하는 기능은 P2
- **뷰포트 독립**: Axial에서 편집한 결과는 Coronal/Sagittal에도 즉시 반영
  (내부적으로는 같은 3D 볼륨의 다른 단면이므로)

### Cornerstone3D 구현 가이드
```
1. BrushTool (cornerstoneTools) 등록
   - strategyName: 'FILL_INSIDE_CIRCLE'
   - brushSize: 사용자 설정값
   - activeSegmentIndex: 활성 레이블 class_id

2. EraserTool은 BrushTool의 변형
   - activeSegmentIndex를 0(background)으로 고정
   - 또는 segmentationData에서 해당 영역을 0으로 직접 설정

3. 편집 시 segmentationData를 직접 수정
   - Cornerstone3D의 segmentation labelmap은 TypedArray
   - 수정 후 viewport.render() 호출하여 즉시 반영

4. 크로스헤어 업데이트
   - Axial에서 편집 후 Coronal/Sagittal도 render() 호출
```

---

## §2. Undo/Redo

### 개요
편집 실수를 되돌리거나 다시 적용할 수 있다.
메모리 기반으로 Frontend에서만 관리한다.

### 구현 방식

#### Undo 스택
- **최대 20개** 편집 이력 유지
- 각 이력은 **변경된 복셀들의 스냅샷**을 저장:
  ```typescript
  interface EditAction {
    sliceAxis: 'axial' | 'coronal' | 'sagittal';
    sliceIndex: number;
    changedVoxels: {
      x: number;
      y: number;
      oldValue: number;  // 이전 클래스 ID
      newValue: number;  // 새 클래스 ID
    }[];
    timestamp: number;
  }
  ```
- 전체 볼륨 스냅샷이 아니라 **변경된 복셀만** 저장하여 메모리 절약

#### Undo 동작
```
1. Ctrl+Z 입력
2. undoStack에서 마지막 EditAction을 꺼냄 (pop)
3. changedVoxels의 각 복셀을 oldValue로 되돌림
4. 되돌린 EditAction을 redoStack에 push
5. 화면 즉시 반영 (viewport.render)
```

#### Redo 동작
```
1. Ctrl+Shift+Z 입력
2. redoStack에서 마지막 EditAction을 꺼냄 (pop)
3. changedVoxels의 각 복셀을 newValue로 다시 적용
4. 적용한 EditAction을 undoStack에 push
5. 화면 즉시 반영
```

#### 주의 사항
- 새 편집을 하면 redoStack은 **전체 초기화** (일반적인 undo/redo 패턴)
- 20개 초과 시 가장 오래된 이력부터 삭제
- 저장(Save) 후에도 undo 스택은 유지 (세션 내)
- 영상을 새로 로드하거나 다른 세그멘테이션을 로드하면 스택 초기화

### UI 표시
- **Undo 버튼**: 도구 패널 또는 상단 툴바에 ↩ 아이콘
- **Redo 버튼**: ↪ 아이콘
- 스택이 비어있으면 버튼 비활성화 (회색)
- 남은 undo 횟수 표시 (선택): "Undo (3)" 

---

## §3. 편집 결과 저장

### 개요
브러시/지우개로 수정한 세그멘테이션을 Backend에 전송하여
NIfTI 파일로 저장한다. 저장은 명시적으로 "Save" 버튼을 클릭해야만 실행된다.

### 저장 시나리오
```
1. 사용자가 브러시/지우개로 편집을 완료한다
2. [Save] 버튼 클릭 (또는 Ctrl+S)
3. 확인 다이얼로그: "수정된 세그멘테이션을 저장하시겠습니까?"
4. "저장" 클릭
5. Frontend에서 전체 세그멘테이션 볼륨을 ArrayBuffer로 직렬화
6. PUT /api/segments/{result_id} 로 전송
7. Backend에서 원본 affine/spacing으로 NIfTI 저장
8. 완료 토스트 메시지: "저장 완료"
```

### 미저장 경고
편집이 있는 상태에서 아래 동작을 시도하면 경고를 표시한다:
- 새 영상 업로드
- 다른 세그멘테이션 결과 로드
- 새 inference 실행
- 브라우저 탭 닫기 (beforeunload 이벤트)

경고 메시지: "저장하지 않은 편집이 있습니다. 저장하시겠습니까?"
→ [저장] [저장하지 않고 계속] [취소]

### API 엔드포인트

#### PUT /api/segments/{result_id}
**Request**:
```
Content-Type: application/octet-stream
X-Seg-Shape: 512,512,128
X-Seg-Dtype: uint8
Body: Raw bytes (전체 세그멘테이션 볼륨)
```

**Response (200)**:
```json
{
  "result_id": "result-abc-456",
  "updated_at": "2025-01-15T11:00:00Z",
  "edited": true,
  "file_path": "results/a1b2c3d4/result-abc-456.nii.gz",
  "backup_path": "results/a1b2c3d4/result-abc-456_backup_20250115T110000.nii.gz"
}
```

### 백업 정책
- 저장 시 기존 파일을 덮어쓰기 전에 **백업 파일 생성**
- 백업 파일명: `{result_id}_backup_{timestamp}.nii.gz`
- 최대 5개 백업 유지, 초과 시 가장 오래된 것 삭제
- 백업은 사용자에게 노출하지 않음 (관리자 수준에서만 접근)

### 검증 규칙 (Backend)
수신한 세그멘테이션 데이터를 저장하기 전에 아래를 검증한다:

| 검증 | 에러 코드 | 설명 |
|------|----------|------|
| Shape 일치 | SHAPE_MISMATCH | 원본 영상과 shape가 다르면 거부 |
| 값 범위 | INVALID_LABEL_VALUE | 유효한 클래스 ID 범위를 벗어나면 거부 |
| dtype 확인 | INVALID_DTYPE | uint8/uint16이 아니면 거부 |

### 기술 노트
- 대용량 볼륨 전송 시 chunked transfer encoding 사용
- 전송 중 연결 끊김 대응: 임시 파일에 먼저 쓰고, 완료 후 rename (atomic write)
- 원본 inference 결과와 편집본을 구분하기 위해 metadata.json의 `edited` 필드 사용
