from __future__ import annotations

import re

from src.ingestion import normalize_department_name


SPECIAL_POPULATION_MARKERS = ["순수외국인입학생", "외국인", "교환학생", "중국국적학생"]
FOREIGN_MARKERS = ["외국인", "교환학생", "중국국적학생"]
TARGET_GRADE_LABELS = ["1학년", "2학년", "3학년", "4학년"]


def normalize_target_grade(value: str) -> str:
    text = str(value).strip()
    if text in {"1", "2", "3", "4"}:
        return f"{text}학년"
    return text


def normalize_target_grades(values: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    return [normalize_target_grade(value) for value in values if str(value).strip()]


def regex_match(text: str, pattern: str) -> bool:
    try:
        return bool(pattern and re.search(pattern, text))
    except Exception:
        # 잘못된 정규식은 앱을 멈추지 않고 불일치로 처리한다.
        return False


def extract_target_departments(target_raw: str) -> set[str]:
    found = set()
    tokens = re.split(r"[,/ \n\t]+", target_raw)
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        # 학과/학부처럼 보이는 토큰만 수강대상 학과로 추출한다.
        if any(suffix in token for suffix in ["학부", "학과", "전공", "공학", "융합"]) or any(
            keyword in token for keyword in ["소프트웨어", "글로벌미디어", "AI소프트", "컴퓨터"]
        ):
            if "제외" not in token:
                normalized = normalize_department_name(re.sub(r"[\(\)]", "", token).strip())
                if normalized:
                    found.add(normalized)
    return found


def extract_excluded_departments(target_raw: str) -> set[str]:
    found = set()
    tokens = re.split(r"[,/ \n\t]+", target_raw)
    for token in tokens:
        if "제외" not in token:
            continue
        # 괄호와 제외 표기를 제거해 실제 학과명만 남긴다.
        clean = re.sub(r"[\(\)제외]", "", token).strip()
        if clean:
            found.add(normalize_department_name(clean))
    return found


def has_foreign_marker(target_raw: str) -> bool:
    return any(marker in target_raw for marker in FOREIGN_MARKERS)


def is_special_population_only(target_raw: str) -> bool:
    if not any(marker in target_raw for marker in SPECIAL_POPULATION_MARKERS):
        return False
    allowed_departments = extract_target_departments(target_raw)
    # 특정 학과도 함께 적힌 경우에는 특수 대상 전용으로만 보지 않는다.
    return not allowed_departments


def is_open_department_target(target_raw: str) -> bool:
    text = target_raw.strip()
    if "전체학년 전체" in text or "전체 " in text or text.endswith("전체") or "(전체)" in text:
        return True
    return text in {"전체학년", "전체학년 전체"}


def matches_target_grade(target_raw: str, target_grades: list[str]) -> bool:
    if is_special_population_only(target_raw):
        return False
    if "전체학년" in target_raw:
        return True
    normalized_grades = normalize_target_grades(target_grades)
    return any(grade in target_raw for grade in normalized_grades)


def matches_target_department(target_raw: str, departments: list[str]) -> bool:
    # 화면 입력 학과명을 원문 추출 학과명과 같은 별칭 체계로 맞춘다.
    normalized_departments = {
        normalize_department_name(str(department).strip())
        for department in departments
        if str(department).strip()
    }
    if not normalized_departments:
        return True
    if is_special_population_only(target_raw):
        return False
    excluded = extract_excluded_departments(target_raw)
    if excluded.intersection(normalized_departments):
        return False
    if is_open_department_target(target_raw):
        # 전체 대상 강의는 학과 필터를 통과시킨다.
        return True
    found = extract_target_departments(target_raw)
    return bool(found.intersection(normalized_departments))


def course_search_text(course: dict) -> str:
    parts = [
        course.get("name", ""),
        course.get("professor", ""),
        course.get("course_id", ""),
        course.get("area", ""),
        course.get("category_label", ""),
        course.get("target_raw", ""),
        course.get("time_raw", ""),
    ]
    return "\n".join(str(part) for part in parts if part)


def course_matches_filters(course: dict, filters: dict) -> bool:
    if filters.get("category_filters") and course["category"] not in filters["category_filters"]:
        return False

    if filters.get("day_filters"):
        # 강의가 여러 요일에 열리면 그중 하나만 맞아도 통과한다.
        course_days = {meeting["day"] for meeting in course["meetings"]}
        if not course_days.intersection(filters["day_filters"]):
            return False

    start_min = min(meeting["start"] for meeting in course["meetings"])
    time_filter = filters.get("time_filter", "전체")
    if time_filter == "오전만" and start_min >= 12 * 60:
        return False
    if time_filter == "오후만" and start_min < 12 * 60:
        return False
    if time_filter == "저녁 제외" and start_min >= 18 * 60:
        return False

    target_raw = course["target_raw"]
    if filters.get("target_grades") and not matches_target_grade(target_raw, filters["target_grades"]):
        return False
    if filters.get("target_departments") and not matches_target_department(target_raw, filters["target_departments"]):
        return False
    if filters.get("hide_foreign_only") and has_foreign_marker(target_raw):
        return False
    if filters.get("target_include_regex") and not regex_match(target_raw, filters["target_include_regex"]):
        return False
    if filters.get("target_exclude_regex") and regex_match(target_raw, filters["target_exclude_regex"]):
        return False

    full_text = course_search_text(course)
    if filters.get("include_regex") and not regex_match(full_text, filters["include_regex"]):
        return False
    if filters.get("exclude_regex") and regex_match(full_text, filters["exclude_regex"]):
        return False

    return True


def search_score(course: dict, keywords: list[str]) -> int:
    haystacks = {
        "name": course["name"].lower(),
        "professor": course["professor"].lower(),
        "course_id": course["course_id"].lower(),
        "area": course["area"].lower(),
        "category": course["category_label"].lower(),
        "target": course["target_raw"].lower(),
        "time": course["time_raw"].lower(),
    }
    if not keywords:
        return 1

    score = 0
    for keyword in keywords:
        matched = False
        if keyword in haystacks["name"]:
            # 과목명 일치는 검색 의도가 가장 강하므로 높은 점수를 준다.
            score += 12
            matched = True
        if keyword in haystacks["professor"]:
            score += 8
            matched = True
        if keyword in haystacks["course_id"]:
            score += 10
            matched = True
        if keyword in haystacks["area"]:
            score += 7
            matched = True
        if keyword in haystacks["category"]:
            score += 7
            matched = True
        if keyword in haystacks["target"]:
            score += 5
            matched = True
        if keyword in haystacks["time"]:
            score += 4
            matched = True
        if not matched:
            # 모든 키워드를 포함해야 검색 결과에 남긴다.
            return 0
    return score
