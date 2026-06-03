# 핵심 함수/클래스 매핑 (현재 코드 기준)

## 1. UI / Facade

| 위치 | 심볼 | 역할 |
| :--- | :--- | :--- |
| `app.py` | `load_catalog_from_uploads()`, `render_*`, `main()` | 입력 수집 + 호출 + 화면 배치 |
| `src/scheduler.py` | `generate_timetables()`, `recommend_fillers()`, `timetable_to_frame()` | 외부 공개용 안정적인 퍼사드 API 진입점 |
| `src/presentation/ui_state.py` | `search_courses()`, `matches_filters()` | 검색어 + 필터 상태로 강의 목록 정렬 |
| `src/presentation/ui_state.py` | `ensure_state()`, `update_bucket()` 등 | 세션 상태/버킷 조작 |
| `src/presentation/ui_state.py` | `render_course_meta()`, `render_timetable()` 등 | 반복 표현/렌더 보조 |
| `src/services/scheduler_service.py` | `generate_timetables()` | 서비스 계층 핵심 시간표 생성 로직 |
| `src/services/filler_service.py` | `recommend_fillers()` | 실패 과목 제거 후 대체 강의 추천 로직 |
| `src/presentation/dataframe_exporter.py` | `timetable_to_frame()` | 시간표 DataFrame 변환 핵심 유틸 |

## 2. 서비스 파이프라인

| 위치 | 심볼 | 역할 |
| :--- | :--- | :--- |
| `src/services/scheduler_service.py` | `generate_timetables_from_legacy_catalog()` | 생성 전체 오케스트레이션 |
| `src/services/scheduler_service.py` | `build_student_profile()` | UI 입력 → `StudentProfile` |
| `src/services/scheduler_service.py` | `required_subject_names_for_profile()` | 학년/학기 기반 필수 과목명 계산 |
| `src/services/filler_service.py` | `recommend_fillers()` | 실패 과목 제거 후 대체 강의 추천 구현 |

## 3. 엔진 / 제약

| 위치 | 심볼 | 역할 |
| :--- | :--- | :--- |
| `src/engine.py` | `ScheduleRequest` | 엔진 입력 DTO |
| `src/engine.py` | `BacktrackingScheduleEngine.search()` | 필수 분반 선택 + 선택과목 탐색 |
| `src/engine.py` | `TopNOptimizer` | top-N 후보 유지 |
| `src/engine.py` | `score_candidate()` + 지표 함수 | 최종 후보 점수 및 정렬 키 계산 |
| `src/constraints.py` | `ConstraintRegistry.from_request()` | 생성 hard 제약 조합 |
| `src/constraints.py` | `NoTimeConflictConstraint` 외 hard classes | 충돌/학점/필수/제외/그룹/자격 검증 |

## 4. 필터/정규화/도메인

| 위치 | 심볼 | 역할 |
| :--- | :--- | :--- |
| `src/filters.py` | `course_matches_filters()` | 검색/생성 공용 필터 판단 |
| `src/filters.py` | `regex_match()`, `search_score()` | 정규식/검색 스코어 유틸 |
| `src/filters.py` | `extract_target_departments()` 등 | 수강대상 텍스트 파싱 보조 |
| `src/data_loader.py` | `process_files()` | 업로드 파일 분류/정규화/경고 수집 |
| `src/ingestion.py` | `legacy_course_to_lecture()`, `build_time_mask()` | legacy dict → 도메인 `Lecture`, 파생 필드 생성 |
| `src/domain/models.py` | `Lecture`, `Schedule`, `StudentProfile` | 핵심 도메인 모델 |
| `src/domain/academic.py` | `AcademicTarget.from_raw()` | 수강대상 문자열 정규화/자격판정 |

## 5. 리팩토링 규칙 (중요)

1. 단순 전달 래퍼(`def x(...): return y(...)`)는 추가하지 않습니다.
2. `shared_*` alias import 패턴은 사용하지 않습니다.
3. 공용 로직은 원본 모듈(`src.filters`, `src.services` 등)에서 직접 import해 사용합니다.
