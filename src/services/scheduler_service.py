from __future__ import annotations

from src.catalog.catalog import LectureCatalog
from src.constraints import ConstraintRegistry
from src.domain.models import Schedule, StudentProfile
from src.engine import BacktrackingScheduleEngine, ScheduleRequest, score_candidate
from src.filters import course_matches_filters
from src.ingestion import (
    build_time_mask,
    legacy_course_to_lecture,
    legacy_courses_to_lectures,
    normalize_department_name,
    required_course_names,
)


def generate_timetables(
    *,
    catalog: dict,
    grade: str,
    semester: str,
    include_regex: str,
    exclude_regex: str,
    preferred_ids: set[str] | None,
    candidate_ids: set[str] | None,
    excluded_ids: set[str] | None,
    alternative_groups: list[set[str]] | None,
    min_credits: int,
    max_credits: int,
    elective_count: int,
    top_n: int,
    weights: dict,
    filter_state: dict | None,
    custom_criteria: list | None = None,
    course_tags: dict[str, list[str]] | None = None,
) -> tuple[list[dict], dict]:
    warnings = list(catalog.get("warnings", []))
    preferred_ids = preferred_ids or set()
    candidate_ids = candidate_ids or set()
    excluded_ids = excluded_ids or set()
    raw_alternative_groups = [set(group) for group in (alternative_groups or []) if group]
    catalog_course_ids = {str(course.get("course_id", "")) for course in catalog["courses"]}
    alternative_groups: list[set[str]] = []
    for index, group in enumerate(raw_alternative_groups, start=1):
        # 업로드한 강의 목록에 실제로 존재하는 과목만 대체 그룹에 남긴다.
        present_ids = {course_id for course_id in group if course_id in catalog_course_ids}
        missing_count = len(group) - len(present_ids)
        if missing_count:
            warnings.append(f"대체 그룹 {index}에서 현재 데이터에 없는 과목 {missing_count}개를 제외했습니다.")
        if not present_ids:
            warnings.append(f"대체 그룹 {index}은(는) 현재 데이터에 선택 가능한 과목이 없어 그룹 제약에서 제외되었습니다.")
            continue
        alternative_groups.append(present_ids)

    effective_filter_state = dict(filter_state or {})
    if effective_filter_state.get("target_departments"):
        # 학과 필터는 수강대상 파싱과 같은 별칭 규칙으로 맞춘다.
        effective_filter_state["target_departments"] = [
            normalize_department_name(dept)
            for dept in effective_filter_state["target_departments"]
            if str(dept).strip()
        ]
    effective_filter_state["include_regex"] = include_regex
    effective_filter_state["exclude_regex"] = exclude_regex
    profile = build_student_profile(grade, semester, effective_filter_state)
    forced_ids = set(preferred_ids)
    for group in alternative_groups:
        # 그룹바구니 과목은 검색 필터와 무관하게 생성 후보에 포함시킨다.
        forced_ids.update(group)

    filtered_courses = []
    for course in catalog["courses"]:
        if "time_mask" not in course:
            course["time_mask"] = build_time_mask(course["meetings"])
        is_preferred = course["course_id"] in preferred_ids
        is_forced = course["course_id"] in forced_ids
        is_excluded = course["course_id"] in excluded_ids
        if is_excluded and not is_preferred:
            continue
        # 사용자가 고정/그룹 지정한 과목은 필터 밖이어도 엔진에 넘긴다.
        if is_forced or course_matches_filters(course, effective_filter_state):
            filtered_courses.append(course)

    required_subject_names = required_subject_names_for_profile(catalog.get("curriculum_required", {}), profile)
    filtered_by_id = {course["course_id"]: course for course in filtered_courses}
    filtered_alternative_groups: list[set[str]] = []
    for index, group in enumerate(alternative_groups, start=1):
        available_group = set(group).intersection(filtered_by_id.keys())
        if not available_group:
            warnings.append(f"대체 그룹 {index}은(는) 현재 생성 조건에서 선택 가능한 과목이 없어 그룹 제약에서 제외되었습니다.")
            continue
        filtered_alternative_groups.append(available_group)
    alternative_groups = filtered_alternative_groups

    available_preferred_ids = frozenset(course_id for course_id in preferred_ids if course_id in filtered_by_id)
    preferred_objects = [filtered_by_id[course_id] for course_id in available_preferred_ids]
    preferred_lectures = [legacy_course_to_lecture(course) for course in preferred_objects]
    adjusted_required = set()
    for name in required_subject_names:
        if any(course["name"] == name for course in preferred_objects):
            # 이미 장바구니에 담긴 필수 과목은 추가 분반 선택이 필요 없다.
            adjusted_required.add(name)
            continue
        
        candidates = [course for course in filtered_courses if course["name"] == name]
        if not candidates:
            warnings.append(f"학년 필수 과목 '{name}'은(는) 검색 조건이나 학과/학년 제한으로 인해 선택 가능한 분반이 없습니다.")
            continue

        if all(
            any(Schedule((preferred,)).has_time_conflict(legacy_course_to_lecture(course)) for preferred in preferred_lectures)
            for course in candidates
        ):
            warnings.append(f"학년 필수 과목 '{name}'은(는) 장바구니 과목과 시간이 겹쳐 제외되었습니다.")
        else:
            # 충돌 없는 분반이 하나라도 있으면 엔진이 직접 선택하게 한다.
            adjusted_required.add(name)

    # 딕셔너리 기반 강의 목록을 엔진이 쓰는 조회 객체로 변환한다.
    lecture_catalog = LectureCatalog(legacy_courses_to_lectures(filtered_courses))
    constraint_set = ConstraintRegistry.from_request(
        profile=profile,
        min_credits=min_credits,
        max_credits=max_credits,
        required_lecture_ids=available_preferred_ids,
        required_subject_names=frozenset(adjusted_required),
        excluded_lecture_ids=frozenset(excluded_ids),
        candidate_lecture_ids=frozenset(candidate_ids),
        alternative_groups=tuple(frozenset(group) for group in alternative_groups),
        weights=weights,
        enforce_profile_eligibility=True,
    )
    request = ScheduleRequest(
        profile=profile,
        min_credits=min_credits,
        max_credits=max_credits,
        required_lecture_ids=available_preferred_ids,
        required_subject_names=frozenset(adjusted_required),
        candidate_lecture_ids=frozenset(candidate_ids),
        excluded_lecture_ids=frozenset(excluded_ids),
        alternative_groups=tuple(frozenset(group) for group in alternative_groups),
        top_n=top_n,
    )

    result = BacktrackingScheduleEngine(
        catalog=lecture_catalog,
        hard_constraints=constraint_set.hard_constraints,
        score_legacy_callback=lambda courses, requested_candidate_ids, requested_alternative_groups: score_candidate(
            courses,
            weights,
            requested_candidate_ids,
            requested_alternative_groups,
            custom_criteria=custom_criteria,
            course_tags=course_tags,
        ),
    ).search(request)

    candidate_rows = list(result.scored_candidates)
    candidate_rows.sort(key=lambda item: item["sort_key"], reverse=True)
    for rank, candidate in enumerate(candidate_rows[:top_n], start=1):
        # 화면 탭 이름에 사용할 순위를 서비스에서 확정한다.
        candidate["rank"] = rank

    all_warnings = warnings + list(result.warnings)
    info = {
        "required_selected": len(adjusted_required),
        "filtered_count": len(filtered_courses),
        "candidate_count": result.stats.candidate_count,
        "preferred_count": len(preferred_ids),
        "candidate_bucket_count": len(candidate_ids),
        "excluded_count": len(excluded_ids),
        "group_count": len(alternative_groups),
        "warnings": all_warnings,
    }
    return candidate_rows[:top_n], info


def build_student_profile(grade: str, semester: str, filter_state: dict | None = None) -> StudentProfile:
    departments = (filter_state or {}).get("target_departments") or []
    departments = [normalize_department_name(dept) for dept in departments if str(dept).strip()]
    return StudentProfile.from_legacy(grade=grade, semester=semester, departments=departments)


def required_subject_names_for_profile(curriculum_required: dict, profile: StudentProfile) -> frozenset[str]:
    if not profile.grade or not profile.semester:
        return frozenset()
    return frozenset(required_course_names(curriculum_required, profile.grade, profile.semester))
