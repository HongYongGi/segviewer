# Frontend 기술 스택 결정

## 핵심 질문
> 왜 처음에 원했던 Streamlit 대신 FastAPI + React를 선택했는가?

## 결론
**Streamlit은 3D 볼륨 렌더링과 픽셀 단위 브러시 편집을 지원할 수 없다.
이 두 기능이 필수이므로 FastAPI(Backend) + React(Frontend)로 전환했다.**

---

## 배경: Streamlit이 매력적이었던 이유

Streamlit은 연구자에게 사실상 가장 친숙한 웹 프레임워크이다.
Python만 알면 되고, HTML/CSS/JavaScript를 전혀 몰라도 UI를 만들 수 있다.

```python
# Streamlit으로 만든 간단한 영상 뷰어 (실제로 동작하는 코드)
import streamlit as st
import nibabel as nib
import matplotlib.pyplot as plt

uploaded = st.file_uploader("NIfTI 업로드", type=["nii", "nii.gz"])
if uploaded:
    img = nib.load(uploaded)
    data = img.get_fdata()
    slice_idx = st.slider("Slice", 0, data.shape[2]-1)
    fig, ax = plt.subplots()
    ax.imshow(data[:,:,slice_idx], cmap='gray')
    st.pyplot(fig)
```

이 코드만으로 파일 업로드 + 슬라이스 뷰어가 동작한다.
10줄도 안 되는 코드로 프로토타입을 만들 수 있다는 것이 Streamlit의 장점이다.

---

## Streamlit의 한계: 왜 전환이 필요했는가

### 한계 1: 3D 볼륨 렌더링

Streamlit에서 3D 볼륨 렌더링을 하려면 두 가지 방법이 있다:

**방법 a) matplotlib의 3D plot**:
- 실시간 회전이 불가능 (정적 이미지만 생성)
- 볼륨 렌더링(ray casting)을 지원하지 않음
- 의료영상 수준의 품질과는 거리가 멈

**방법 b) Streamlit Custom Component**:
- JavaScript로 3D 뷰어를 만들어서 Streamlit에 임베드하는 방식
- 기술적으로 가능하지만, 결국 React 컴포넌트를 만드는 것과 동일한 작업
- Streamlit ↔ Custom Component 간 대용량 데이터(3D 볼륨) 전송이 매우 비효율적
  (JSON 직렬화 → Base64 인코딩 → 재디코딩 과정이 필요)
- Streamlit의 "스크립트 재실행" 특성 때문에 3D 뷰어 상태가 리셋될 수 있음

### 한계 2: 브러시/지우개 편집

Streamlit은 근본적으로 "서버에서 렌더링 → 클라이언트에서 표시"하는 구조이다.
사용자의 마우스 움직임 하나하나를 서버에 전송하고,
서버가 결과를 렌더링해서 다시 보내는 방식은 실시간 브러시 편집에 적합하지 않다.

- **브러시 드래그**: 마우스가 움직일 때마다 서버 왕복이 필요 → 지연 발생
- **실시간 커서**: 브러시 크기/색상에 따른 커서 미리보기가 어려움
- **픽셀 정밀도**: matplotlib 기반 렌더링은 픽셀 단위 정확한 편집이 어려움

### 한계 3: 의료영상 전문 기능

- **크로스헤어 동기화**: 세 뷰포트 간 실시간 연동이 Streamlit에서는 복잡
- **윈도우/레벨 드래그**: 마우스 드래그로 실시간 밝기 조절은 서버 왕복 지연으로 불가
- **대용량 데이터**: CT 볼륨(128MB+)을 Streamlit의 세션 스테이트로 관리하면 메모리 과다 사용

---

## FastAPI + React를 선택한 이유

### FastAPI (Backend)

**왜 FastAPI인가 (Django, Flask 대비)**:

| 기준 | FastAPI | Flask | Django |
|------|---------|-------|--------|
| 비동기 지원 | ✓ 네이티브 (async/await) | △ 외부 라이브러리 필요 | △ 3.1+에서 지원, 불완전 |
| 타입 검증 | ✓ Pydantic 내장 | ✗ 수동 | △ serializer |
| API 문서 자동 생성 | ✓ Swagger UI 자동 | ✗ 수동 | △ DRF 필요 |
| 학습 곡선 | ✓ Python 함수 스타일 | ✓ 간단 | ✗ 무거움 |
| 바이너리 응답 | ✓ Response(content=bytes) | ✓ 가능 | △ 불편 |
| WebSocket | ✓ 내장 | △ flask-socketio | △ channels |

FastAPI의 결정적 장점:
1. **비동기 지원**: inference는 수십 초 걸리는데, 이 동안 다른 API 호출이 블로킹되면 안 된다.
   FastAPI의 async/await로 자연스럽게 해결.
2. **바이너리 데이터 전송**: 3D 볼륨을 raw bytes로 전송해야 하는데,
   FastAPI의 `Response(content=bytes)`가 가장 깔끔하다.
3. **Swagger UI**: API를 만들면 자동으로 문서가 생긴다.
   Frontend 개발자(또는 에이전트)가 바로 테스트할 수 있다.

### React + TypeScript (Frontend)

**왜 React인가 (Vue, Svelte, Vanilla JS 대비)**:

| 기준 | React | Vue | Svelte |
|------|-------|-----|--------|
| Cornerstone3D 지원 | ✓ 공식 예제 React 기반 | △ 커뮤니티 수준 | ✗ 거의 없음 |
| 의료영상 커뮤니티 | ✓ OHIF Viewer가 React | △ 일부 프로젝트 | ✗ 매우 적음 |
| 생태계 크기 | ✓ 가장 큼 | ✓ 큼 | △ 성장 중 |
| 에이전트 코드 생성 | ✓ 학습 데이터 풍부 | ✓ 양호 | △ 적음 |

React의 결정적 장점:
1. **Cornerstone3D와의 호환**: Cornerstone3D (의료영상 뷰어 라이브러리)의
   공식 예제와 문서가 모두 React 기반이다.
   다른 프레임워크를 쓰면 통합 과정에서 추가 작업이 크게 늘어난다.
2. **OHIF Viewer 참고**: 오픈소스 의료영상 뷰어 OHIF가 React로 만들어져 있어,
   구현 참고 자료가 풍부하다.
3. **에이전트 친화적**: AI 코딩 에이전트가 React 코드를 생성하는 데
   가장 많은 학습 데이터가 있으므로 품질이 높을 가능성이 크다.

### TypeScript
- NIfTI 메타데이터(shape, spacing, affine)를 다룰 때 타입 안전성이 중요
- ArrayBuffer → Float32Array 변환 같은 바이너리 처리에서 타입 실수 방지
- Cornerstone3D API가 TypeScript로 작성되어 있어 타입 추론이 잘 됨

---

## 트레이드오프 인정

### 우리가 잃는 것
1. **Python 단일 스택의 단순함**: Backend는 Python, Frontend는 TypeScript로 이원화
2. **빠른 프로토타이핑**: Streamlit 10줄 vs React 100줄+
3. **연구자 직접 수정 용이성**: Python만 아는 연구원이 Frontend를 수정하기 어려움

### 이 손실을 감수하는 이유
- 3D 렌더링과 브러시 편집이 **핵심 요구사항**이므로, 이를 포기할 수 없음
- 에이전트(AI)가 코드를 생성하므로, 연구자가 직접 수정할 필요가 줄어듦
- Docker Compose로 빌드/배포를 자동화하면 이원화의 운영 부담이 최소화됨

### Streamlit이 적합한 경우 (우리에겐 아닌 이유도)
만약 요구사항이 "2D 슬라이스 뷰어 + inference 실행만" 이었다면
Streamlit이 최적이었을 것이다. 3D 렌더링과 브러시 편집이 빠졌다면
10배 적은 코드로 동일한 기능을 구현할 수 있었다.
이 판단을 기록해두는 이유는, 나중에 "왜 Streamlit 안 썼어요?"라는
질문에 답하기 위함이다.

---

## 핵심 라이브러리 선택 근거

### Cornerstone3D (의료영상 뷰어)

**후보들**:
| 라이브러리 | 설명 | 장점 | 단점 |
|-----------|------|------|------|
| Cornerstone3D | Cornerstone.js의 차세대 버전 | 2D+3D 통합, 세그멘테이션 도구 내장 | 학습 곡선 높음 |
| AMI (AMI Medical Imaging) | Three.js 기반 의료영상 뷰어 | 구현이 간단 | 세그멘테이션 편집 도구 없음 |
| OHIF Viewer 임베드 | 오픈소스 PACS 뷰어 | 기능 완성도 높음 | 너무 무겁고 커스터마이징 어려움 |
| Niivue | NIfTI 전용 뷰어 | NIfTI 최적화, 가벼움 | 세그멘테이션 편집 도구 부족 |
| 직접 구현 (Three.js) | Three.js로 처음부터 | 완전한 제어 | 개발 시간 과다 |

**Cornerstone3D를 선택한 이유**:
1. **세그멘테이션 도구 내장**: BrushTool, EraserTool, ScissorsTool 등이
   라이브러리에 포함되어 있어 별도 구현이 불필요
2. **2D + 3D 통합**: StackViewport(2D)와 VolumeViewport(3D)를
   하나의 라이브러리에서 관리
3. **의료영상 표준 준수**: DICOM, NIfTI 좌표계, 윈도우/레벨 등
   의료영상 고유 기능을 올바르게 처리
4. **활발한 개발**: Microsoft, MGH, BWH 등이 후원하는 활발한 프로젝트

### Zustand (상태관리)

**왜 Redux가 아닌가**:
- Redux: 보일러플레이트가 많고, action/reducer/selector를 일일이 정의해야 함
- Zustand: 함수 하나로 스토어 생성, 타입 추론 우수, 번들 크기 작음
- 우리 앱의 전역 상태는 복잡하지 않으므로 (현재 영상, 모델, 세그멘테이션, 도구 상태)
  Zustand로 충분함

### Vite (빌드 도구)

**왜 CRA(Create React App)가 아닌가**:
- CRA는 더 이상 유지보수되지 않음 (deprecated)
- Vite: 빌드 속도 10배 이상 빠름, HMR(Hot Module Replacement) 즉각 반영
- Cornerstone3D가 WASM 파일을 사용하는데, Vite의 WASM 지원이 좋음
