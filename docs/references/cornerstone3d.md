# Cornerstone3D 참고 자료

## 이 문서의 목적
Cornerstone3D는 이 프로젝트의 Frontend 핵심 라이브러리이다.
에이전트가 뷰어, 세그멘테이션, 편집 기능을 구현할 때 참고해야 할
핵심 개념과 API 사용법을 정리한다.

---

## Cornerstone3D란?

의료영상(DICOM, NIfTI 등)을 웹 브라우저에서 표시하고 조작하기 위한
JavaScript/TypeScript 라이브러리이다. WebGL2를 사용하여 GPU 가속 렌더링을 수행한다.

**주요 패키지**:
- `@cornerstonejs/core` — 렌더링 엔진, Viewport, Volume 관리
- `@cornerstonejs/tools` — 윈도우/레벨, 세그멘테이션, 브러시 등 도구
- `@cornerstonejs/streaming-image-volume-loader` — 볼륨 데이터 로더

**공식 문서**: https://www.cornerstonejs.org/docs/
**GitHub**: https://github.com/cornerstonejs/cornerstone3D

---

## 핵심 개념

### RenderingEngine
모든 Viewport를 관리하는 최상위 객체이다. 앱에서 하나만 생성한다.

```typescript
import { RenderingEngine } from '@cornerstonejs/core';
const renderingEngine = new RenderingEngine('myRenderingEngine');
```

### Viewport 종류
| 종류 | 용도 | 우리 프로젝트에서 |
|------|------|------------------|
| StackViewport | 2D 슬라이스 뷰 (전통적) | 사용하지 않음 |
| VolumeViewport | 3D 볼륨 렌더링 | 4번째 패널 (3D 뷰) |
| VolumeViewport (ORTHOGRAPHIC) | 볼륨 기반 2D 슬라이스 | Axial, Coronal, Sagittal 패널 ✓ |

### Volume
3D 볼륨 데이터를 표현하는 객체이다.
우리는 Backend에서 받은 raw bytes를 Volume으로 변환한다.

```typescript
// 볼륨 생성 (개념적 흐름)
const volume = await volumeLoader.createAndCacheVolume(volumeId, {
  imageIds: [...],  // 또는 raw data 직접 주입
});
```

### Segmentation
세그멘테이션 데이터를 관리하는 별도 모듈이다.
`labelmap` 타입을 사용한다 (각 복셀에 정수 레이블).

---

## 초기화 순서 (매우 중요)

Cornerstone3D는 초기화 순서가 엄격하다. 순서를 어기면 에러가 발생한다.

```typescript
// 1. Core 초기화
import { init as csInit } from '@cornerstonejs/core';
await csInit();

// 2. Tools 초기화
import { init as csToolsInit } from '@cornerstonejs/tools';
csToolsInit();

// 3. RenderingEngine 생성
const renderingEngine = new RenderingEngine('viewer');

// 4. Viewport 설정 (DOM element가 존재해야 함)
renderingEngine.setViewports([
  {
    viewportId: 'axial',
    type: ViewportType.STACK,  // 또는 ViewportType.ORTHOGRAPHIC
    element: document.getElementById('axial-container'),
  },
  // ...
]);

// 5. 볼륨 로딩 및 뷰포트에 연결
const volume = await volumeLoader.createAndCacheVolume(volumeId);
volume.load();
await setVolumesForViewports(renderingEngine, [
  { volumeId, viewportId: 'axial' },
  // ...
]);
```

---

## 2D 슬라이스 뷰어 구현 참고

### StackViewport vs VolumeViewport for 2D

두 가지 방식이 있다:
1. **StackViewport**: 개별 슬라이스 이미지를 스택으로 관리. 전통적인 방식.
2. **VolumeViewport (ORTHOGRAPHIC)**: 3D 볼륨을 잘라서 2D로 표시. MPR 지원.

**우리 프로젝트는 VolumeViewport(ORTHOGRAPHIC)를 사용한다.**
이유: 세 방향(Axial/Coronal/Sagittal)의 크로스헤어 동기화와
세그멘테이션 오버레이가 VolumeViewport에서 더 자연스럽게 동작한다.

### 커스텀 볼륨 로더

Backend에서 raw bytes를 받아 Cornerstone3D Volume으로 변환하는
커스텀 로더를 작성해야 한다.

```typescript
// 커스텀 볼륨 로더 (개념적 구조)
function createVolumeFromRawBytes(
  arrayBuffer: ArrayBuffer,
  shape: [number, number, number],
  spacing: [number, number, number],
  direction: number[],  // affine에서 추출
  origin: number[],     // affine에서 추출
): IVolume {
  const scalarData = new Float32Array(arrayBuffer);
  // Cornerstone3D Volume 객체 생성
  // dimensions, spacing, direction, origin 설정
  // scalarData 주입
}
```

**주의**: Cornerstone3D의 내부 좌표계(LPS)와 우리 데이터(RAS)의
변환이 필요할 수 있다. nibabel의 `as_closest_canonical`이
RAS+로 변환해주지만, Cornerstone3D가 기대하는 direction matrix를
정확히 설정해야 영상이 올바르게 표시된다.

---

## 세그멘테이션 구현 참고

### Segmentation 등록 흐름

```typescript
import { segmentation } from '@cornerstonejs/tools';

// 1. 세그멘테이션 데이터 등록
segmentation.addSegmentations([{
  segmentationId: 'seg-001',
  representation: {
    type: csToolsEnums.SegmentationRepresentations.Labelmap,
    data: {
      volumeId: segVolumeId,  // 세그멘테이션 볼륨의 ID
    },
  },
}]);

// 2. Viewport에 세그멘테이션 표시
await segmentation.addSegmentationRepresentations(
  toolGroupId,
  [{
    segmentationId: 'seg-001',
    type: csToolsEnums.SegmentationRepresentations.Labelmap,
  }]
);

// 3. 컬러맵 설정
segmentation.config.color.setColorForSegmentIndex(
  'seg-001',
  1,  // segment index (class_id)
  [255, 0, 0, 128]  // RGBA
);
```

### 세그멘테이션 표시/숨김

```typescript
// 특정 세그먼트(클래스) 표시/숨김
segmentation.config.visibility.setSegmentVisibility(
  toolGroupId,
  'seg-001',
  segmentIndex,  // class_id
  isVisible      // true/false
);
```

---

## 브러시/편집 도구 참고

### BrushTool 사용

```typescript
import { BrushTool, SegmentationDisplayTool } from '@cornerstonejs/tools';

// 1. 도구 등록
cornerstoneTools.addTool(BrushTool);
cornerstoneTools.addTool(SegmentationDisplayTool);

// 2. ToolGroup에 추가
const toolGroup = ToolGroupManager.createToolGroup('editGroup');
toolGroup.addTool(BrushTool.toolName);
toolGroup.addTool(SegmentationDisplayTool.toolName);

// 3. 브러시 활성화
toolGroup.setToolActive(BrushTool.toolName, {
  bindings: [{ mouseButton: MouseBindings.Primary }],
});

// 4. 브러시 설정
segmentation.config.setBrushSizeForToolGroup(toolGroupId, brushSize);
segmentation.activeSegmentation.setActiveSegmentIndex(
  toolGroupId,
  segmentIndex  // 칠할 class_id
);
```

### 지우개 구현 방법

Cornerstone3D에는 별도 EraserTool이 없을 수 있다.
대안: BrushTool의 activeSegmentIndex를 0(background)으로 설정하면
지우개와 동일한 효과.

```typescript
// 지우개 = 브러시 + activeSegmentIndex=0
function activateEraser() {
  segmentation.activeSegmentation.setActiveSegmentIndex(toolGroupId, 0);
  toolGroup.setToolActive(BrushTool.toolName, {
    bindings: [{ mouseButton: MouseBindings.Primary }],
  });
}
```

---

## 알려진 함정과 해결책

### 1. WASM 로더 초기화 실패
Cornerstone3D는 내부적으로 WASM 파일을 사용한다.
Vite에서 WASM을 올바르게 로드하려면 설정이 필요하다.

```typescript
// vite.config.ts
export default defineConfig({
  optimizeDeps: {
    exclude: ['@cornerstonejs/core', '@cornerstonejs/tools'],
  },
});
```

### 2. Viewport element 크기가 0인 경우
Viewport를 생성할 때 DOM element의 크기가 0이면 렌더링이 안 된다.
React에서 useEffect + ref를 사용하여 element가 마운트된 후 초기화해야 한다.

### 3. 메모리 누수
Volume을 교체할 때 이전 Volume을 명시적으로 해제해야 한다.
```typescript
cache.removeVolumeLoadObject(oldVolumeId);
```

### 4. 볼륨 방향 뒤집힘
Backend에서 보낸 데이터의 array 순서(C-contiguous)와
Cornerstone3D가 기대하는 순서가 다를 수 있다.
shape를 [z, y, x] → [x, y, z]로 변환해야 할 수 있다.
**반드시 작은 테스트 볼륨으로 방향을 먼저 검증한다.**

---

## 참고 자료 링크

- Cornerstone3D 공식 예제: https://www.cornerstonejs.org/docs/examples
- OHIF Viewer (참고 구현): https://github.com/OHIF/Viewers
- Cornerstone3D 세그멘테이션 예제: cornerstonejs.org → Examples → Segmentation
- VTK.js (3D 렌더링 내부): https://kitware.github.io/vtk-js/
