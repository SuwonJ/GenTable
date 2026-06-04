# 시간표 생성기 Product Structure (현재 구현 기준)

이 문서는 **현재 코드베이스의 실제 구조**를 기준으로 작성된 기준 문서입니다.

## 1. 제품 목표

1. 지저분한 학사 원천 데이터를 최대한 안전하게 정규화한다.
2. 생성 엔진은 가능한 후보를 누락하지 않도록 백트래킹 + 안전한 가지치기를 사용한다.
3. UI/레거시 dict 경계를 유지하면서 내부는 도메인 모델 기반으로 동작한다.
4. 생성 제약과 선호 점수 계산 위치를 분리해 규칙을 명확히 관리한다.

## 2. 아키텍처 레이어

```text
app.py (UI)
     -> src/services/scheduler_service.py (orchestration & core logic)
        -> src/filters.py (catalog filtering)
        -> src/ingestion.py (legacy dict -> Lecture)
        -> src/constraints.py (ConstraintRegistry)
        -> src/engine.py (BacktrackingScheduleEngine)
        -> src/domain/*.py (domain models)
```

### 레이어 책임

- **UI (`app.py`)**  
  사용자 입력 수집, 서비스 호출, 검색/결과 화면 배치
- **Facade (`src/scheduler.py`)**  
  외부 호출용 안정적인 공개 진입점 (`generate_timetables`, `recommend_fillers`, `timetable_to_frame`)
- **UI State (`src/presentation/ui_state.py`)**  
  세션 상태, 버킷 조작, 검색 어댑터, 반복 렌더 보조
- **Service (Core Logic) (`src/services/scheduler_service.py`, `src/services/filler_service.py`)**  
  입력 정규화, 필터링, 필수과목 계산, 엔진 실행, warnings 조합 등 핵심 비즈니스 로직 수행
- **Engine (`src/engine.py`)**  
  필수 분반 탐색 + 선택과목 탐색 + top-N 유지 + 통계/점수 계산
- **Constraints (`src/constraints.py`)**  
  생성 hard 제약 정의 및 요청별 조합
- **Domain (`src/domain`)**  
  `Lecture`, `Schedule`, `StudentProfile`, `AcademicTarget`의 불변 모델

## 3. 핵심 도메인 모델

- `Lecture`: 과목/분반/시간/수강대상(`AcademicTarget`) 보유
- `Schedule`: `Lecture` 묶음, 학점/충돌/식별자 집합 계산
- `StudentProfile`: 학년/학기/학과(와일드카드 `"전체"` 정규화 포함)
- `AcademicTarget`: 수강대상 원문에서 학년/학과/제외/특수대상 규칙을 표현

## 4. 생성 파이프라인

1. `catalog`와 UI 입력을 받는다.
2. `build_student_profile()`로 학생 프로필을 만든다.
3. `course_matches_filters()`로 1차 후보를 거른다.
   - 장바구니/대체그룹 강제 항목은 필터에서 보호한다.
4. `required_subject_names_for_profile()`로 필수 과목명을 계산한다.
5. `legacy_courses_to_lectures()`로 엔진 입력 도메인 객체를 만든다.
6. `ConstraintRegistry.from_request()`로 제약 세트를 만든다.
7. `BacktrackingScheduleEngine.search()`를 실행한다.
8. 결과를 legacy dict 후보로 정렬하고 `info["warnings"]`를 합쳐 반환한다.

## 5. 제약 체계

### Hard constraints

- `NoTimeConflictConstraint`
- `NoDuplicateSubjectConstraint`
- `CreditRangeConstraint`
- `RequiredLectureConstraint`
- `RequiredSubjectConstraint`
- `ExcludedLectureConstraint`
- `AlternativeGroupConstraint`
- `StudentEligibilityConstraint` (프로필 자격 검증)

### Scoring

점수와 정렬 기준은 `src.engine.score_candidate()`와 엔진 지표 함수에서만 계산합니다.

## 6. 검색/필터 구조

검색 및 타겟 판정 유틸은 `src/filters.py`에 집중되어 있습니다.

- `course_matches_filters()`: 카테고리/요일/시간/학년/학과/정규식 판정
- `search_score()`: 검색 키워드 가중 점수
- `extract_target_departments()` 등: 수강대상 텍스트 파싱 보조

> 최근 정리 원칙: `app.py`는 `shared_*` alias 래퍼를 두지 않고 `src.filters` 함수나 `src.services`를 직접 사용합니다.

## 7. 출력 계약

`generate_timetables` 반환값:

- `list[dict]` 후보 목록  
  (`courses`, `score`, `sort_key`, `rank`, 기타 점수 메타)
- `info` 딕셔너리  
  (`filtered_count`, `candidate_count`, `warnings`, 버킷/그룹 통계)

UI는 이 계약을 직접 소비하므로, 내부 리팩토링 시에도 반환 shape를 유지해야 합니다.

## 8. 확장 원칙

1. 새 규칙이 필요하면 엔진 본문보다 `constraints.py`에 우선 추가합니다.
2. 검색/타겟 파싱 변경은 `src/filters.py`를 단일 진입점으로 유지합니다.
3. UI 레거시 호환이 필요하면 `src/services/scheduler_service.py` 경계에서 흡수합니다.
4. `info["warnings"]`를 통해 사용자에게 제외/제약 사유를 명시적으로 전달합니다.

## 9. 유지보수 체크리스트

1. `docs/file-structure.md`와 실제 파일 트리가 일치하는가
2. `docs/function-mapping.md` 함수명이 실제 코드와 일치하는가
3. `shared_*` alias/단순 전달 래퍼가 재도입되지 않았는가
4. 검색 규칙(`course_matches_filters`)과 생성 규칙(`StudentEligibilityConstraint`)의 의도가 충돌하지 않는가
