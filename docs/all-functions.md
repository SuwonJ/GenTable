# 전체 함수 레퍼런스 (자동 정리)

- 범위: 프로젝트의 `*.py` 파일(테스트 포함, `.venv`/숨김 폴더 제외)
- 기준: 현재 코드 스냅샷 기준 자동 추출
- 합계: 함수/메서드 169개

## 목차
- `app.py`
- `src/catalog/catalog.py`
- `src/constraints.py`
- `src/data_loader.py`
- `src/domain/academic.py`
- `src/domain/models.py`
- `src/engine.py`
- `src/filters.py`
- `src/ingestion.py`
- `src/presentation/dataframe_exporter.py`
- `src/presentation/ui_state.py`
- `src/services/filler_service.py`
- `src/services/scheduler_service.py`
- `tests/test_public_api_contract.py`
- `tests/test_scheduler_filters.py`

## app.py

| 심볼 | 설명 |
| :--- | :--- |
| `load_catalog_from_uploads(uploaded_files)` | 외부 데이터/설정을 로드합니다. |
| `render_search_tab(results, active_group, filter_state)` | UI 화면 요소를 렌더링합니다. |
| `render_group_panel(catalog_by_id, group_key)` | UI 화면 요소를 렌더링합니다. |
| `render_basket_tab(catalog_by_id)` | UI 화면 요소를 렌더링합니다. |
| `render_summary_panel(catalog_by_id)` | UI 화면 요소를 렌더링합니다. |
| `render_results_tab(catalog, controls)` | UI 화면 요소를 렌더링합니다. |
| `main()` | 해당 모듈의 핵심 동작을 수행합니다. |

## src/catalog/catalog.py

| 심볼 | 설명 |
| :--- | :--- |
| `LectureCatalog.__init__(self, lectures)` | 내부 보조 로직을 수행합니다. |
| `LectureCatalog.by_id(self, lecture_id)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `LectureCatalog.by_subject_name(self, name)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `LectureCatalog.all(self)` | 해당 모듈의 핵심 동작을 수행합니다. |

## src/constraints.py

| 심볼 | 설명 |
| :--- | :--- |
| `HardConstraint.can_add(self, schedule, lecture)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `HardConstraint.is_satisfied(self, schedule)` | 불리언 조건을 판정합니다. |
| `NoTimeConflictConstraint.can_add(self, schedule, lecture)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `NoTimeConflictConstraint.is_satisfied(self, schedule)` | 불리언 조건을 판정합니다. |
| `NoDuplicateSubjectConstraint.can_add(self, schedule, lecture)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `NoDuplicateSubjectConstraint.is_satisfied(self, schedule)` | 불리언 조건을 판정합니다. |
| `CreditRangeConstraint.can_add(self, schedule, lecture)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `CreditRangeConstraint.is_satisfied(self, schedule)` | 불리언 조건을 판정합니다. |
| `RequiredLectureConstraint.can_add(self, schedule, lecture)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `RequiredLectureConstraint.is_satisfied(self, schedule)` | 불리언 조건을 판정합니다. |
| `RequiredSubjectConstraint.can_add(self, schedule, lecture)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `RequiredSubjectConstraint.is_satisfied(self, schedule)` | 불리언 조건을 판정합니다. |
| `ExcludedLectureConstraint.can_add(self, schedule, lecture)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `ExcludedLectureConstraint.is_satisfied(self, schedule)` | 불리언 조건을 판정합니다. |
| `AlternativeGroupConstraint.can_add(self, schedule, lecture)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `AlternativeGroupConstraint.is_satisfied(self, schedule)` | 불리언 조건을 판정합니다. |
| `StudentEligibilityConstraint.can_add(self, schedule, lecture)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `StudentEligibilityConstraint.is_satisfied(self, schedule)` | 불리언 조건을 판정합니다. |
| `ConstraintRegistry.from_request(*, profile, min_credits, max_credits, required_lecture_ids, required_subject_names, excluded_lecture_ids, candidate_lecture_ids, alternative_groups, weights, enforce_profile_eligibility)` | 해당 모듈의 핵심 동작을 수행합니다. |

## src/data_loader.py

| 심볼 | 설명 |
| :--- | :--- |
| `load_catalog(table_dir)` | 외부 데이터/설정을 로드합니다. |
| `process_files(files, filenames)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `normalize_courses(df, source)` | 값을 일관된 형식으로 정규화합니다. |
| `load_curriculum_required(file)` | 외부 데이터/설정을 로드합니다. |
| `categorize(raw)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `category_label(raw)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `safe_int(value)` | 해당 모듈의 핵심 동작을 수행합니다. |

## src/domain/academic.py

| 심볼 | 설명 |
| :--- | :--- |
| `AcademicTarget.is_eligible(self, grade, department)` | 불리언 조건을 판정합니다. |
| `AcademicTarget.from_raw(cls, raw, target_grades)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `normalize_target_grade(value)` | 값을 일관된 형식으로 정규화합니다. |
| `normalize_wildcard(value)` | 값을 일관된 형식으로 정규화합니다. |

## src/domain/models.py

| 심볼 | 설명 |
| :--- | :--- |
| `TimeSlot.overlaps(self, other)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `Lecture.time_mask(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `StudentProfile.from_legacy(cls, grade, semester, departments)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `Schedule.__post_init__(self)` | 내부 보조 로직을 수행합니다. |
| `Schedule.credits(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `Schedule.lecture_ids(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `Schedule.subject_names(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `Schedule.time_mask(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `Schedule.has_time_conflict(self, lecture)` | 불리언 조건을 판정합니다. |
| `Schedule.add(self, lecture)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `Schedule.raw_courses(self)` | 해당 모듈의 핵심 동작을 수행합니다. |

## src/engine.py

| 심볼 | 설명 |
| :--- | :--- |
| `_daily_earliest_starts(courses)` | 내부 보조 로직을 수행합니다. |
| `count_free_days(courses)` | 지표/건수를 집계합니다. |
| `count_morning_courses(courses)` | 지표/건수를 집계합니다. |
| `count_nine_am_courses(courses)` | 지표/건수를 집계합니다. |
| `count_morning_penalty(courses)` | 지표/건수를 집계합니다. |
| `count_gaps(courses)` | 지표/건수를 집계합니다. |
| `count_gap_minutes(courses)` | 지표/건수를 집계합니다. |
| `total_daily_span(courses)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `earliest_start_among_courses(courses)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `score_candidate(courses, weights, candidate_ids, alternative_groups)` | 검색/후보 점수와 정렬 기준을 계산합니다. |
| `earliest_start(lecture)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `lecture_sort_key(lecture)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `optional_priority(lecture, candidate_ids, group_ids)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `suffix_credit_capacity(credits)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `suffix_alternative_group_cover(course_ids, groups)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `TopNOptimizer.push(self, scored)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `TopNOptimizer.results(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `BacktrackingScheduleEngine.__init__(self, *, catalog, hard_constraints, score_legacy_callback)` | 내부 보조 로직을 수행합니다. |
| `BacktrackingScheduleEngine.search(self, request)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `BacktrackingScheduleEngine._can_add(self, schedule, lecture)` | 내부 보조 로직을 수행합니다. |
| `BacktrackingScheduleEngine._is_satisfied(self, schedule)` | 내부 보조 로직을 수행합니다. |
| `BacktrackingScheduleEngine._initial_schedule_is_viable(self, schedule)` | 내부 보조 로직을 수행합니다. |
| `_legacy_course_sort_key(course)` | 내부 보조 로직을 수행합니다. |

## src/filters.py

| 심볼 | 설명 |
| :--- | :--- |
| `normalize_target_grade(value)` | 값을 일관된 형식으로 정규화합니다. |
| `normalize_target_grades(values)` | 값을 일관된 형식으로 정규화합니다. |
| `regex_match(text, pattern)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `extract_target_departments(target_raw)` | 입력에서 필요한 정보를 추출합니다. |
| `extract_excluded_departments(target_raw)` | 입력에서 필요한 정보를 추출합니다. |
| `has_foreign_marker(target_raw)` | 불리언 조건을 판정합니다. |
| `is_special_population_only(target_raw)` | 불리언 조건을 판정합니다. |
| `is_open_department_target(target_raw)` | 불리언 조건을 판정합니다. |
| `matches_target_grade(target_raw, target_grades)` | 불리언 조건을 판정합니다. |
| `matches_target_department(target_raw, departments)` | 불리언 조건을 판정합니다. |
| `course_search_text(course)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `course_matches_filters(course, filters)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `search_score(course, keywords)` | 검색/후보 점수와 정렬 기준을 계산합니다. |

## src/ingestion.py

| 심볼 | 설명 |
| :--- | :--- |
| `normalize_department_name(value)` | 값을 일관된 형식으로 정규화합니다. |
| `parse_meetings(time_raw)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `to_minutes(value)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `extract_credits(value)` | 입력에서 필요한 정보를 추출합니다. |
| `extract_grades(target_raw)` | 입력에서 필요한 정보를 추출합니다. |
| `required_course_names(curriculum_required, grade, semester)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `build_time_mask(meetings)` | 요청/상태/마스크 등 파생 데이터를 구성합니다. |
| `legacy_course_to_lecture(course)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `legacy_courses_to_lectures(courses)` | 해당 모듈의 핵심 동작을 수행합니다. |

## src/presentation/dataframe_exporter.py

| 심볼 | 설명 |
| :--- | :--- |
| `timetable_to_frame(courses)` | 해당 모듈의 핵심 동작을 수행합니다. |

## src/presentation/ui_state.py

| 심볼 | 설명 |
| :--- | :--- |
| `default_controls()` | 해당 모듈의 핵심 동작을 수행합니다. |
| `sanitize_controls(controls)` | 값을 일관된 형식으로 정규화합니다. |
| `ensure_state()` | 해당 모듈의 핵심 동작을 수행합니다. |
| `export_config()` | 해당 모듈의 핵심 동작을 수행합니다. |
| `import_config(json_str)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `group_keys()` | 해당 모듈의 핵심 동작을 수행합니다. |
| `group_name_map()` | 해당 모듈의 핵심 동작을 수행합니다. |
| `add_group()` | 대상을 컬렉션/상태에 추가합니다. |
| `delete_group(group_key)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `reset_all_buckets()` | 상태를 초기화합니다. |
| `profile_grade_label(grade)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `generation_filter_state(controls)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `matches_filters(course, category_filters, day_filters, time_filter, target_grades, target_departments, hide_foreign_only, target_include_regex, target_exclude_regex)` | 불리언 조건을 판정합니다. |
| `search_courses(courses, query, category_filters, day_filters, time_filter, target_grades, target_departments, hide_foreign_only, target_include_regex, target_exclude_regex)` | 검색/후보 점수와 정렬 기준을 계산합니다. |
| `update_bucket(course_id, bucket)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `remove_from_bucket(course_id)` | 대상을 컬렉션/상태에서 제거합니다. |
| `add_to_group(course_id, group_key)` | 대상을 컬렉션/상태에 추가합니다. |
| `remove_from_group(course_id, group_key)` | 대상을 컬렉션/상태에서 제거합니다. |
| `clear_group(group_key)` | 상태를 초기화합니다. |
| `bucket_label(course_id)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `group_label(course_id)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `group_key_for_course(course_id)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `clear_course_selection(course_id)` | 상태를 초기화합니다. |
| `current_selection_value(course_id)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `selection_options()` | 해당 모듈의 핵심 동작을 수행합니다. |
| `selection_label(value)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `selection_status_meta(course_id)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `apply_selection_from_widget(course_id, widget_key)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `add_all_to_group_batch(results, group_key)` | 대상을 컬렉션/상태에 추가합니다. |
| `alternative_group_sets()` | 해당 모듈의 핵심 동작을 수행합니다. |
| `sync_group_name(group_key)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `format_course_line(course)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `render_course_meta(course)` | UI 화면 요소를 렌더링합니다. |
| `minute_to_text(value)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `earliest_start_by_day(candidate)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `render_timetable(candidate, alternative_groups)` | UI 화면 요소를 렌더링합니다. |
| `has_internal_conflict(courses)` | 불리언 조건을 판정합니다. |
| `result_frame(results)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `target_departments(courses)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `highlight_target_text(course, filter_state)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `target_badges(course)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `matched_target_pills(course, filter_state)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `matched_rule_text(course, filter_state)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `render_pills(pills, highlight)` | UI 화면 요소를 렌더링합니다. |

## src/services/filler_service.py

| 심볼 | 설명 |
| :--- | :--- |
| `recommend_fillers(catalog, base_courses, failed_course_names, max_results)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `_has_conflict(course, selected)` | 내부 보조 로직을 수행합니다. |
| `_freed_time_blocks(base_courses, failed_course_names)` | 내부 보조 로직을 수행합니다. |
| `_overlap_minutes(meeting, block)` | 내부 보조 로직을 수행합니다. |

## src/services/scheduler_service.py

| 심볼 | 설명 |
| :--- | :--- |
| `generate_timetables(*, catalog, grade, semester, include_regex, exclude_regex, preferred_ids, candidate_ids, excluded_ids, alternative_groups, min_credits, max_credits, elective_count, top_n, weights, filter_state)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `build_student_profile(grade, semester, filter_state)` | 요청/상태/마스크 등 파생 데이터를 구성합니다. |
| `required_subject_names_for_profile(curriculum_required, profile)` | 해당 모듈의 핵심 동작을 수행합니다. |

## tests/test_public_api_contract.py

| 심볼 | 설명 |
| :--- | :--- |
| `make_course(course_id, name, day, start, end)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `PublicSchedulerApiContractTests.test_scheduler_facade_exports_only_public_entrypoints(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `PublicSchedulerApiContractTests.test_generate_timetables_result_shape_and_ordering_contract(self)` | 해당 모듈의 핵심 동작을 수행합니다. |

## tests/test_scheduler_filters.py

| 심볼 | 설명 |
| :--- | :--- |
| `make_course(course_id, name, day, start, end, *, category, category_label, target_raw, professor, credits, seats)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `SchedulerFilterTests.test_schedule_request_uses_default_state_limit(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `SchedulerFilterTests.test_optional_priority_prefers_later_start(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `SchedulerFilterTests.test_open_department_target_matches_shared_filter(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `SchedulerFilterTests.test_target_grade_filter_accepts_numeric_profile_grade(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `SchedulerFilterTests.test_target_department_filter_applies_aliases(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `SchedulerFilterTests.test_generate_timetable_applies_profile_target_filter(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `SchedulerFilterTests.test_generate_timetable_satisfies_alternative_group(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `SchedulerFilterTests.test_generate_timetable_selects_only_one_per_alternative_group(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `SchedulerFilterTests.test_generate_timetable_does_not_fail_when_elective_count_zero(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `SchedulerFilterTests.test_generate_timetable_ignores_empty_alternative_group_after_catalog_sync(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `SchedulerFilterTests.test_score_candidate_prefers_later_start_when_morning_avoidance_enabled(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `SchedulerFilterTests.test_score_candidate_penalizes_each_morning_day(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `SchedulerFilterTests.test_generate_timetable_prefers_later_optional_course(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `SchedulerFilterTests.test_generate_timetable_includes_legacy_score_metrics(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
| `SchedulerFilterTests.test_sort_key_prioritizes_zero_nine_am_courses(self)` | 해당 모듈의 핵심 동작을 수행합니다. |
