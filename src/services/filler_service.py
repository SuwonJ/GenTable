from __future__ import annotations


def recommend_fillers(
    catalog: dict,
    base_courses: list[dict],
    failed_course_names: list[str],
    max_results: int,
):
    import pandas as pd

    # 실패하지 않은 과목은 그대로 유지하고 이들과 충돌하는 후보를 막는다.
    remaining_courses = [course for course in base_courses if course["name"] not in failed_course_names]
    blocked_ids = {course["course_id"] for course in remaining_courses}
    # 실패한 과목이 비운 시간대를 대체 강의 추천 기준으로 사용한다.
    free_blocks = _freed_time_blocks(base_courses, failed_course_names)

    rows = []
    for course in catalog["courses"]:
        if course["course_id"] in blocked_ids or course["name"] in failed_course_names:
            continue
        if _has_conflict(course, remaining_courses):
            continue
        # 빈 시간대와 많이 겹칠수록 기존 시간표 형태를 덜 흔든다.
        overlap_score = sum(_overlap_minutes(meeting, block) for meeting in course["meetings"] for block in free_blocks)
        if overlap_score <= 0:
            continue
        rows.append(
            {
                "과목명": course["name"],
                "과목번호": course["course_id"],
                "이수구분": course["category_label"],
                "교수명": course["professor"],
                "학점": course["credits"],
                "강의시간": course["time_raw"],
                "여석": course["seats"],
                # 여석이 많을수록 실제 신청 가능성이 높다고 보고 점수를 보정한다.
                "추천점수": overlap_score + course["seats"] * 3,
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    # 추천점수 우선, 동점이면 여석이 많은 강의를 먼저 보여준다.
    return frame.sort_values(["추천점수", "여석"], ascending=False).head(max_results)


def _has_conflict(course: dict, selected: list[dict]) -> bool:
    mask = course.get("time_mask", 0)
    # 기존 시간표와 겹치는 후보는 대체 추천에서 제외한다.
    return any(mask & other.get("time_mask", 0) for other in selected)


def _freed_time_blocks(base_courses: list[dict], failed_course_names: list[str]) -> list[dict]:
    blocks = []
    for course in base_courses:
        if course["name"] in failed_course_names:
            blocks.extend(course["meetings"])
    return blocks


def _overlap_minutes(meeting: dict, block: dict) -> int:
    if meeting["day"] != block["day"]:
        return 0
    return max(0, min(meeting["end"], block["end"]) - max(meeting["start"], block["start"]))
