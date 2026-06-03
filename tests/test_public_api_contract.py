import inspect
import unittest

import src.scheduler as scheduler


def make_course(course_id: str, name: str, day: str, start: int, end: int) -> dict:
    # 실제 로더 결과와 같은 필드 구성을 가진 테스트 강의를 만든다.
    return {
        "source": "contract",
        "course_id": course_id,
        "name": name,
        "category_raw": "전선",
        "category": "major_elective",
        "category_label": "전선",
        "area": "",
        "professor": "교수",
        "credits": 3.0,
        "seats": 10,
        "time_raw": f"{day} {start // 60:02d}:{start % 60:02d}-{end // 60:02d}:{end % 60:02d}",
        "target_raw": "전체학년 전체",
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


class PublicSchedulerApiContractTests(unittest.TestCase):
    def test_scheduler_facade_exports_only_public_entrypoints(self) -> None:
        # 공개 모듈은 외부 호출에 필요한 함수만 노출해야 한다.
        public_functions = {
            name
            for name, value in vars(scheduler).items()
            if inspect.isfunction(value) and not name.startswith("_")
        }
        self.assertEqual({"generate_timetables", "recommend_fillers", "timetable_to_frame"}, public_functions)
        self.assertEqual(["generate_timetables", "recommend_fillers", "timetable_to_frame"], scheduler.__all__)

    def test_generate_timetables_result_shape_and_ordering_contract(self) -> None:
        # 오전 회피 가중치가 있을 때 늦은 수업이 먼저 오는지 확인한다.
        early = make_course("900000-01", "아침수업", "월", 540, 630)
        late = make_course("900001-01", "늦은수업", "월", 660, 750)
        catalog = {"courses": [early, late], "curriculum_required": {}, "warnings": ["원본 경고"]}

        candidates, info = scheduler.generate_timetables(
            catalog=catalog,
            grade="전체",
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
            top_n=2,
            weights={"prefer_free_day": 0, "avoid_morning": 5, "avoid_gap": 0},
            filter_state={},
        )

        self.assertEqual([1, 2], [candidate["rank"] for candidate in candidates])
        self.assertEqual(late["course_id"], candidates[0]["courses"][0]["course_id"])
        for key in [
            "courses",
            "score",
            "sort_key",
            "total_credits",
            "free_days",
            "nine_am_count",
            "gap_count",
            "morning_count",
            "morning_penalty",
            "gap_minutes",
            "rank",
        ]:
            # 화면 표시가 의존하는 결과 키는 빠지면 안 된다.
            self.assertIn(key, candidates[0])
        # 원본 경고는 생성 결과 정보에 그대로 전달되어야 한다.
        self.assertIn("원본 경고", info["warnings"])
        self.assertEqual(2, info["candidate_count"])


if __name__ == "__main__":
    unittest.main()
