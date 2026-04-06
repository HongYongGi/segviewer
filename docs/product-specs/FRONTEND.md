# FRONTEND.md — Frontend 코딩 가이드

## 이 문서의 목적
에이전트가 Frontend 코드를 작성할 때 따라야 할 규칙과 패턴을 정의한다.

---

## 프로젝트 구조

```
frontend/src/
├── App.tsx                    # 메인 레이아웃
├── main.tsx                   # 엔트리포인트
├── api/
│   ├── client.ts              # axios 인스턴스 설정
│   ├── images.ts              # /api/images/* 호출 함수
│   ├── inference.ts           # /api/inference/* 호출 함수
│   ├── models.ts              # /api/models/* 호출 함수
│   └── segments.ts            # /api/segments/* 호출 함수
├── components/
│   ├── Layout.tsx             # 전체 레이아웃 (툴바 + 뷰어 + 사이드바)
│   ├── Toolbar.tsx            # 상단 툴바 (업로드, 모델 선택, 실행 버튼)
│   ├── Sidebar.tsx            # 우측 사이드바 (레이블 패널 + 메타데이터)
│   ├── LabelPanel.tsx         # 세그멘테이션 레이블 목록
│   ├── MetadataPanel.tsx      # 영상 메타데이터 표시
│   ├── ProgressBar.tsx        # Inference 진행률 바
│   └── ToolPanel.tsx          # 브러시/지우개 도구 패널
├── viewers/
│   ├── ViewerGrid.tsx         # 2x2 뷰포트 그리드 컨테이너
│   ├── SliceViewport.tsx      # 단일 2D 슬라이스 뷰포트
│   ├── VolumeViewport.tsx     # 3D 볼륨 렌더링 뷰포트
│   └── cornerstoneSetup.ts   # Cornerstone3D 초기화 유틸
├── editors/
│   ├── BrushEditor.ts         # 브러시 도구 로직
│   ├── EraserEditor.ts        # 지우개 도구 로직
│   └── UndoManager.ts         # Undo/Redo 스택 관리
├── stores/
│   ├── imageStore.ts          # 현재 영상 상태 (Zustand)
│   ├── modelStore.ts          # 모델 목록/선택 상태
│   ├── segmentationStore.ts   # 세그멘테이션 상태
│   ├── toolStore.ts           # 현재 도구 상태 (brush/eraser/navigate)
│   └── inferenceStore.ts      # inference 진행 상태
├── types/
│   ├── image.ts               # ImageMetadata, ImageResponse 등
│   ├── model.ts               # ModelConfig, ModelList 등
│   ├── segmentation.ts        # SegmentationResult, LabelInfo 등
│   └── inference.ts           # InferenceJob, InferenceStatus 등
└── utils/
    ├── arrayBufferUtils.ts    # ArrayBuffer ↔ TypedArray 변환
    ├── colormap.ts            # 세그멘테이션 컬러맵 생성
    └── formatters.ts          # 숫자 포맷팅, 파일 크기 표시 등
```

---

## 코딩 규칙

### TypeScript 필수
- 모든 파일은 `.tsx` 또는 `.ts`
- `any` 타입 사용 금지 (unknown + 타입 가드 사용)
- API 응답은 반드시 타입 정의

### 컴포넌트 규칙
- 함수형 컴포넌트만 사용 (클래스 컴포넌트 금지)
- Props 타입을 interface로 정의
- 복잡한 로직은 커스텀 Hook으로 분리

### 상태 관리 (Zustand)
```typescript
// stores/imageStore.ts 예시
import { create } from 'zustand';

interface ImageState {
  imageId: string | null;
  metadata: ImageMetadata | null;
  isLoading: boolean;
  setImage: (id: string, meta: ImageMetadata) => void;
  clearImage: () => void;
}

export const useImageStore = create<ImageState>((set) => ({
  imageId: null,
  metadata: null,
  isLoading: false,
  setImage: (id, meta) => set({ imageId: id, metadata: meta }),
  clearImage: () => set({ imageId: null, metadata: null }),
}));
```

### API 호출 패턴
```typescript
// api/client.ts
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 300000,  // 5분 (대용량 업로드/inference 고려)
});

// api/images.ts
export async function uploadImage(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await apiClient.post<UploadResponse>(
    '/images/upload',
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
  return data;
}

export async function getVolume(imageId: string): Promise<{
  buffer: ArrayBuffer;
  shape: number[];
  dtype: string;
  spacing: number[];
}> {
  const response = await apiClient.get(`/images/${imageId}/volume`, {
    responseType: 'arraybuffer',
  });
  return {
    buffer: response.data,
    shape: response.headers['x-image-shape'].split(',').map(Number),
    dtype: response.headers['x-image-dtype'],
    spacing: response.headers['x-image-spacing'].split(',').map(Number),
  };
}
```

### 에러 처리
```typescript
// 전역 에러 핸들러 (api/client.ts)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data?.error) {
      // Backend에서 보낸 구조화된 에러
      const { error: code, message } = error.response.data;
      // 토스트 메시지 또는 에러 상태 업데이트
      console.error(`[${code}] ${message}`);
    }
    return Promise.reject(error);
  }
);
```

---

## 스타일링 규칙

### Tailwind CSS (선호)
- 클래스명 기반 스타일링 (별도 CSS 파일 최소화)
- 컴포넌트별 CSS 모듈은 불필요한 복잡성

### 레이아웃
- 전체 레이아웃: CSS Grid 사용
- 뷰포트 그리드: `grid-template-columns: 1fr 1fr` + `grid-template-rows: 1fr 1fr`
- 사이드바: 고정 너비 300px, 접기/펼치기 가능
- 최소 지원 해상도: 1280 × 720

### 색상 (다크 테마 기본)
의료영상 뷰어는 전통적으로 다크 테마를 사용한다 (눈의 피로 감소).

| 용도 | 색상 |
|------|------|
| 배경 | #1a1a2e |
| 뷰포트 배경 | #000000 |
| 패널 배경 | #16213e |
| 텍스트 | #e0e0e0 |
| 강조 | #0f3460 |
| 버튼 (Primary) | #533483 |
| 에러 | #e94560 |
| 성공 | #4ecca3 |

---

## Cornerstone3D 통합 주의사항

### React와 Cornerstone3D의 충돌
Cornerstone3D는 DOM element를 직접 조작한다.
React의 가상 DOM과 충돌할 수 있으므로:

1. 뷰포트 DOM element는 `useRef`로 참조
2. Cornerstone3D 초기화는 `useEffect`에서 수행
3. React 리렌더링 시 Cornerstone3D viewport를 재생성하지 않도록 주의
4. cleanup 함수에서 반드시 viewport 해제

```typescript
// ViewportComponent.tsx (패턴)
const elementRef = useRef<HTMLDivElement>(null);

useEffect(() => {
  if (!elementRef.current) return;
  
  // Cornerstone3D viewport 초기화
  const viewport = renderingEngine.getViewport(viewportId);
  // ...
  
  return () => {
    // cleanup: viewport 해제
    renderingEngine.disableElement(viewportId);
  };
}, []);

return <div ref={elementRef} style={{ width: '100%', height: '100%' }} />;
```
