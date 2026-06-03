from __future__ import annotations

import re

from src.domain.academic import AcademicTarget
from src.domain.models import CourseCategory, Lecture, Subject, TimeSlot


ALIASES = {
    "AI소프트웨어": "AI소프트웨어학부",
    "AI소프트": "AI소프트웨어학부",
    "소프트웨어학부": "AI소프트웨어학부",
    "소프트웨어전공": "소프트웨어전공",
    "AI융합전공": "AI융합전공",
}


from src.domain.models import DAY_ORDER, DAY_MAP


def normalize_department_name(value: str) -> str:
    text = str(value).strip()
    # 학교 자료에서 줄여 쓰는 학과명을 대표 이름으로 통일한다.
    return ALIASES.get(text, text)


def parse_meetings(time_raw: str) -> list[dict]:
    meetings = []
    for raw_line in str(time_raw).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # 한 셀 안에 여러 강의 시간이 쉼표/세미콜론으로 들어올 수 있다.
        parts = [part.strip() for part in re.split(r"[,;]", line) if part.strip()]
        for part in parts:
            match = re.search(r"([월화수목금 ]+)\s+(\d{2}:\d{2})-(\d{2}:\d{2})", part)
            if not match:
                continue
            # 월수처럼 요일이 붙어 있으면 각 요일별 수업 시간 항목으로 나눈다.
            days = [day for day in DAY_ORDER if day in match.group(1)]
            start = to_minutes(match.group(2))
            end = to_minutes(match.group(3))
            location_match = re.search(r"\((.+)\)", part)
            location = location_match.group(1) if location_match else ""
            for day in days:
                meetings.append(
                    {
                        "day": day,
                        "day_index": DAY_MAP[day],
                        "start": start,
                        "end": end,
                        "location": location,
                    }
                )
    return meetings


def to_minutes(value: str) -> int:
    try:
        hours, minutes = value.split(":")
        return int(hours) * 60 + int(minutes)
    except Exception:
        return 0


def extract_credits(value: str) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)", str(value))
    return float(match.group(1)) if match else 0.0


def extract_grades(target_raw: str) -> list[str]:
    text = str(target_raw)
    if "전체" in text:
        # 전체학년 표기는 모든 학년을 대상으로 확장한다.
        return ["1", "2", "3", "4"]
    return sorted(set(re.findall(r"([1-4])학년", text)))


def required_course_names(curriculum_required: dict, grade: str | None, semester: str | None) -> set[str]:
    # 전체 선택이면 모든 학년/학기를 대상으로 필수 과목을 모은다.
    grades = ["1", "2", "3", "4"] if grade in {None, "전체"} else [str(grade)]
    semesters = ["1", "2"] if semester in {None, "전체"} else [str(semester)]
    result = set()
    for grade_key in grades:
        for semester_key in semesters:
            result.update(item["name"] for item in curriculum_required.get(grade_key, {}).get(semester_key, []))
    return result


def build_time_mask(meetings: list[dict]) -> int:
    mask = 0
    for meeting in meetings:
        day_offset = meeting["day_index"] * 1440
        for minute in range(meeting["start"], meeting["end"]):
            # 요일별 분 단위를 하나의 정수 비트 위치로 표현한다.
            mask |= 1 << (day_offset + minute)
    return mask


def legacy_course_to_lecture(course: dict) -> Lecture:
    target_raw = str(course.get("target_raw", ""))
    target_grades = course.get("target_grades", [])
    # 원본 수강대상 문자열을 생성 제약에서 사용할 도메인 객체로 변환한다.
    target = AcademicTarget.from_raw(target_raw, target_grades=target_grades)

    slots = tuple(
        TimeSlot(
            day=meeting["day"],
            start_minute=int(meeting["start"]),
            end_minute=int(meeting["end"]),
            location=str(meeting.get("location", "")),
        )
        for meeting in course.get("meetings", [])
    )
    category = str(course.get("category", CourseCategory.OTHER.value))
    # 과목 정보와 분반 정보를 나누어 엔진의 중복 과목 검사를 단순하게 한다.
    subject = Subject(
        code=str(course.get("course_id", "")),
        name=str(course.get("name", "")),
        category=category,
        credits=float(course.get("credits", 0.0)),
        area=str(course.get("area", "")),
    )
    return Lecture(
        id=str(course.get("course_id", "")),
        subject=subject,
        professor=str(course.get("professor", "")),
        seats=int(course.get("seats", 0) or 0),
        target_raw=target_raw,
        target=target,
        time_slots=slots,
        source=str(course.get("source", "")),
        raw=course,
    )


def legacy_courses_to_lectures(courses: list[dict]) -> tuple[Lecture, ...]:
    return tuple(legacy_course_to_lecture(course) for course in courses)
