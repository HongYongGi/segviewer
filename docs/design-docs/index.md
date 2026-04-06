# Design Docs Index

## 이 폴더의 목적
프로젝트에서 내린 주요 설계 결정과 그 근거를 기록한다.
"왜 이렇게 했는가?"에 대한 답을 찾을 수 있는 곳이다.

나중에 합류하는 연구실 멤버, 또는 코드를 수정해야 하는 에이전트가
"이거 왜 이렇게 되어 있지?"라는 질문에 빠르게 답을 찾을 수 있도록 작성한다.

## 설계 결정 목록

| 문서 | 핵심 질문 | 결론 요약 |
|------|----------|----------|
| core-beliefs.md | 이 프로젝트의 설계 철학은? | 단순함, 데이터 무결성, nnUNet 존중 |
| nnunet-integration.md | nnUNet을 어떻게 통합할 것인가? | Python API 직접 호출 (CLI 래핑 ✗) |
| frontend-stack.md | 왜 Streamlit이 아니라 FastAPI+React인가? | 3D 렌더링/브러시 편집은 Streamlit 한계 |
| data-transfer-strategy.md | NIfTI 데이터를 어떻게 Frontend에 전달? | Raw bytes + 커스텀 헤더 (JSON ✗) |
| gpu-memory-management.md | GPU 메모리를 어떻게 관리? | LRU 캐시 2개, 동시 1개 inference |

## 읽는 순서 추천
1. **core-beliefs.md** → 전체 방향 이해
2. **nnunet-integration.md** → 가장 중요한 기술 결정
3. 나머지는 관심 있는 주제부터
