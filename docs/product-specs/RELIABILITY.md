# RELIABILITY.md — 안정성 및 에러 처리 가이드

## 원칙
"에러가 발생해도 앱이 죽지 않고, 사용자가 다음 행동을 알 수 있어야 한다."

---

## Backend 안정성 규칙

### 1. 모든 API 엔드포인트는 try-except로 감싼다
```python
@router.post("/upload")
async def upload_image(file: UploadFile):
    try:
        result = await image_service.process_upload(file)
        return result
    except InvalidNiftiError as e:
        raise HTTPException(400, detail={"error": "INVALID_NIFTI_FORMAT", "message": str(e)})
    except FileTooLargeError as e:
        raise HTTPException(413, detail={"error": "FILE_TOO_LARGE", "message": str(e)})
    except Exception as e:
        logger.exception("Unexpected error in upload")
        raise HTTPException(500, detail={"error": "INTERNAL_ERROR", "message": "서버 내부 오류가 발생했습니다."})
```

### 2. Inference 실패 시 GPU 상태를 복구한다
inference 도중 어떤 에러가 발생하든, GPU 메모리를 정리해야 한다.
정리하지 않으면 다음 inference도 실패한다.

```python
try:
    result = predictor.predict_from_files(...)
except Exception:
    torch.cuda.empty_cache()
    gc.collect()
    raise
```

### 3. 파일 저장은 atomic write를 사용한다
세그멘테이션 저장 중 서버가 죽으면 파일이 깨질 수 있다.
임시 파일에 먼저 쓰고, 완료 후 rename한다.

```python
import tempfile, os

def save_nifti_atomic(data, affine, path):
    dir_name = os.path.dirname(path)
    with tempfile.NamedTemporaryFile(dir=dir_name, suffix='.nii.gz', delete=False) as tmp:
        nib.save(nib.Nifti1Image(data, affine), tmp.name)
        os.rename(tmp.name, path)  # atomic on same filesystem
```

### 4. 업로드 디렉토리가 없으면 자동 생성한다
앱 시작 시 uploads/, results/ 디렉토리 존재를 확인하고 없으면 생성한다.

---

## Frontend 안정성 규칙

### 1. React Error Boundary 설정
뷰포트 컴포넌트가 크래시해도 전체 앱이 죽지 않도록 Error Boundary로 감싼다.

### 2. 네트워크 에러 시 재시도 안내
- 업로드 실패: "업로드에 실패했습니다. 다시 시도해주세요." + 재시도 버튼
- inference 실패: 에러 코드별 구체적 안내 (GPU OOM → fold 줄이기 제안)
- 볼륨 로딩 실패: "영상 로딩에 실패했습니다. 페이지를 새로고침해주세요."

### 3. 대용량 데이터 로딩 시 타임아웃 설정
- axios timeout: 300초 (5분) — 500MB 파일 업로드 고려
- WebSocket: 30초 ping 간격, 연결 끊김 시 자동 재연결 (3회 시도)

### 4. beforeunload 경고
미저장 편집이 있을 때 탭을 닫으려고 하면 경고를 표시한다.

---

## 로깅 규칙

### Backend 로깅
```python
import logging
logger = logging.getLogger("nnunet-viewer")

# 로그 레벨별 용도
logger.debug("NIfTI loaded: shape=%s, spacing=%s", shape, spacing)
logger.info("Inference started: job_id=%s, model=%s", job_id, model)
logger.warning("GPU memory low: free=%dMB", free_mb)
logger.error("Inference failed: %s", error_message)
logger.exception("Unexpected error")  # 스택 트레이스 포함
```

### 로그 레벨 설정
환경변수 `LOG_LEVEL`로 설정 (기본: INFO)
- DEBUG: 개발 중 상세 로그
- INFO: 일반 운영 (권장)
- WARNING: 문제 가능성만
- ERROR: 오류만

---

## 장애 시나리오 대응

| 시나리오 | 증상 | 대응 |
|---------|------|------|
| GPU CUDA 에러 | inference 실패 | empty_cache + 에러 메시지 |
| 디스크 꽉 참 | 저장 실패 | 에러 메시지 + uploads/ 정리 안내 |
| nnUNet_results 경로 잘못됨 | 앱 시작 실패 | 시작 시 경로 검증 + 명확한 에러 |
| Backend 서버 다운 | Frontend 빈 화면 | "서버에 연결할 수 없습니다" 표시 |
| WebSocket 끊김 | 진행률 멈춤 | 자동 재연결 + polling 대체 |
| 브라우저 메모리 부족 | 탭 크래시 | 다운샘플링으로 볼륨 크기 줄이기 |
