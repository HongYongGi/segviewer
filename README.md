# SegViewer

nnU-Net 기반 CT 의료영상 세그멘테이션 뷰어 웹 애플리케이션.

## 기능

- NIfTI 파일 업로드 및 Axial/Sagittal/Coronal MPR 뷰어
- nnU-Net v2 자동 세그멘테이션 추론 (GPU 가속)
- 세그멘테이션 결과 오버레이 및 편집 (브러시/지우개)
- 3D 메시 생성 및 다운로드
- 실시간 추론 진행률 (WebSocket)

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | React 19, TypeScript, Cornerstone.js v4, Zustand, Tailwind CSS |
| Backend | FastAPI, nnU-Net v2, PyTorch, nibabel |
| Infra | Docker Compose, Nginx, CUDA |

## 빠른 시작

### Docker (권장)

```bash
cp .env.example .env
# .env에서 NNUNET_RESULTS_PATH 설정
docker-compose up --build
```

브라우저에서 `http://localhost:3000` 접속.

### 로컬 개발

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## 프로젝트 구조

```
segviewer/
├── backend/
│   ├── app/
│   │   ├── routers/      # API 엔드포인트
│   │   ├── services/     # 비즈니스 로직
│   │   ├── dependencies.py  # DI 설정
│   │   └── config.py     # 환경변수
│   └── tests/            # pytest 테스트
├── frontend/
│   ├── src/
│   │   ├── viewers/      # Cornerstone.js 뷰어
│   │   ├── components/   # UI 컴포넌트
│   │   ├── stores/       # Zustand 상태 관리
│   │   └── api/          # HTTP 클라이언트
│   └── package.json
├── docs/                 # 설계 문서
└── docker-compose.yml
```

## 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `NNUNET_RESULTS_PATH` | nnU-Net 학습 결과 경로 | (필수) |
| `UPLOAD_DIR` | 업로드 디렉토리 | `./uploads` |
| `RESULTS_DIR` | 추론 결과 디렉토리 | `./results` |
| `GPU_DEVICE_INDEX` | GPU 디바이스 번호 | `0` |
| `MAX_CACHED_MODELS` | 최대 캐시 모델 수 | `2` |
