# Phase 0: Foundation — 프로젝트 기반 세팅

## 목표
코드를 한 줄도 안 짠 상태에서 `docker-compose up` 한 번에
Backend + Frontend가 뜨고, 브라우저에서 빈 페이지가 보이는 상태까지.

## 왜 이 단계가 먼저인가
Phase 1에서 기능을 만들려면 "코드를 수정하고 → 결과를 확인하는" 루프가
빠르게 돌아야 한다. 프로젝트 구조, Docker 설정, 개발 환경이 없으면
기능 구현 자체를 시작할 수 없다.

## 예상 소요: 1~2일

---

## 작업 목록

### 0-1. 프로젝트 디렉토리 구조 생성
**목표**: AGENTS.md에 정의된 디렉토리 구조를 실제로 만든다.

```
project-root/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 앱 엔트리포인트
│   │   ├── config.py            # 설정 (환경변수 로딩)
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── images.py        # 빈 라우터 (placeholder)
│   │   │   ├── inference.py
│   │   │   ├── models.py
│   │   │   └── segments.py
│   │   ├── services/
│   │   │   └── __init__.py
│   │   └── utils/
│   │       └── __init__.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── (Vite + React + TypeScript 초기화)
│   ├── Dockerfile
│   └── ...
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

**완료 기준**: 모든 디렉토리와 __init__.py가 존재한다.

### 0-2. Backend 기본 세팅
**목표**: FastAPI가 실행되고 `/api/health` 엔드포인트가 응답한다.

**main.py 내용**:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="nnUNet Segmentation Viewer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 내부망 전용
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Image-Shape", "X-Image-Dtype", "X-Image-Spacing",
                    "X-Image-ByteOrder", "X-Image-Affine",
                    "X-Seg-Shape", "X-Seg-Dtype", "X-Seg-Num-Classes", "X-Seg-Labels",
                    "X-Slice-Shape", "X-Slice-Dtype",
                    "X-Mesh-Vertices-Count", "X-Mesh-Faces-Count", "X-Mesh-Format"],
)

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
```

**config.py 내용**:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 환경변수 이름 매핑:
    # - nnUNet 공식 환경변수는 "nnUNet_results" (대소문자 혼합)
    # - Pydantic Settings는 대소문자 무시(case_insensitive)이므로
    #   .env에 "nnUNet_results_path=/path" 또는 "NNUNET_RESULTS_PATH=/path"
    #   어느 형태든 아래 필드에 매핑됨
    # - 주의: 이 값은 nnUNet 공식 환경변수(nnUNet_results)와 별개이다.
    #   nnUNet 자체는 nnUNet_results를 직접 읽지만, 우리 앱은
    #   nnunet_results_path를 통해 경로를 관리한다.
    nnunet_results_path: str  # 필수: nnUNet_results 디렉토리 경로
    upload_dir: str = "./uploads"
    results_dir: str = "./results"
    max_upload_size_mb: int = 500
    max_cached_models: int = 2
    gpu_device_index: int = 0

    class Config:
        env_file = ".env"

settings = Settings()
```

**requirements.txt**:
```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic-settings>=2.0.0
nibabel>=5.0.0
numpy>=1.24.0
SimpleITK>=2.3.0
torch>=2.0.0
nnunetv2>=2.2.0
python-multipart>=0.0.6
websockets>=11.0
```

**완료 기준**: `uvicorn app.main:app --reload` 실행 후
`curl localhost:8000/api/health` → `{"status":"ok"}` 반환.

### 0-3. Frontend 기본 세팅
**목표**: Vite + React + TypeScript 프로젝트가 생성되고,
브라우저에서 빈 페이지(또는 "nnUNet Viewer" 제목)가 표시된다.

**실행 명령**:
```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install axios zustand
npm install @cornerstonejs/core @cornerstonejs/tools @cornerstonejs/streaming-image-volume-loader
npm install -D @types/node
```

**vite.config.ts 주의사항**:
- Cornerstone3D가 WASM 파일을 사용하므로 WASM 지원 설정 필요
- Backend API 프록시 설정: `/api` → `http://localhost:8000/api`

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
});
```

**완료 기준**: `npm run dev` 실행 후 `localhost:5173` 에서 페이지 표시.

### 0-4. Docker 설정
**목표**: `docker-compose up` 한 번에 Backend + Frontend가 실행된다.

**docker-compose.yml**:
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ${nnUNet_results:-./weights}:/data/nnUNet_results:ro
      - ./uploads:/app/uploads
      - ./results:/app/results
    environment:
      - nnunet_results_path=/data/nnUNet_results
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

**핵심 포인트**:
- nnUNet_results는 읽기 전용(`:ro`)으로 마운트
- GPU 접근을 위해 nvidia 디바이스 예약
- uploads/results 디렉토리는 볼륨으로 마운트 (컨테이너 재시작 시 데이터 보존)

**완료 기준**: `docker-compose up --build` 성공.
`localhost:8000/api/health` 응답, `localhost:3000` 페이지 표시.

### 0-5. .env 파일 및 .gitignore
**.env.example**:
```bash
# 필수 설정
nnunet_results_path=/path/to/your/nnUNet_results

# 선택 설정 (기본값 있음)
UPLOAD_DIR=./uploads
RESULTS_DIR=./results
MAX_UPLOAD_SIZE_MB=500
MAX_CACHED_MODELS=2
GPU_DEVICE_INDEX=0
```

**.gitignore**:
```
# 환경
.env
__pycache__/
node_modules/
*.pyc

# 데이터 (절대 커밋하지 않음)
uploads/
results/
weights/
*.nii
*.nii.gz
*.pth

# 빌드
dist/
build/
.vite/
```

**완료 기준**: `.env.example`을 복사하여 `.env`를 만들고 경로만 수정하면 바로 실행 가능.

---

## Phase 0 완료 체크리스트
- [ ] 디렉토리 구조가 AGENTS.md와 일치한다
- [ ] Backend: `/api/health` 가 200 OK를 반환한다
- [ ] Frontend: 브라우저에서 페이지가 표시된다
- [ ] Docker: `docker-compose up` 으로 한 번에 실행된다
- [ ] `.env.example` 이 존재하고 설명이 충분하다
- [ ] `.gitignore` 가 데이터 파일과 환경 파일을 제외한다
- [ ] Backend에서 `import nnunetv2` 가 에러 없이 실행된다
- [ ] Backend에서 `torch.cuda.is_available()` 이 True를 반환한다
