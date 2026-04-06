# QUALITY_SCORE.md — 품질 기준

## 이 문서의 목적
에이전트가 코드를 작성할 때 "이 정도면 충분한가?"를 판단하는 기준을 정의한다.
완벽함을 추구하지 않되, 최소한의 품질은 보장한다.

---

## 기능 완료 기준

하나의 기능이 "완료"되려면 아래를 모두 만족해야 한다:

### Must (필수)
- [ ] 정상 시나리오에서 기대대로 동작한다
- [ ] 명백한 에러 케이스에서 크래시하지 않고 에러 메시지를 표시한다
- [ ] 관련 스펙 문서(product-specs)의 완료 기준을 통과한다
- [ ] NIfTI 헤더(affine, spacing)가 보존된다 (해당되는 경우)
- [ ] Inference 결과가 CLI 실행 결과와 동일하다 (해당되는 경우)

### Should (권장)
- [ ] TypeScript 타입 에러가 없다
- [ ] Python 코드에 타입 힌트가 있다
- [ ] 에러 메시지가 사용자 친화적이다 (다음 행동 안내 포함)
- [ ] 10초 이상 걸리는 작업에 진행률 표시가 있다

### Nice to have (있으면 좋음)
- [ ] 테스트 코드가 있다
- [ ] 코드에 주석이 충분하다 (왜 이렇게 했는지)
- [ ] 성능이 합리적이다 (주관적 기준: "불편하지 않은" 수준)

---

## 코드 품질 기준

### Python (Backend)
- 함수 길이: 50줄 이내 권장 (넘으면 분리)
- 타입 힌트: 모든 public 함수의 인자와 반환값
- docstring: 모든 service 클래스와 public 메서드
- import 정리: 표준 라이브러리 → 서드파티 → 로컬 순서

### TypeScript (Frontend)
- 컴포넌트 길이: 150줄 이내 권장 (넘으면 분리)
- any 타입: 금지
- Props 타입: interface로 명시적 정의
- 매직 넘버 금지: 상수로 추출

---

## Inference 결과 품질 검증

### bit-exact 검증 방법
웹앱의 inference 결과가 CLI와 동일한지 확인하는 절차:

```python
import nibabel as nib
import numpy as np

web_result = nib.load('web_output/result.nii.gz').get_fdata()
cli_result = nib.load('cli_output/result.nii.gz').get_fdata()

# 완전 일치 확인
assert np.array_equal(web_result, cli_result), "결과가 다릅니다!"

# affine 일치 확인
web_affine = nib.load('web_output/result.nii.gz').affine
cli_affine = nib.load('cli_output/result.nii.gz').affine
assert np.allclose(web_affine, cli_affine), "Affine이 다릅니다!"
```

이 검증은 Phase 1-5(Inference 실행) 완료 시 반드시 수행한다.
