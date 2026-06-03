from __future__ import annotations

import heapq
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from src.catalog.catalog import LectureCatalog
from src.domain.models import Lecture, Schedule, StudentProfile


DAY_ORDER = ["월", "화", "수", "목", "금"]


def _daily_earliest_starts(courses: list[dict]) -> dict[str, int]:
    daily_min: dict[str, int] = {}
    for course in courses:
        for meeting in course.get("meetings", []):
            day = meeting["day"]
            start = meeting["start"]
            if day not in daily_min or start < daily_min[day]:
                daily_min[day] = start
    return daily_min


def count_free_days(courses: list[dict]) -> int:
    used = {meeting["day"] for course in courses for meeting in course.get("meetings", [])}
    return len([day for day in DAY_ORDER if day not in used])


def count_morning_courses(courses: list[dict]) -> int:
    return sum(1 for start in _daily_earliest_starts(courses).values() if start < 9.5 * 60)


def count_nine_am_courses(courses: list[dict]) -> int:
    return sum(1 for start in _daily_earliest_starts(courses).values() if 9 * 60 <= start < 10 * 60)


def count_morning_penalty(courses: list[dict]) -> float:
    penalty = 0.0
    for first_start in _daily_earliest_starts(courses).values():
        if first_start >= 12 * 60:
            continue
        penalty += max(0.0, (12 * 60 - first_start) / 30)
    return penalty


def count_gaps(courses: list[dict]) -> int:
    daily = defaultdict(list)
    for course in courses:
        for meeting in course.get("meetings", []):
            daily[meeting["day"]].append((meeting["start"], meeting["end"]))

    gaps = 0
    for items in daily.values():
        items.sort()
        # 90분 이하의 빈 시간만 사용자가 체감하는 애매한 공강으로 센다.
        for (_, prev_end), (next_start, _) in zip(items, items[1:]):
            if 0 < next_start - prev_end <= 90:
                gaps += 1
    return gaps


def count_gap_minutes(courses: list[dict]) -> int:
    daily = defaultdict(list)
    for course in courses:
        for meeting in course.get("meetings", []):
            daily[meeting["day"]].append((meeting["start"], meeting["end"]))

    gap_minutes = 0
    for items in daily.values():
        items.sort()
        for (_, prev_end), (next_start, _) in zip(items, items[1:]):
            if next_start > prev_end:
                gap_minutes += next_start - prev_end
    return gap_minutes


def total_daily_span(courses: list[dict]) -> int:
    daily = defaultdict(list)
    for course in courses:
        for meeting in course.get("meetings", []):
            daily[meeting["day"]].append((meeting["start"], meeting["end"]))

    span = 0
    for items in daily.values():
        if not items:
            continue
        starts = [start for start, _ in items]
        ends = [end for _, end in items]
        span += max(ends) - min(starts)
    return span


def earliest_start_among_courses(courses: list[dict]) -> int:
    starts = [meeting["start"] for course in courses for meeting in course.get("meetings", [])]
    if not starts:
        return 24 * 60
    return min(starts)


def score_candidate(
    courses: list[dict],
    weights: dict,
    candidate_ids: set[str],
    alternative_groups: list[set[str]],
    custom_criteria: list | None = None,
    course_tags: dict[str, list[str]] | None = None,
) -> dict:
    free_days = count_free_days(courses)
    nine_am_count = count_nine_am_courses(courses)
    morning_count = count_morning_courses(courses)
    morning_penalty = count_morning_penalty(courses)
    gap_count = count_gaps(courses)
    gap_minutes = count_gap_minutes(courses)
    daily_span = total_daily_span(courses)
    earliest_class_start = earliest_start_among_courses(courses)
    seats_sum = sum(course["seats"] for course in courses)
    course_ids = {course["course_id"] for course in courses}
    score = 1000.0

    # 사용자가 조절한 가중치를 실제 점수 보상/감점으로 변환한다.
    score += weights["prefer_free_day"] * free_days * 120
    score -= weights["avoid_morning"] * morning_penalty * 8
    score -= weights["avoid_morning"] * morning_count * 25
    score -= weights["avoid_gap"] * gap_minutes * 0.9
    score -= weights["avoid_gap"] * gap_count * 18

    score += weights.get("prefer_seats", 0) * min(seats_sum / 5, 30)
    score += sum(15 for course in courses if course["category"] in {"major_required", "general_required"})
    score += len(candidate_ids.intersection(course_ids)) * 25
    score += sum(10 for group in alternative_groups if group.intersection(course_ids))

    # LLM 커스텀 기준 점수를 합산한다.
    custom_score = 0.0
    if custom_criteria:
        from src.services.criteria_service import evaluate_all_criteria
        custom_score = evaluate_all_criteria(custom_criteria, courses, course_tags)
        score += custom_score

    avoid_morning_weight = weights.get("avoid_morning", 0)
    if avoid_morning_weight > 0:
        # 오전 회피가 켜진 경우 9시 수업이 적은 후보를 우선 정렬한다.
        sort_key = (
            -nine_am_count,
            -morning_penalty,
            -morning_count,
            -gap_minutes,
            free_days,
            round(score, 3),
            -earliest_class_start,
            -daily_span,
            seats_sum,
            -len(courses),
        )
    else:
        sort_key = (
            round(score, 3),
            -gap_minutes,
            free_days,
            -earliest_class_start,
            -daily_span,
            seats_sum,
            -len(courses),
        )

    return {
        "courses": courses,
        "score": score,
        "sort_key": sort_key,
        "total_credits": sum(course["credits"] for course in courses),
        "free_days": free_days,
        "nine_am_count": nine_am_count,
        "gap_count": gap_count,
        "morning_count": morning_count,
        "morning_penalty": morning_penalty,
        "gap_minutes": gap_minutes,
        "custom_score": custom_score,
    }


def earliest_start(lecture: Lecture) -> int:
    if not lecture.time_slots:
        return 24 * 60
    return min(slot.start_minute for slot in lecture.time_slots)


def lecture_sort_key(lecture: Lecture) -> tuple:
    first = min((slot.start_minute for slot in lecture.time_slots), default=24 * 60)
    return first, lecture.subject.name, lecture.id


def optional_priority(lecture: Lecture, candidate_ids: frozenset[str], group_ids: frozenset[str]) -> tuple:
    return (
        # 위시와 그룹바구니에 담긴 과목을 선택 과목 탐색 앞쪽에 둔다.
        lecture.id in candidate_ids,
        lecture.id in group_ids,
        lecture.subject.category in {"major_required", "general_required"},
        lecture.seats,
        earliest_start(lecture),
        lecture.subject.name,
    )


def suffix_credit_capacity(credits: list[float]) -> list[float]:
    suffix = [0.0] * (len(credits) + 1)
    for index in range(len(credits) - 1, -1, -1):
        # 남은 선택 과목으로 채울 수 있는 최대 학점을 미리 계산한다.
        suffix[index] = suffix[index + 1] + credits[index]
    return suffix


def suffix_alternative_group_cover(course_ids: list[str], groups: tuple[frozenset[str], ...]) -> list[set[int]]:
    suffix: list[set[int]] = [set() for _ in range(len(course_ids) + 1)]
    for index in range(len(course_ids) - 1, -1, -1):
        suffix[index] = set(suffix[index + 1])
        for group_index, group in enumerate(groups):
            if course_ids[index] in group:
                # 뒤쪽 후보들로 아직 만족시킬 수 있는 그룹 번호를 저장한다.
                suffix[index].add(group_index)
    return suffix


DEFAULT_MAX_STATES = 120_000


@dataclass(frozen=True)
class ScheduleRequest:
    profile: StudentProfile
    min_credits: float
    max_credits: float
    required_lecture_ids: frozenset[str]
    required_subject_names: frozenset[str]
    candidate_lecture_ids: frozenset[str]
    excluded_lecture_ids: frozenset[str]
    alternative_groups: tuple[frozenset[str], ...]
    top_n: int
    max_states: int | None = DEFAULT_MAX_STATES


@dataclass(frozen=True)
class SearchStats:
    explored_states: int = 0
    candidate_count: int = 0
    search_limit_hit: bool = False


@dataclass(frozen=True)
class ScheduleResult:
    schedules: tuple[Schedule, ...]
    scored_candidates: tuple[dict, ...]
    stats: SearchStats
    warnings: tuple[str, ...] = ()


@dataclass
class TopNOptimizer:
    top_n: int
    _heap: list[tuple[tuple, int, dict]] = field(default_factory=list)
    _sequence: int = 0

    def push(self, scored: dict) -> None:
        self._sequence += 1
        item = (scored["sort_key"], self._sequence, scored)
        if len(self._heap) < max(self.top_n, 1):
            heapq.heappush(self._heap, item)
            return
        if item[0] > self._heap[0][0]:
            # 상위 후보보다 낮은 조합은 버려 메모리 사용량을 제한한다.
            heapq.heapreplace(self._heap, item)

    def results(self) -> list[dict]:
        return [item[2] for item in sorted(self._heap, key=lambda value: value[0], reverse=True)]


ScoreCallback = Callable[[list[dict], set[str], list[set[str]]], dict]


class BacktrackingScheduleEngine:
    def __init__(
        self,
        *,
        catalog: LectureCatalog,
        hard_constraints: tuple[object, ...],
        score_legacy_callback: ScoreCallback | None = None,
    ) -> None:
        self.catalog = catalog
        self.hard_constraints = hard_constraints
        self.score_legacy_callback = score_legacy_callback

    def search(self, request: ScheduleRequest) -> ScheduleResult:
        warnings: list[str] = []
        preferred = [lecture for lecture_id in request.required_lecture_ids if (lecture := self.catalog.by_id(lecture_id))]
        initial = Schedule(tuple(preferred))
        # 장바구니에서 이미 중복/충돌이 있으면 사용자에게 먼저 경고한다.
        for left_index, left in enumerate(preferred):
            for right in preferred[left_index + 1 :]:
                if left.subject.name == right.subject.name:
                    warnings.append(
                        f"경고: '{left.subject.name}'의 서로 다른 분반({left.id}, {right.id})이 모두 장바구니(필수)에 있습니다. 하나만 선택해야 합니다."
                    )
                if Schedule((left,)).has_time_conflict(right):
                    warnings.append(f"경고: 장바구니(필수) 과목 간 시간 충돌 발생: {left.subject.name} <-> {right.subject.name}")

        selected_preferred_names = initial.subject_names
        required_choice_names = sorted(request.required_subject_names - selected_preferred_names)
        # 필수 과목명별로 선택 가능한 분반 목록을 만든다.
        required_options = {
            name: tuple(
                lecture
                for lecture in self.catalog.by_subject_name(name)
                if lecture.id not in request.required_lecture_ids and self._can_add(initial, lecture)
            )
            for name in required_choice_names
        }
        unsatisfied_required = [name for name, options in required_options.items() if not options]
        for name in unsatisfied_required:
            warnings.append(f"학년 필수 과목 '{name}'의 선택 가능한 분반을 찾지 못했습니다.")

        if unsatisfied_required:
            # 필수 과목 분반이 하나도 없으면 선택 과목 탐색을 시작하지 않는다.
            warnings.append("필수 과목 분반 선택 단계에서 막혀 시간표를 만들지 못했습니다.")
            return ScheduleResult((), (), SearchStats(), tuple(warnings))

        # 분반 수가 적은 필수 과목부터 골라 백트래킹 가지 수를 줄인다.
        required_names_ordered = sorted(required_choice_names, key=lambda name: len(required_options[name]))
        optional_pool = [
            lecture
            for lecture in self.catalog.all()
            if lecture.id not in request.required_lecture_ids
            and lecture.subject.name not in request.required_subject_names
            and lecture.id not in request.excluded_lecture_ids
            and self._can_add(initial, lecture)
        ]
        group_ids = frozenset(course_id for group in request.alternative_groups for course_id in group)
        optional_ranked = sorted(
            optional_pool,
            key=lambda lecture: optional_priority(lecture, request.candidate_lecture_ids, group_ids),
            reverse=True,
        )
        suffix_credits = suffix_credit_capacity([lecture.subject.credits for lecture in optional_ranked])
        suffix_group_cover = suffix_alternative_group_cover([lecture.id for lecture in optional_ranked], request.alternative_groups)
        optimizer = TopNOptimizer(request.top_n)
        candidate_count = 0
        explored_states = 0
        search_limit_hit = False

        def push_candidate(schedule: Schedule) -> None:
            nonlocal candidate_count
            if not self._is_satisfied(schedule):
                return
            candidate_count += 1
            if self.score_legacy_callback:
                # 기존 딕셔너리 기반 점수 계산과 화면 출력 형식을 그대로 재사용한다.
                scored = self.score_legacy_callback(
                    sorted(schedule.raw_courses(), key=_legacy_course_sort_key),
                    set(request.candidate_lecture_ids),
                    [set(group) for group in request.alternative_groups],
                )
            else:
                scored = {
                    "courses": schedule.raw_courses(),
                    "score": 1000.0,
                    "sort_key": (1000.0,),
                    "total_credits": schedule.credits,
                }
            optimizer.push(scored)

        def search_optional(start_index: int, schedule: Schedule) -> None:
            nonlocal explored_states, search_limit_hit
            explored_states += 1
            if request.max_states is not None and explored_states > request.max_states:
                search_limit_hit = True
                return

            if schedule.credits >= request.min_credits:
                push_candidate(schedule)

            if start_index >= len(optional_ranked) or schedule.credits >= request.max_credits:
                return
            if schedule.credits + suffix_credits[start_index] < request.min_credits:
                # 남은 과목을 모두 더해도 최소 학점에 못 미치면 더 탐색하지 않는다.
                return

            uncovered_groups = {
                group_index for group_index, group in enumerate(request.alternative_groups) if not group.intersection(schedule.lecture_ids)
            }
            if not uncovered_groups.issubset(suffix_group_cover[start_index]):
                # 남은 후보로 채울 수 없는 대체 그룹이 있으면 현재 가지를 버린다.
                return

            for next_index in range(start_index, len(optional_ranked)):
                lecture = optional_ranked[next_index]
                if schedule.credits + lecture.subject.credits > request.max_credits:
                    continue
                if lecture.subject.name in schedule.subject_names:
                    continue
                if schedule.time_mask and lecture.time_mask and schedule.time_mask & lecture.time_mask:
                    # 비트마스크 충돌 검사는 가장 빠른 시간 겹침 필터이다.
                    continue
                if not self._can_add(schedule, lecture):
                    continue
                search_optional(next_index + 1, schedule.add(lecture))
                if search_limit_hit:
                    return

        def search_required(index: int, schedule: Schedule) -> None:
            nonlocal search_limit_hit
            if schedule.credits > request.max_credits:
                return
            if index == len(required_names_ordered):
                search_optional(0, schedule)
                return

            name = required_names_ordered[index]
            for lecture in required_options[name]:
                if not self._can_add(schedule, lecture):
                    continue
                search_required(index + 1, schedule.add(lecture))
                if search_limit_hit:
                    return

        if self._initial_schedule_is_viable(initial):
            search_required(0, initial)
        else:
            warnings.append("오류: 장바구니(필수) 과목끼리 충돌하거나 중복되어 시간표를 만들 수 없습니다.")

        scored_candidates = optimizer.results()
        if not scored_candidates:
            if request.alternative_groups:
                warnings.append("현재 조건에서 각 대체 그룹마다 하나 이상 포함하는 시간표를 찾지 못했습니다.")
            else:
                warnings.append("현재 조건(학점, 학년 등)을 모두 만족하는 시간표 조합이 존재하지 않습니다.")
        if search_limit_hit:
            warnings.append("탐색 상태 제한에 도달해 일부 조합을 확인하지 못했습니다.")

        schedules = tuple(Schedule(tuple()) for _ in scored_candidates)
        return ScheduleResult(
            schedules=schedules,
            scored_candidates=tuple(scored_candidates),
            stats=SearchStats(
                explored_states=explored_states,
                candidate_count=candidate_count,
                search_limit_hit=search_limit_hit,
            ),
            warnings=tuple(warnings),
        )

    def _can_add(self, schedule: Schedule, lecture: Lecture) -> bool:
        return all(constraint.can_add(schedule, lecture) for constraint in self.hard_constraints)

    def _is_satisfied(self, schedule: Schedule) -> bool:
        return all(constraint.is_satisfied(schedule) for constraint in self.hard_constraints)

    def _initial_schedule_is_viable(self, schedule: Schedule) -> bool:
        selected = Schedule()
        for lecture in schedule.lectures:
            if not self._can_add(selected, lecture):
                return False
            selected = selected.add(lecture)
        return True


def _legacy_course_sort_key(course: dict) -> tuple:
    meetings = course.get("meetings", [])
    first = min((meeting["day_index"] * 1440 + meeting["start"] for meeting in meetings), default=24 * 60)
    return first, course.get("name", ""), course.get("course_id", "")
