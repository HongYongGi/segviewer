# nnUNet 통합 전략

## 핵심 질문
> nnUNetv2를 우리 웹앱에 어떻게 통합할 것인가?

## 결론
**nnUNetv2의 Python API (`nnUNetPredictor` 클래스)를 Backend에서 직접 호출한다.**

---

## 배경: nnUNet inference를 호출하는 세 가지 방법

nnUNetv2로 세그멘테이션을 실행하려면 크게 세 가지 방법이 있다.
각각의 장단점을 이해해야 왜 Python API를 선택했는지 알 수 있다.

### 방법 A: CLI(Command Line Interface) 래핑
```bash
# 터미널에서 직접 실행하는 방식
nnUNetv2_predict -i /input -o /output -d 001 -c 3d_fullres -f 0 1 2 3 4
```
이 명령어를 Python의 `subprocess.run()`으로 감싸서 호출하는 방법이다.

### 방법 B: Python API 직접 호출
```python
# Python 코드에서 직접 import하여 사용
from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
predictor = nnUNetPredictor(...)
predictor.initialize_from_trained_model_folder(model_path)
predictor.predict_from_files(input_dir, output_dir)
```

### 방법 C: nnUNet을 별도 서버로 분리 (gRPC/REST)
nnUNet inference만 담당하는 마이크로서비스를 따로 만들고,
우리 Backend가 그 서버에 요청을 보내는 방법이다.

---

## 비교 분석

### 방법 A: CLI 래핑

**장점**:
- 구현이 가장 간단하다 (subprocess 한 줄)
- nnUNet 업데이트에 영향을 거의 받지 않는다 (CLI 인터페이스는 안정적)
- nnUNet 환경과 웹앱 환경을 완전히 분리할 수 있다

**단점**:
- **진행률 추적이 어렵다**: subprocess의 stdout을 파싱해야 하는데,
  nnUNet의 출력 포맷이 버전마다 달라질 수 있다
- **모델 캐싱이 불가능하다**: 매 호출마다 모델을 GPU에 새로 로드한다.
  이 과정이 10~30초 걸리므로, 반복 사용 시 매우 비효율적이다
- **에러 핸들링이 어렵다**: subprocess가 실패하면 stderr 문자열을
  파싱해야 하는데, 에러 유형 구분이 어렵다 (GPU 메모리 부족 vs 파일 오류 등)
- **인메모리 처리가 불가능하다**: 반드시 파일 기반으로만 입출력해야 한다
- **프로세스 오버헤드**: 매번 새 Python 프로세스가 생성된다

**치명적 단점 — 모델 캐싱 불가**:
연구 시나리오에서 같은 모델로 여러 케이스를 연속 처리하는 경우가 대부분이다.
모델 로딩 30초 + inference 30초라면, CLI 방식은 매 케이스마다 60초가 걸리지만,
API 방식은 첫 번째만 60초이고 두 번째부터는 30초다.
10개 케이스 기준: CLI 600초 vs API 330초 — **거의 2배 차이**가 난다.

### 방법 B: Python API 직접 호출 ← 우리의 선택

**장점**:
- **모델 캐싱 가능**: nnUNetPredictor 인스턴스를 메모리에 유지하면
  GPU에 로드된 모델을 재사용할 수 있다
- **세밀한 진행률 추적**: predictor 내부 콜백을 활용하거나,
  예상 시간 기반으로 단계별 진행률을 제공할 수 있다
- **정교한 에러 핸들링**: Python exception을 직접 catch하여
  에러 유형을 정확히 분류할 수 있다 (RuntimeError → GPU OOM 등)
- **인메모리 처리 옵션**: `predict_single_npy_array()` 메서드로
  파일 I/O 없이 numpy array를 직접 전달할 수 있다 (P2에서 검토)
- **동일 프로세스**: FastAPI와 같은 프로세스에서 실행되므로
  프로세스 간 통신 오버헤드가 없다

**단점**:
- **nnUNet 의존성이 Backend에 직접 포함된다**: nnUNet, PyTorch 등
  무거운 패키지가 Backend requirements에 포함됨
- **nnUNet 내부 API 변경에 영향 받을 수 있다**: nnUNetPredictor의
  메서드 시그니처가 바뀌면 우리 코드도 수정해야 한다
- **Backend 프로세스가 무거워진다**: GPU를 사용하는 inference가
  API 서버와 같은 프로세스에서 돌아감

**단점 완화 전략**:
- nnUNet 의존성 → Docker 컨테이너로 환경 고정
- API 변경 → 얇은 래퍼(InferenceService)로 감싸서 변경 영향 최소화
- 프로세스 무게 → 비동기 처리(asyncio)로 inference 중에도 API 응답 가능

### 방법 C: 별도 서버 분리

**장점**:
- 관심사가 완전히 분리된다
- inference 서버만 독립적으로 스케일링할 수 있다
- 여러 GPU 서버에 분산 가능

**단점**:
- **과도한 복잡성**: 우리 규모(5~15명, GPU 1대)에서는 불필요
- **네트워크 통신 오버헤드**: 대용량 NIfTI 데이터를 서비스 간 전송
- **배포/운영 복잡도 증가**: 서비스 2개 관리, 장애 포인트 증가
- **구현 시간 증가**: gRPC 스키마 정의, 서비스 디스커버리 등

---

## 최종 결정 근거

| 기준 | CLI 래핑 | Python API | 별도 서버 |
|------|---------|-----------|----------|
| 모델 캐싱 | ✗ 불가 | ✓ 가능 | ✓ 가능 |
| 진행률 추적 | △ 어려움 | ✓ 가능 | ✓ 가능 |
| 에러 핸들링 | △ 문자열 파싱 | ✓ 직접 catch | ✓ 직접 catch |
| 구현 복잡도 | ✓ 낮음 | ✓ 낮음 | ✗ 높음 |
| 운영 복잡도 | ✓ 낮음 | ✓ 낮음 | ✗ 높음 |
| 확장성 | ✗ 제한적 | △ 중간 | ✓ 높음 |
| 우리 규모에 적합 | △ | ✓ | ✗ |

**모델 캐싱이 가능하다는 점이 결정적**이었다.
연구 워크플로에서 같은 모델을 반복 사용하는 빈도가 매우 높기 때문에,
매번 모델을 새로 로드하는 방식은 사용자 경험을 크게 해친다.

---

## 구현 세부: nnUNetPredictor 래핑 설계

### 왜 래퍼가 필요한가
nnUNetPredictor를 직접 사용할 수 있지만, 얇은 래퍼를 두는 이유:

1. **nnUNet 버전 업데이트 대응**: nnUNetPredictor의 인터페이스가 바뀌면
   래퍼만 수정하면 된다. 나머지 코드(라우터, 서비스)는 영향 없음.
2. **캐싱 로직 분리**: 모델 로딩/해제/캐시 관리는 nnUNet의 책임이 아니라
   우리 앱의 책임이므로 래퍼에서 처리.
3. **비동기 연결**: nnUNet은 동기 코드이지만 FastAPI는 비동기이므로,
   `asyncio.to_thread()`로 감싸는 코드를 래퍼에 집중.

### 래퍼 구조
```python
# backend/app/services/inference_service.py

class InferenceService:
    """nnUNetPredictor를 관리하는 래퍼.
    
    역할:
    1. 모델 캐싱 (LRU, 최대 2개)
    2. inference 실행 (비동기 큐)
    3. 진행률 추적
    4. 에러 분류
    
    이 클래스 밖에서는 nnUNet import를 하지 않는다.
    """
    
    def get_or_load_predictor(self, model_config) -> nnUNetPredictor:
        """캐시에서 predictor를 가져오거나 새로 로드한다."""
        
    def run_inference(self, image_path, model_config, progress_callback):
        """inference를 실행하고 progress_callback으로 진행률을 알린다."""
        
    def release_model(self, cache_key):
        """GPU 메모리에서 모델을 해제한다."""
```

### nnUNet 의존성 격리 규칙
- `from nnunetv2.xxx import yyy` 는 **오직 InferenceService 파일에서만** 사용
- 다른 모든 파일(라우터, 다른 서비스, 유틸)에서는 nnUNet을 직접 import하지 않음
- 이렇게 하면 nnUNet 버전 업데이트 시 수정 범위가 InferenceService 하나로 한정됨

---

## nnUNet 버전 호환성 노트

### 현재 대상: nnUNetv2 (2.x)
- PyPI 패키지: `nnunetv2`
- 핵심 클래스: `nnunetv2.inference.predict_from_raw_data.nnUNetPredictor`
- 최소 요구 Python: 3.9+
- 최소 요구 PyTorch: 2.0+

### nnUNetv1 → v2 주요 차이 (참고)
v1에서 v2로 넘어올 때 가장 큰 변화는:
- v1: `predict_from_folder()` 함수 기반
- v2: `nnUNetPredictor` 클래스 기반 (인스턴스화 → 초기화 → 예측)
- v2에서 모델 캐싱이 가능해진 것도 클래스 기반으로 바뀌었기 때문이다

### 향후 nnUNet 업데이트 대응
nnUNet의 메이저 업데이트가 있을 경우:
1. InferenceService의 래퍼 메서드만 수정
2. 나머지 코드는 InferenceService의 인터페이스에만 의존하므로 무영향
3. Docker 이미지에서 nnUNet 버전을 고정(`nnunetv2==2.x.x`)하여 예기치 않은 업데이트 방지

---

## 진행률 추적 구현 전략

### 문제
nnUNetPredictor는 내부적으로 tqdm을 사용하여 진행률을 표시하지만,
우리가 원하는 것은 "모델 로딩 5% → 전처리 15% → fold별 추론 20~85% → 후처리 90%"
같은 단계별 세분화된 진행률이다.

### 해결 방식: 단계별 시간 추정 (Time-based Progress)

nnUNet 내부를 monkey-patch하지 않고, 각 단계의 예상 소요 시간을 기반으로
진행률을 추정한다.

```
단계별 시간 비율 (전형적인 CT 512x512x128, 3d_fullres, 5-fold):
- 모델 로딩: 15초 (첫 실행) / 0초 (캐시)    → 0~5%
- 전처리: 5초                                → 5~15%
- Fold 0 추론: 10초                          → 15~29%
- Fold 1 추론: 10초                          → 29~43%
- Fold 2 추론: 10초                          → 43~57%
- Fold 3 추론: 10초                          → 57~71%
- Fold 4 추론: 10초                          → 71~85%
- 앙상블 + 후처리: 5초                       → 85~95%
- 결과 저장: 2초                             → 95~100%
```

각 단계의 시작/끝을 감지하는 방법:
- `predictor.initialize_from_trained_model_folder()` 호출 전후 → 모델 로딩
- `predictor.predict_from_files()` 호출 전 → 전처리+추론 시작
- fold 수를 알고 있으므로 전체 시간을 fold 수로 균등 분할
- 호출 완료 후 → 후처리+저장

### 왜 이 방식인가
- nnUNet 내부 코드를 수정하지 않으므로 업데이트에 안전하다
- 정확한 실시간 진행률은 아니지만, 사용자에게 "멈추지 않았다"는
  피드백을 주기에는 충분하다
- 첫 몇 번 실행 후 실제 소요 시간을 기록하여 추정치를 보정할 수 있다 (P2)

---

## 자주 묻는 질문 (FAQ)

### Q: nnUNet을 subprocess로 호출하면 안 되나요? 더 간단한데.
subprocess가 더 간단한 것은 맞다. 하지만 모델 캐싱이 불가능하다는 점이 치명적이다.
연구 시나리오에서 같은 모델로 20개 케이스를 연속 처리할 때,
매번 30초씩 모델을 로드하면 총 10분을 낭비하게 된다.
Python API는 첫 번째만 30초이고 나머지 19개는 추가 로딩 없이 바로 실행된다.

### Q: 나중에 GPU가 여러 대가 되면 어떻게 하나요?
현재 설계(단일 프로세스 내 InferenceService)는 GPU 1대 전제이다.
GPU가 2대 이상이 되면 그때 방법 C(별도 서버 분리)를 검토한다.
지금 YAGNI(You Aren't Gonna Need It) 원칙에 따라 과도한 설계를 피한다.

### Q: inference 중에 웹서버가 멈추지 않나요?
FastAPI의 비동기 처리 덕분에 멈추지 않는다.
inference는 `asyncio.to_thread()`로 별도 스레드에서 실행되므로,
추론 중에도 다른 API 요청(영상 업로드, 메타데이터 조회 등)은 정상 처리된다.
다만 GPU는 하나이므로 동시 inference는 큐로 순차 처리한다.

### Q: predict_single_npy_array()를 쓰면 파일 I/O를 줄일 수 있지 않나요?
맞다. 하지만 MVP에서는 파일 기반(`predict_from_files`)을 사용한다.
이유: (1) 파일 기반이 nnUNet 공식 문서에 더 잘 설명되어 있고,
(2) 디버깅 시 중간 파일을 확인할 수 있어 편하며,
(3) 대부분의 시간이 GPU 연산에 소요되므로 파일 I/O는 전체의 5% 미만이다.
인메모리 방식은 P2에서 최적화 항목으로 검토한다.
