import unittest

from src.engine import DEFAULT_MAX_STATES, ScheduleRequest, optional_priority, score_candidate
from src.domain.models import StudentProfile
from src.filters import course_matches_filters, matches_target_department, matches_target_grade
from src.ingestion import legacy_course_to_lecture
from src.services.scheduler_service import generate_timetables


def make_course(
    course_id: str,
    name: str,
    day: str,
    start: int,
    end: int,
    *,
    category: str = "major_elective",
    category_label: str = "전선",
    target_raw: str = "전체학년 전체",
    professor: str = "교수",
    credits: float = 3.0,
    seats: int = 10,
) -> dict:
    # 실제 강의 목록과 같은 키를 가진 테스트 강의를 만든다.
    return {
        "source": "test",
        "course_id": course_id,
        "name": name,
        "category_raw": category_label,
        "category": category,
        "category_label": category_label,
        "area": "",
        "professor": professor,
        "credits": credits,
        "seats": seats,
        "time_raw": f"{day} {start // 60:02d}:{start % 60:02d}-{end // 60:02d}:{end % 60:02d}",
        "target_raw": target_raw,
        "target_grades": [],
        "meetings": [
            {
                "day": day,
                "day_index": ["월", "화", "수", "목", "금"].index(day),
                "start": start,
                "end": end,
                "location": "",
            }
        ],
    }


class SchedulerFilterTests(unittest.TestCase):
    def test_schedule_request_uses_default_state_limit(self) -> None:
        # 요청에 제한값을 넣지 않으면 기본 탐색 한도를 사용한다.
        request = ScheduleRequest(
            profile=StudentProfile(),
            min_credits=3,
            max_credits=18,
            required_lecture_ids=frozenset(),
            required_subject_names=frozenset(),
            candidate_lecture_ids=frozenset(),
            excluded_lecture_ids=frozenset(),
            alternative_groups=tuple(),
            top_n=5,
        )
        self.assertEqual(DEFAULT_MAX_STATES, request.max_states)

    def test_optional_priority_prefers_later_start(self) -> None:
        early = legacy_course_to_lecture(make_course("090000-01", "이른강의", "월", 540, 630))
        late = legacy_course_to_lecture(make_course("090001-01", "늦은강의", "월", 780, 870))
        self.assertGreater(
            optional_priority(late, frozenset(), frozenset()),
            optional_priority(early, frozenset(), frozenset()),
        )

    def test_open_department_target_matches_shared_filter(self) -> None:
        course = make_course("100000-01", "자료구조", "월", 540, 630, target_raw="전체학년 전체")
        filters = {
            "target_departments": ["AI소프트웨어학부"],
            "target_grades": [],
            "category_filters": [],
            "day_filters": [],
            "time_filter": "전체",
            "hide_foreign_only": False,
            "target_include_regex": "",
            "target_exclude_regex": "",
        }
        self.assertTrue(course_matches_filters(course, filters))

    def test_target_grade_filter_accepts_numeric_profile_grade(self) -> None:
        self.assertTrue(matches_target_grade("AI소프트웨어학부 2학년", ["2"]))
        self.assertTrue(matches_target_grade("AI소프트웨어학부 2학년", ["2학년"]))
        self.assertFalse(matches_target_grade("AI소프트웨어학부 3학년", ["2"]))

    def test_target_department_filter_applies_aliases(self) -> None:
        self.assertTrue(matches_target_department("AI소프트 2학년", ["AI소프트웨어학부"]))
        self.assertTrue(matches_target_department("AI소프트웨어학부 2학년", ["AI소프트"]))
        self.assertFalse(matches_target_department("컴퓨터학부 2학년", ["AI소프트"]))

    def test_generate_timetable_applies_profile_target_filter(self) -> None:
        # 학년과 학과 조건이 모두 맞는 강의만 생성 후보에 남아야 한다.
        eligible = make_course(
            "100010-01",
            "프로필대상",
            "월",
            540,
            630,
            target_raw="AI소프트웨어학부 2학년",
        )
        other_grade = make_course(
            "100011-01",
            "타학년",
            "화",
            540,
            630,
            target_raw="AI소프트웨어학부 3학년",
        )
        other_department = make_course(
            "100012-01",
            "타학과",
            "수",
            540,
            630,
            target_raw="컴퓨터학부 2학년",
        )
        catalog = {
            "courses": [eligible, other_grade, other_department],
            "curriculum_required": {},
            "warnings": [],
        }

        candidates, info = generate_timetables(
            catalog=catalog,
            grade="2",
            semester="전체",
            include_regex="",
            exclude_regex="",
            preferred_ids=set(),
            candidate_ids=set(),
            excluded_ids=set(),
            alternative_groups=[],
            min_credits=3,
            max_credits=3,
            elective_count=0,
            top_n=5,
            weights={"prefer_free_day": 1, "avoid_morning": 1, "avoid_gap": 1},
            filter_state={"target_departments": ["AI소프트웨어학부"]},
        )

        self.assertTrue(candidates, msg=info)
        first_ids = {course["course_id"] for course in candidates[0]["courses"]}
        self.assertEqual({eligible["course_id"]}, first_ids)

    def test_generate_timetable_satisfies_alternative_group(self) -> None:
        # 대체 그룹이 있으면 그룹 안의 강의가 하나 이상 포함되어야 한다.
        preferred = make_course("100000-01", "알고리즘", "월", 540, 630, category="major_required", category_label="전필")
        group_a = make_course("100001-01", "웹프로그래밍", "화", 540, 630)
        group_b = make_course("100002-01", "모바일프로그래밍", "수", 540, 630)
        filler = make_course("100003-01", "교양영어", "목", 540, 630, category="general_required", category_label="교필")
        catalog = {
            "courses": [preferred, group_a, group_b, filler],
            "curriculum_required": {},
            "warnings": [],
        }

        candidates, info = generate_timetables(
            catalog=catalog,
            grade="전체",
            semester="전체",
            include_regex="",
            exclude_regex="",
            preferred_ids={preferred["course_id"]},
            candidate_ids=set(),
            excluded_ids=set(),
            alternative_groups=[{group_a["course_id"], group_b["course_id"]}],
            min_credits=6,
            max_credits=9,
            elective_count=2,
            top_n=5,
            weights={"prefer_free_day": 1, "avoid_morning": 1, "avoid_gap": 1},
            filter_state={},
        )

        self.assertTrue(candidates, msg=info)
        first_ids = {course["course_id"] for course in candidates[0]["courses"]}
        self.assertIn(preferred["course_id"], first_ids)
        self.assertTrue(
            {group_a["course_id"], group_b["course_id"]}.intersection(first_ids),
            msg=first_ids,
        )

    def test_generate_timetable_selects_only_one_per_alternative_group(self) -> None:
        group_a = make_course("100101-01", "그룹A", "월", 540, 630)
        group_b = make_course("100102-01", "그룹B", "화", 540, 630)
        other_c = make_course("100103-01", "선택C", "수", 540, 630)
        other_d = make_course("100104-01", "선택D", "목", 540, 630)
        catalog = {
            "courses": [group_a, group_b, other_c, other_d],
            "curriculum_required": {},
            "warnings": [],
        }

        candidates, info = generate_timetables(
            catalog=catalog,
            grade="전체",
            semester="전체",
            include_regex="",
            exclude_regex="",
            preferred_ids=set(),
            candidate_ids=set(),
            excluded_ids=set(),
            alternative_groups=[{group_a["course_id"], group_b["course_id"]}],
            min_credits=9,
            max_credits=9,
            elective_count=2,
            top_n=10,
            weights={"prefer_free_day": 0, "avoid_morning": 0, "avoid_gap": 0},
            filter_state={},
        )

        self.assertTrue(candidates, msg=info)
        group_ids = {group_a["course_id"], group_b["course_id"]}
        for candidate in candidates:
            selected = {course["course_id"] for course in candidate["courses"]}
            self.assertEqual(1, len(group_ids.intersection(selected)), msg=selected)

    def test_generate_timetable_does_not_fail_when_elective_count_zero(self) -> None:
        course_a = make_course("200000-01", "이산수학", "월", 540, 630)
        course_b = make_course("200001-01", "프로그래밍기초", "화", 540, 630)
        course_c = make_course("200002-01", "컴퓨팅사고", "수", 540, 630)
        catalog = {
            "courses": [course_a, course_b, course_c],
            "curriculum_required": {},
            "warnings": [],
        }

        candidates, info = generate_timetables(
            catalog=catalog,
            grade="전체",
            semester="전체",
            include_regex="",
            exclude_regex="",
            preferred_ids=set(),
            candidate_ids=set(),
            excluded_ids=set(),
            alternative_groups=[{course_a["course_id"], course_b["course_id"]}],
            min_credits=6,
            max_credits=9,
            elective_count=0,
            top_n=5,
            weights={"prefer_free_day": 1, "avoid_morning": 1, "avoid_gap": 1},
            filter_state={},
        )

        self.assertTrue(candidates, msg=info)

    def test_generate_timetable_ignores_empty_alternative_group_after_catalog_sync(self) -> None:
        valid = make_course("210000-01", "유효그룹", "월", 540, 630)
        catalog = {
            "courses": [valid],
            "curriculum_required": {},
            "warnings": [],
        }

        candidates, info = generate_timetables(
            catalog=catalog,
            grade="전체",
            semester="전체",
            include_regex="",
            exclude_regex="",
            preferred_ids=set(),
            candidate_ids=set(),
            excluded_ids=set(),
            alternative_groups=[{valid["course_id"]}, {"99999999"}],
            min_credits=3,
            max_credits=3,
            elective_count=0,
            top_n=3,
            weights={"prefer_free_day": 0, "avoid_morning": 0, "avoid_gap": 0},
            filter_state={},
        )

        self.assertTrue(candidates, msg=info)
        self.assertTrue(
            any("그룹 제약에서 제외" in warning for warning in info["warnings"]),
            msg=info["warnings"],
        )

    def test_score_candidate_prefers_later_start_when_morning_avoidance_enabled(self) -> None:
        # 오전 회피 점수는 늦게 시작하는 후보에 유리하게 작동해야 한다.
        early = [make_course("300000-01", "아침수업", "월", 540, 630)]
        late = [make_course("300001-01", "늦은수업", "월", 660, 750)]
        weights = {"prefer_free_day": 0, "avoid_morning": 5, "avoid_gap": 0}

        early_score = score_candidate(early, weights, set(), [])
        late_score = score_candidate(late, weights, set(), [])

        self.assertGreater(late_score["score"], early_score["score"])
        self.assertGreater(early_score["morning_penalty"], late_score["morning_penalty"])

    def test_score_candidate_penalizes_each_morning_day(self) -> None:
        multi_day_morning = make_course("310000-01", "다일아침", "월", 540, 630)
        multi_day_morning["meetings"].append(
            {"day": "화", "day_index": 1, "start": 540, "end": 630, "location": ""}
        )
        single_day_morning = make_course("310001-01", "단일아침", "월", 540, 630)
        weights = {"prefer_free_day": 0, "avoid_morning": 5, "avoid_gap": 0}

        multi_score = score_candidate([multi_day_morning], weights, set(), [])
        single_score = score_candidate([single_day_morning], weights, set(), [])

        self.assertGreater(multi_score["nine_am_count"], single_score["nine_am_count"])
        self.assertGreater(multi_score["morning_penalty"], single_score["morning_penalty"])
        self.assertLess(multi_score["score"], single_score["score"])

    def test_generate_timetable_prefers_later_optional_course(self) -> None:
        fixed = make_course("400000-01", "고정과목", "화", 780, 870)
        early = make_course("400001-01", "이른선택", "월", 540, 630)
        late = make_course("400002-01", "늦은선택", "월", 660, 750)
        catalog = {
            "courses": [fixed, early, late],
            "curriculum_required": {},
            "warnings": [],
        }

        candidates, info = generate_timetables(
            catalog=catalog,
            grade="전체",
            semester="전체",
            include_regex="",
            exclude_regex="",
            preferred_ids={fixed["course_id"]},
            candidate_ids=set(),
            excluded_ids=set(),
            alternative_groups=[],
            min_credits=6,
            max_credits=6,
            elective_count=2,
            top_n=3,
            weights={"prefer_free_day": 0, "avoid_morning": 5, "avoid_gap": 0},
            filter_state={},
        )

        self.assertTrue(candidates, msg=info)
        first_ids = {course["course_id"] for course in candidates[0]["courses"]}
        self.assertIn(late["course_id"], first_ids)
        self.assertNotIn(early["course_id"], first_ids)

    def test_generate_timetable_includes_legacy_score_metrics(self) -> None:
        course_a = make_course("410000-01", "강의A", "월", 600, 690)
        course_b = make_course("410001-01", "강의B", "화", 600, 690)
        catalog = {
            "courses": [course_a, course_b],
            "curriculum_required": {},
            "warnings": [],
        }

        candidates, info = generate_timetables(
            catalog=catalog,
            grade="전체",
            semester="전체",
            include_regex="",
            exclude_regex="",
            preferred_ids=set(),
            candidate_ids=set(),
            excluded_ids=set(),
            alternative_groups=[],
            min_credits=6,
            max_credits=6,
            elective_count=0,
            top_n=3,
            weights={"prefer_free_day": 1, "avoid_morning": 1, "avoid_gap": 1},
            filter_state={},
        )

        self.assertTrue(candidates, msg=info)
        first = candidates[0]
        self.assertIn("free_days", first)
        self.assertIn("gap_count", first)
        self.assertIn("morning_penalty", first)

    def test_sort_key_prioritizes_zero_nine_am_courses(self) -> None:
        # 정렬 기준은 아홉시 수업이 없는 후보를 먼저 선택해야 한다.
        weights = {"prefer_free_day": 5, "avoid_morning": 5, "avoid_gap": 5}
        no_nine = [
            make_course("500000-01", "점심수업", "월", 720, 810),
            make_course("500000-02", "오후수업", "화", 780, 870),
        ]
        with_nine = [
            make_course("500001-01", "아홉시수업", "월", 540, 630),
            make_course("500001-02", "공강좋음", "수", 780, 870),
        ]

        no_nine_score = score_candidate(no_nine, weights, set(), [])
        with_nine_score = score_candidate(with_nine, weights, set(), [])

        self.assertEqual(no_nine_score["nine_am_count"], 0)
        self.assertEqual(with_nine_score["nine_am_count"], 1)
        self.assertGreater(no_nine_score["sort_key"], with_nine_score["sort_key"])


if __name__ == "__main__":
    unittest.main()
