# 코드 이해 학습 경로 (현재 구조용)

## 1. 문서 먼저 읽기 (빠른 입문)

1. `docs/file-structure.md`  
   - 모듈 책임과 경계를 먼저 잡습니다.
2. `docs/data-flow.md`  
   - 검색/생성 요청이 어디를 거쳐 처리되는지 확인합니다.
3. `docs/function-mapping.md`  
   - 증상별로 어느 파일/함수를 열어야 하는지 연결합니다.
4. `docs/product-structure.md`  
   - 전체 설계 원칙과 확장 포인트를 확인합니다.

## 2. 코드 읽기 순서 (핵심 8파일)

1. `app.py`  
   - 입력 수집, 서비스 호출, 화면 배치 확인
2. `src/presentation/ui_state.py`
   - 상태(`controls`, 버킷), 검색 어댑터, 반복 렌더 보조 확인
3. `src/scheduler.py`
   - 외부 공개용 안정적인 퍼사드 API 진입점
4. `src/services/scheduler_service.py`  
   - 실제 생성 파이프라인 조율 및 생성 알고리즘 조율 서비스
5. `src/services/filler_service.py`
   - 대체 강의 추천 서비스
6. `src/filters.py`  
   - 검색/타겟 판정 공통 규칙
7. `src/constraints.py`  
   - 생성 hard 제약과 registry 조합 방식
8. `src/engine.py`  
   - 백트래킹 탐색/가지치기/Top-N/점수 계산
9. `src/ingestion.py`  
   - dict 강의 → 도메인 변환/필수 과목명 추출
10. `src/domain/models.py` + `src/domain/academic.py`  
    - 불변 도메인 모델과 수강대상 자격 규칙

## 3. 디버깅 시작점 가이드

1. 검색 결과가 이상함: `src.presentation.ui_state.search_courses` → `src.filters.course_matches_filters`
2. 생성 후보가 안 나옴: `scheduler_service.generate_timetables_from_legacy_catalog`
3. 특정 강의가 누락됨: `ConstraintRegistry` + `StudentEligibilityConstraint`
4. 순위가 체감과 다름: `src.engine.score_candidate` + 엔진 지표 함수
5. 경고 메시지 확인: 반환된 `info["warnings"]`

## 4. 기여 시 체크포인트

1. 래퍼 함수 대신 원본 모듈 직접 import 사용
2. 검색 규칙과 생성 규칙이 서로 어긋나지 않게 유지
3. UI 변경 시 `generate_timetables` (in `scheduler_service.py`) 인자 계약 유지
4. 변경 후 `tests/test_scheduler_filters.py`, `tests/test_public_api_contract.py` 포함 전체 테스트 확인
