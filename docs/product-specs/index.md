# Product Specs Index

## 프로젝트 목표
연구실 팀원이 브라우저에서 nnUNetv2 CT 다중 클래스 세그멘테이션을
실행 · 시각화 · 편집할 수 있는 내부용 웹 도구.

## 사용자 정의

### 주 사용자: 연구실 팀원 (의료영상 분석 연구자)
- **기술 수준**: Python/딥러닝에 익숙하지만 웹 개발은 비전문가
- **사용 빈도**: 매일 또는 주 3-4회
- **일반적인 워크플로**: 모델 학습 완료 → 결과 확인 → 세그멘테이션 품질 검수 → 필요 시 수정
- **사용 환경**: 연구실 내부 네트워크, GPU 서버 접속, Chrome/Firefox 브라우저
- **인원**: 5-15명 수준 (동시 접속은 1-3명 예상)

### 사용자가 기대하는 것
- 복잡한 설치 없이 브라우저만 열면 바로 사용 가능
- nnUNet inference를 커맨드라인 대신 GUI로 실행
- ITK-SNAP 수준의 시각화 품질 (2D 슬라이스 + 오버레이)
- 간단한 세그멘테이션 수정 후 바로 NIfTI로 저장

### 사용자가 기대하지 않는 것 (범위 밖)
- DICOM 뷰어 수준의 완전한 PACS 시스템
- nnUNet 학습(training) 기능
- 다중 사용자 동시 편집 (Google Docs 스타일)
- 외부 인터넷 접속 필요 기능

---

## 기능 목록 및 우선순위

| 우선순위 | 기능 | 스펙 문서 | 상태 |
|---------|------|----------|------|
| **P0** | NIfTI 업로드 + 메타데이터 표시 | image-upload-and-view.md §1 | 미구현 |
| **P0** | 2D 슬라이스 뷰어 (Axial/Coronal/Sagittal) | image-upload-and-view.md §2 | 미구현 |
| **P0** | 윈도우/레벨 조절 (CT 프리셋) | image-upload-and-view.md §3 | 미구현 |
| **P0** | nnUNet 모델 목록 조회 | inference-pipeline.md §1 | 미구현 |
| **P0** | nnUNet inference 실행 + 진행률 표시 | inference-pipeline.md §2 | 미구현 |
| **P0** | 세그멘테이션 오버레이 표시 (컬러맵) | segmentation-overlay.md §1 | 미구현 |
| **P0** | 클래스별 표시/숨김 토글 | segmentation-overlay.md §2 | 미구현 |
| **P1** | 3D 볼륨 렌더링 | image-upload-and-view.md §4 | 미구현 |
| **P1** | 세그멘테이션 3D 표면 렌더링 | segmentation-overlay.md §3 | 미구현 |
| **P1** | 브러시/지우개 편집 도구 | segmentation-editor.md §1 | 미구현 |
| **P1** | 편집 Undo/Redo | segmentation-editor.md §2 | 미구현 |
| **P1** | 편집 결과 저장 (NIfTI) | segmentation-editor.md §3 | 미구현 |
| **P2** | 세그멘테이션 결과 다운로드 | segmentation-overlay.md §4 | 미구현 |
| **P2** | 모델별 성능 메모/태그 | model-management.md §1 | 미구현 |
| **P2** | Inference 히스토리 목록 | inference-pipeline.md §3 | 미구현 |

## 우선순위 정의
- **P0 (Must Have)**: 이것 없이는 앱이 의미가 없음. MVP에 반드시 포함.
- **P1 (Should Have)**: 핵심 사용성을 크게 높이는 기능. MVP 직후 구현.
- **P2 (Nice to Have)**: 있으면 편하지만 없어도 사용 가능. 여유 있을 때 구현.

---

## 공통 규칙

### 에러 응답 포맷 (모든 API 공통)
```json
{
  "error": "INVALID_NIFTI_FORMAT",
  "message": "업로드된 파일이 유효한 NIfTI 형식이 아닙니다.",
  "detail": {
    "filename": "scan.nii.gz",
    "reason": "nibabel이 파일을 로드할 수 없음"
  }
}
```

### 에러 코드 목록
| 코드 | HTTP 상태 | 설명 |
|------|----------|------|
| INVALID_NIFTI_FORMAT | 400 | NIfTI로 파싱할 수 없는 파일 |
| NOT_3D_VOLUME | 400 | 3D가 아닌 영상 (2D 또는 4D) |
| FILE_TOO_LARGE | 413 | 파일 크기 초과 (기본 500MB) |
| IMAGE_NOT_FOUND | 404 | 존재하지 않는 image_id |
| MODEL_NOT_FOUND | 404 | 존재하지 않는 모델 조합 |
| INFERENCE_ALREADY_RUNNING | 409 | 이미 inference가 실행 중 |
| INFERENCE_FAILED | 500 | nnUNet inference 실행 중 오류 |
| GPU_OUT_OF_MEMORY | 507 | GPU 메모리 부족 |
| RESULT_NOT_FOUND | 404 | 존재하지 않는 세그멘테이션 결과 |
| SHAPE_MISMATCH | 400 | 편집된 세그멘테이션과 원본 shape 불일치 |
