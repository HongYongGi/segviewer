# GPU 메모리 관리 전략

## 핵심 질문
> GPU 하나로 여러 모델의 inference를 어떻게 효율적으로 처리할 것인가?

## 결론
**LRU 캐시로 최대 2개 모델을 GPU에 유지하고,
동시에 1개 inference만 실행하며, 나머지는 큐에 대기시킨다.**

---

## 배경: GPU 메모리는 왜 부족한가

### 일반적인 연구용 GPU VRAM
| GPU | VRAM | 연구실에서 흔한 정도 |
|-----|------|-------------------|
| RTX 3090 | 24 GB | 흔함 |
| RTX 4090 | 24 GB | 흔함 |
| A100 | 40 / 80 GB | 가끔 |
| H100 | 80 GB | 드묾 |

### nnUNet 모델의 GPU 메모리 사용량
nnUNet 3d_fullres 모델 기준 (대략적):
| 항목 | VRAM 사용 |
|------|----------|
| 모델 weight (FP32) | 0.5 ~ 2 GB |
| 입력 텐서 | 1 ~ 4 GB (볼륨 크기에 비례) |
| 중간 활성화 | 2 ~ 8 GB |
| TTA (Test Time Augmentation) | 추가 2 ~ 4 GB |
| **합계 (1개 모델)** | **약 6 ~ 18 GB** |

24GB GPU에 모델 1개를 올리면 이미 대부분의 메모리를 사용한다.
두 번째 모델을 동시에 올리는 것은 대부분 불가능하다.

### 왜 "캐싱"이 중요한가

모델을 GPU에 로드하는 데 걸리는 시간:
| 모델 크기 | CPU→GPU 전송 시간 | 초기화 포함 총 시간 |
|----------|------------------|-------------------|
| 500 MB | ~3초 | ~10초 |
| 1 GB | ~5초 | ~15초 |
| 2 GB | ~10초 | ~30초 |

같은 모델로 10개 케이스를 처리할 때:
- 캐싱 없음: 10 × (로딩 15초 + 추론 30초) = **450초 (7.5분)**
- 캐싱 있음: 로딩 15초 + 10 × 추론 30초 = **315초 (5.25분)** → **30% 절약**

---

## 캐싱 전략 상세

### LRU (Least Recently Used) 캐시

**왜 LRU인가**:
연구 워크플로를 관찰하면 두 가지 패턴이 있다:

1. **단일 모델 반복** (가장 흔함): 하나의 모델로 여러 케이스를 연속 처리
   → 캐시에 1개만 있어도 충분
2. **두 모델 비교** (가끔): 모델 A와 모델 B의 결과를 번갈아 비교
   → 캐시에 2개 있으면 편함 (A→B→A→B 전환 시 매번 로딩 불필요)
3. **세 모델 이상 비교** (드묾): 이 경우 어차피 캐시 미스가 발생하므로
   캐시 크기를 3 이상으로 늘려도 큰 의미 없음

따라서 **캐시 크기 = 2**가 비용 대비 가장 효율적이다.

### 캐시 동작 흐름

```
[요청] 모델 A로 inference 실행해줘

[캐시 확인] 모델 A가 캐시에 있는가?
  ├── YES → 캐시에서 predictor를 꺼내서 바로 inference 실행
  └── NO → 캐시에 빈 자리가 있는가?
       ├── YES → 모델 A를 GPU에 로드하고 캐시에 추가
       └── NO (캐시 꽉 참) → LRU 정책에 따라 가장 오래 안 쓴 모델 해제
                             → 모델 A를 GPU에 로드하고 캐시에 추가
```

### 캐시 키 설계

```python
# 캐시 키: (dataset_id, trainer, plans, configuration)
# 예: ("001", "nnUNetTrainer", "nnUNetPlans", "3d_fullres")

# fold는 캐시 키에 포함하지 않는다!
# 이유: 같은 모델에서 fold만 바꾸는 경우, predictor를 재사용하고
# initialize 단계에서 use_folds만 변경하면 된다.
# (weight 파일 구조가 같으므로 네트워크 구조는 동일)
```

### 모델 해제 절차

GPU 메모리를 확실히 회수하려면 단순히 Python 객체를 삭제하는 것만으로는 부족하다.
PyTorch의 CUDA 메모리 관리 특성 때문에 아래 순서를 반드시 지켜야 한다:

```python
def release_model(self, cache_key: str):
    """GPU에서 모델을 완전히 해제한다."""
    predictor = self.cache.pop(cache_key)
    
    # 1단계: 네트워크를 CPU로 이동 (GPU 텐서 참조 해제)
    if hasattr(predictor, 'network'):
        predictor.network.cpu()
    
    # 2단계: predictor 참조 삭제
    del predictor
    
    # 3단계: Python 가비지 컬렉션 강제 실행
    import gc
    gc.collect()
    
    # 4단계: CUDA 캐시 메모리 해제
    # (PyTorch는 메모리를 pool로 관리하므로 이 단계가 필수)
    torch.cuda.empty_cache()
    
    # 5단계: 해제 후 실제 VRAM 확인 (로그용)
    free_mb = torch.cuda.mem_get_info()[0] / 1024**2
    logger.info(f"모델 해제 완료. GPU 여유 메모리: {free_mb:.0f}MB")
```

**왜 이렇게 복잡한가 (비전문가를 위한 설명)**:
PyTorch는 성능을 위해 GPU 메모리를 미리 할당해두고 재사용하는 "메모리 풀" 방식을 쓴다.
모델을 삭제해도 PyTorch가 "나중에 또 쓸지도 모르니까" 하고 메모리를 잡고 있는 경우가 있다.
`torch.cuda.empty_cache()`를 호출해야 PyTorch가 잡고 있던 메모리를 OS에 반환한다.
그래야 다음 모델을 로드할 공간이 확보된다.

---

## 동시성 제어

### 왜 동시에 1개만 실행하는가

GPU는 CPU와 달리 "시분할 멀티태스킹"에 적합하지 않다.
두 개의 inference를 동시에 실행하면:

1. **VRAM 부족**: 모델 하나가 10~18GB를 쓰는데, 두 개를 동시에 올리면 초과
2. **성능 저하**: GPU가 컨텍스트 스위칭을 하면 각각이 오히려 느려짐
3. **OOM 크래시**: 메모리 초과 시 CUDA OOM 에러로 프로세스가 죽을 수 있음

따라서 **한 번에 1개만 실행하고, 나머지는 큐에 넣어 순서대로 처리**한다.

### 큐 구현

```python
# 비동기 작업 큐 (의사 코드)

class InferenceQueue:
    def __init__(self, max_queue_size=5):
        self.queue = asyncio.Queue(maxsize=max_queue_size)
        self.current_job = None
    
    async def submit(self, job):
        """작업을 큐에 추가한다. 큐가 가득 차면 429 에러."""
        if self.queue.full():
            raise QueueFullError()
        await self.queue.put(job)
        return job.id
    
    async def worker(self):
        """큐에서 작업을 하나씩 꺼내 실행한다. (무한 루프)"""
        while True:
            job = await self.queue.get()
            self.current_job = job
            try:
                await asyncio.to_thread(
                    self.inference_service.run_inference,
                    job.image_path,
                    job.model_config,
                    job.progress_callback
                )
                job.status = "completed"
            except torch.cuda.OutOfMemoryError:
                job.status = "failed"
                job.error = "GPU_OUT_OF_MEMORY"
            except Exception as e:
                job.status = "failed"
                job.error = str(e)
            finally:
                self.current_job = None
```

### 큐 상태 가시성
사용자가 "내 작업이 왜 안 시작하지?"라고 느끼지 않도록:
- 큐에 대기 중일 때: "대기 중 (순서: 2/3)" 같은 메시지 표시
- 다른 사람의 작업이 실행 중일 때: "inference 실행 중... 예상 대기: 30초"
- 큐가 가득 찼을 때: "현재 대기열이 가득 찼습니다. 잠시 후 다시 시도해주세요."

---

## GPU OOM(Out of Memory) 대응

### OOM이 발생하는 시나리오
1. **큰 볼륨**: 512×512×512 같은 고해상도 CT
2. **TTA 활성화**: Test Time Augmentation이 메모리를 2배 가까이 사용
3. **5-fold 앙상블**: fold별로 순차 처리하지만 앙상블 결합 시 메모리 사용

### OOM 대응 전략 (자동 재시도)

```
[1차 시도] 기본 설정으로 inference
  └── OOM 발생?
       ├── NO → 성공!
       └── YES ↓

[2차 시도] TTA(mirroring) 비활성화로 재시도
  → use_mirroring=False (메모리 ~40% 절감, 정확도 소폭 하락)
  └── OOM 발생?
       ├── NO → 성공 (사용자에게 "TTA 없이 실행됨" 알림)
       └── YES ↓

[3차 시도] step_size 증가로 재시도
  → tile_step_size=0.75 (기본 0.5 → 타일 오버랩 감소, 메모리 절감)
  └── OOM 발생?
       ├── NO → 성공 (사용자에게 설정 변경 알림)
       └── YES ↓

[최종 실패]
  → 사용자에게 에러 메시지:
    "GPU 메모리가 부족합니다.
     시도해볼 수 있는 방법:
     1. 단일 fold로 실행 (메모리 절감)
     2. 2d configuration 사용 (3d보다 메모리 적음)
     3. 다른 inference 완료 후 재시도"
```

### OOM 복구 후 메모리 정리
OOM이 발생하면 PyTorch의 GPU 메모리 상태가 불안정해질 수 있다.
반드시 아래 정리를 수행한다:

```python
except torch.cuda.OutOfMemoryError:
    # 실패한 inference의 중간 텐서 정리
    torch.cuda.empty_cache()
    gc.collect()
    
    # 캐시된 모델도 해제 (메모리 확보)
    self.release_all_cached_models()
    
    # 이후 재시도 또는 에러 반환
```

---

## 모니터링: GPU 상태 API

연구원이 "왜 이렇게 느리지?" 할 때 확인할 수 있도록
GPU 상태를 API로 제공한다.

### GET /api/system/gpu
```json
{
  "gpu_name": "NVIDIA RTX 4090",
  "gpu_index": 0,
  "vram_total_mb": 24576,
  "vram_used_mb": 12800,
  "vram_free_mb": 11776,
  "gpu_utilization_percent": 85,
  "gpu_temperature_celsius": 72,
  "cached_models": [
    {
      "key": "001_nnUNetTrainer_nnUNetPlans_3d_fullres",
      "dataset": "Dataset001_Liver",
      "estimated_vram_mb": 2048,
      "loaded_at": "2025-01-15T10:00:00Z",
      "last_used_at": "2025-01-15T10:30:00Z",
      "use_count": 5
    }
  ],
  "current_inference": {
    "job_id": "job-xyz-789",
    "model": "Dataset001_Liver / 3d_fullres",
    "started_at": "2025-01-15T10:35:00Z",
    "elapsed_seconds": 15
  },
  "queue_length": 0,
  "pytorch_version": "2.1.0",
  "cuda_version": "12.1"
}
```

이 정보는 Frontend의 하단 상태바 또는 설정 패널에 표시한다.
주요 표시 항목: GPU 이름, VRAM 사용량 바, 현재 inference 상태.

---

## 자주 묻는 질문

### Q: GPU가 2개면 캐시를 4개로 늘리면 되나요?
현재 설계는 단일 GPU만 지원한다. 다중 GPU 지원은 이 문서의 범위 밖이며,
필요 시 별도 design doc으로 작성한다.
단, InferenceService에서 `device=torch.device('cuda', gpu_index)`로
GPU 인덱스를 지정하는 것은 어렵지 않으므로 확장 가능하다.

### Q: 모델을 미리 로드해둘 수 없나요? (Warm-up)
할 수 있다. 앱 시작 시 환경변수 `PRELOAD_MODELS`에 지정된 모델을
자동 로드하는 기능을 P2에서 구현할 수 있다.

### Q: CPU inference도 지원해야 하나요?
MVP에서는 GPU만 지원한다. CPU inference는 10~100배 느리므로
실용적이지 않다. 다만 `device` 설정을 환경변수로 관리하면
나중에 CPU 지원 추가가 가능하다.
