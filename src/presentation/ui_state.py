from __future__ import annotations

import json
import re
from html import escape

import streamlit as st

from src.filters import (
    course_matches_filters,
    extract_excluded_departments,
    extract_target_departments,
    has_foreign_marker,
    is_open_department_target,
    normalize_target_grade,
    regex_match,
    search_score,
)


from src.domain.models import DAY_ORDER
TOP_N_MIN = 3
TOP_N_MAX = 30


def default_controls() -> dict:
    return {
        "grade": "전체",
        "semester": "전체",
        "department": "전체",
        "include_regex": "",
        "exclude_regex": "",
        "min_credits": 16,
        "max_credits": 20,
        "elective_count": 2,
        "top_n": 15,
        "weights": {
            "prefer_free_day": 3,
            "avoid_morning": 2,
            "avoid_gap": 3,
        },
    }


def sanitize_controls(controls: dict | None) -> dict:
    sanitized = default_controls()
    if not isinstance(controls, dict):
        return sanitized

    # 저장 파일에서 읽은 값은 화면 위젯 범위 안으로 제한한다.
    sanitized["grade"] = controls.get("grade", sanitized["grade"])
    sanitized["semester"] = controls.get("semester", sanitized["semester"])
    sanitized["department"] = str(controls.get("department", sanitized["department"]))
    sanitized["include_regex"] = str(controls.get("include_regex", sanitized["include_regex"]))
    sanitized["exclude_regex"] = str(controls.get("exclude_regex", sanitized["exclude_regex"]))
    sanitized["min_credits"] = max(0, min(21, int(controls.get("min_credits", sanitized["min_credits"]))))
    sanitized["max_credits"] = max(6, min(24, int(controls.get("max_credits", sanitized["max_credits"]))))
    sanitized["elective_count"] = max(0, min(4, int(controls.get("elective_count", sanitized["elective_count"]))))
    sanitized["top_n"] = max(TOP_N_MIN, min(TOP_N_MAX, int(controls.get("top_n", sanitized["top_n"]))))
    if sanitized["min_credits"] > sanitized["max_credits"]:
        # 최소/최대 학점이 뒤집힌 저장값은 자동으로 교정한다.
        sanitized["min_credits"], sanitized["max_credits"] = sanitized["max_credits"], sanitized["min_credits"]

    saved_weights = controls.get("weights", {})
    if isinstance(saved_weights, dict):
        for key in sanitized["weights"]:
            sanitized["weights"][key] = max(0, min(5, int(saved_weights.get(key, sanitized["weights"][key]))))
    return sanitized


def ensure_state() -> None:
    # 선택 버킷은 앱 전체에서 공유하므로 세션 상태에 한 번만 만든다.
    st.session_state.setdefault("preferred_ids", set())
    st.session_state.setdefault("candidate_ids", set())
    st.session_state.setdefault("excluded_ids", set())
    if "alternative_groups" not in st.session_state:
        st.session_state.alternative_groups = {
            "group_1": {"name": "그룹바구니 1", "ids": set()},
        }
    if "group_order" not in st.session_state:
        st.session_state.group_order = list(st.session_state.alternative_groups.keys())
    st.session_state.setdefault("next_group_index", len(st.session_state.group_order) + 1)
    # LLM 커스텀 기준 및 과목 태그 캐시
    st.session_state.setdefault("custom_criteria", [])
    st.session_state.setdefault("course_tags", {})

    if "controls" not in st.session_state:
        st.session_state.controls = default_controls()
    else:
        # 저장된 설정값이 오래된 형식이어도 현재 위젯 범위에 맞춰 보정한다.
        st.session_state.controls = sanitize_controls(st.session_state.controls)


def export_config() -> str:
    # 집합은 설정 파일로 바로 저장할 수 없으므로 목록으로 변환한다.
    from src.services.criteria_service import CustomCriterion
    data = {
        "preferred_ids": list(st.session_state.preferred_ids),
        "candidate_ids": list(st.session_state.candidate_ids),
        "excluded_ids": list(st.session_state.excluded_ids),
        "alternative_groups": {
            key: {"name": value["name"], "ids": list(value["ids"])}
            for key, value in st.session_state.alternative_groups.items()
        },
        "group_order": st.session_state.group_order,
        "next_group_index": st.session_state.next_group_index,
        "controls": st.session_state.controls,
        "custom_criteria": [
            c.to_dict() if isinstance(c, CustomCriterion) else c
            for c in st.session_state.get("custom_criteria", [])
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def import_config(json_str: str) -> None:
    try:
        data = json.loads(json_str)
        # 저장 파일의 목록 데이터를 다시 집합으로 복원해 중복 선택을 막는다.
        st.session_state.preferred_ids = set(data.get("preferred_ids", []))
        st.session_state.candidate_ids = set(data.get("candidate_ids", []))
        st.session_state.excluded_ids = set(data.get("excluded_ids", []))
        alt_groups = data.get("alternative_groups", {})
        st.session_state.alternative_groups = {
            key: {"name": value["name"], "ids": set(value["ids"])}
            for key, value in alt_groups.items()
        }
        st.session_state.group_order = data.get("group_order", list(st.session_state.alternative_groups.keys()))
        st.session_state.next_group_index = data.get("next_group_index", len(st.session_state.group_order) + 1)
        st.session_state.controls = sanitize_controls(data.get("controls"))
        # 커스텀 기준 복원
        from src.services.criteria_service import CustomCriterion
        st.session_state.custom_criteria = [
            CustomCriterion.from_dict(c) for c in data.get("custom_criteria", [])
        ]
        
        # UI 리렌더링을 위해 일부 캐시된 상태를 초기화할 수 있음
        if "candidates" in st.session_state:
            del st.session_state["candidates"]
            
        st.toast("설정이 성공적으로 불러와졌습니다!")
    except Exception as exc:
        st.error(f"설정을 불러오는 중 오류 발생: {exc}")


def group_keys() -> list[str]:
    return list(st.session_state.get("group_order", []))


def group_name_map() -> dict[str, str]:
    groups = st.session_state.get("alternative_groups", {})
    return {key: groups[key]["name"] for key in group_keys() if key in groups}


def add_group() -> None:
    index = st.session_state.next_group_index
    key = f"group_{index}"
    # 삭제된 그룹 번호를 재사용하지 않고 새 키를 만든다.
    st.session_state.next_group_index += 1
    st.session_state.alternative_groups[key] = {"name": f"그룹바구니 {index}", "ids": set()}
    st.session_state.group_order.append(key)


def delete_group(group_key: str) -> None:
    if group_key not in st.session_state.alternative_groups:
        return
    st.session_state.alternative_groups.pop(group_key, None)
    st.session_state.group_order = [key for key in st.session_state.group_order if key != group_key]


def reset_all_buckets() -> None:
    st.session_state.preferred_ids = set()
    st.session_state.candidate_ids = set()
    st.session_state.excluded_ids = set()
    for key in group_keys():
        st.session_state.alternative_groups[key]["ids"] = set()


def profile_grade_label(grade: str) -> str | None:
    if grade == "전체":
        return None
    return normalize_target_grade(grade)


def generation_filter_state(controls: dict) -> dict:
    grade_label = profile_grade_label(controls.get("grade", "전체"))
    department = controls.get("department", "전체")
    # 생성 탭은 수강대상 조건만 서비스 필터로 넘긴다.
    return {
        "target_grades": [grade_label] if grade_label else [],
        "target_departments": [department] if department and department != "전체" else [],
        "category_filters": [],
        "day_filters": [],
        "time_filter": "전체",
        "hide_foreign_only": False,
        "target_include_regex": "",
        "target_exclude_regex": "",
    }


def matches_filters(
    course: dict,
    category_filters: list[str],
    day_filters: list[str],
    time_filter: str,
    target_grades: list[str],
    target_departments: list[str],
    hide_foreign_only: bool,
    target_include_regex: str,
    target_exclude_regex: str,
) -> bool:
    return course_matches_filters(
        course,
        {
            "category_filters": category_filters,
            "day_filters": day_filters,
            "time_filter": time_filter,
            "target_grades": target_grades,
            "target_departments": target_departments,
            "hide_foreign_only": hide_foreign_only,
            "target_include_regex": target_include_regex,
            "target_exclude_regex": target_exclude_regex,
        },
    )


def search_courses(
    courses: list[dict],
    query: str,
    category_filters: list[str],
    day_filters: list[str],
    time_filter: str,
    target_grades: list[str],
    target_departments: list[str],
    hide_foreign_only: bool,
    target_include_regex: str,
    target_exclude_regex: str,
) -> list[dict]:
    keywords = [token.lower() for token in query.split() if token.strip()]
    results = []
    for course in courses:
        # 구조화 필터를 먼저 적용하고, 통과한 강의만 키워드 점수를 계산한다.
        if not matches_filters(
            course,
            category_filters,
            day_filters,
            time_filter,
            target_grades,
            target_departments,
            hide_foreign_only,
            target_include_regex,
            target_exclude_regex,
        ):
            continue
        score = search_score(course, keywords)
        if score <= 0:
            continue
        copied = dict(course)
        # 원본 강의 목록은 유지하고 화면용 점수만 복사본에 붙인다.
        copied["search_score"] = score
        results.append(copied)
    return sorted(results, key=lambda item: (-item["search_score"], item["name"]))


def update_bucket(course_id: str, bucket: str) -> None:
    basket = st.session_state.preferred_ids
    wish = st.session_state.candidate_ids
    excluded = st.session_state.excluded_ids
    # 한 과목은 장바구니/위시/제외 중 하나에만 들어갈 수 있다.
    basket.discard(course_id)
    wish.discard(course_id)
    excluded.discard(course_id)
    if bucket == "basket":
        basket.add(course_id)
    elif bucket == "wish":
        wish.add(course_id)
    elif bucket == "excluded":
        excluded.add(course_id)


def remove_from_bucket(course_id: str) -> None:
    st.session_state.preferred_ids.discard(course_id)
    st.session_state.candidate_ids.discard(course_id)
    st.session_state.excluded_ids.discard(course_id)


def add_to_group(course_id: str, group_key: str) -> None:
    for value in st.session_state.alternative_groups.values():
        # 같은 과목이 여러 대체 그룹에 동시에 들어가지 않게 한다.
        value["ids"].discard(course_id)
    if group_key in st.session_state.alternative_groups:
        st.session_state.alternative_groups[group_key]["ids"].add(course_id)


def remove_from_group(course_id: str, group_key: str) -> None:
    if group_key in st.session_state.alternative_groups:
        st.session_state.alternative_groups[group_key]["ids"].discard(course_id)


def clear_group(group_key: str) -> None:
    if group_key in st.session_state.alternative_groups:
        st.session_state.alternative_groups[group_key]["ids"] = set()


def bucket_label(course_id: str) -> str:
    if course_id in st.session_state.preferred_ids:
        return "장바구니"
    if course_id in st.session_state.candidate_ids:
        return "위시"
    if course_id in st.session_state.excluded_ids:
        return "제외"
    return "-"


def group_label(course_id: str) -> str:
    for value in st.session_state.alternative_groups.values():
        if course_id in value["ids"]:
            return f"그룹바구니({value['name']})"
    return "-"


def group_key_for_course(course_id: str) -> str:
    for key, value in st.session_state.alternative_groups.items():
        if course_id in value["ids"]:
            return key
    return "-"


def clear_course_selection(course_id: str) -> None:
    remove_from_bucket(course_id)
    for key in group_keys():
        remove_from_group(course_id, key)


def current_selection_value(course_id: str) -> str:
    if course_id in st.session_state.preferred_ids:
        return "basket"
    if course_id in st.session_state.candidate_ids:
        return "wish"
    if course_id in st.session_state.excluded_ids:
        return "exclude"
    group_key = group_key_for_course(course_id)
    if group_key != "-":
        # 선택상자 값에는 그룹 키를 포함해 어떤 그룹인지 보존한다.
        return f"group:{group_key}"
    return "none"


def selection_options() -> list[str]:
    return ["none", "basket", "wish", "exclude"] + [f"group:{key}" for key in group_keys()]


def selection_label(value: str) -> str:
    if value == "none":
        return "선택 안 함"
    if value == "basket":
        return "장바구니 (필수)"
    if value == "wish":
        return "위시 (후보)"
    if value == "exclude":
        return "제외"
    if value.startswith("group:"):
        key = value.split(":", 1)[1]
        return f"그룹바구니 · {group_name_map().get(key, key)}"
    return value


def selection_status_meta(course_id: str) -> tuple[str, str]:
    value = current_selection_value(course_id)
    if value == "basket":
        return "장바구니", "status-basket"
    if value == "wish":
        return "위시", "status-wish"
    if value == "exclude":
        return "제외", "status-exclude"
    if value.startswith("group:"):
        return selection_label(value), "status-group"
    return "선택 안 함", "status-none"


def apply_selection_from_widget(course_id: str, widget_key: str) -> None:
    value = st.session_state[widget_key]
    # 선택 변경 시 기존 버킷/그룹 소속을 먼저 모두 제거한다.
    clear_course_selection(course_id)
    if value == "basket":
        update_bucket(course_id, "basket")
    elif value == "wish":
        update_bucket(course_id, "wish")
    elif value == "exclude":
        update_bucket(course_id, "excluded")
    elif value.startswith("group:"):
        add_to_group(course_id, value.split(":", 1)[1])


def add_all_to_group_batch(results: list[dict], group_key: str) -> None:
    for course in results:
        add_to_group(course["course_id"], group_key)


def alternative_group_sets() -> list[set[str]]:
    return [set(st.session_state.alternative_groups[key]["ids"]) for key in group_keys() if st.session_state.alternative_groups[key]["ids"]]


def sync_group_name(group_key: str) -> None:
    st.session_state.alternative_groups[group_key]["name"] = st.session_state[f"name_{group_key}"]


def format_course_line(course: dict) -> str:
    return (
        f"{course['name']} ({course['course_id']}) | "
        f"{course['category_label']} | {course['credits']}학점 | "
        f"{course['professor']} | 대상 {course['target_raw']}"
    )


def render_course_meta(course: dict) -> str:
    # 카드에 필요한 주요 메타데이터만 추려 한 줄 요약 마크업을 만든다.
    grades = [grade for grade in ["1학년", "2학년", "3학년", "4학년"] if grade in course["target_raw"]]
    grade_text = ", ".join(grades) if grades else ("전체학년" if "전체학년" in course["target_raw"] else "-")
    time_lines = course["time_raw"].splitlines()
    first_line = time_lines[0] if time_lines else "-"
    time_text = first_line.split(" (")[0] if " (" in first_line else first_line
    location_text = first_line[first_line.find("(") + 1 : first_line.rfind(")")] if "(" in first_line and ")" in first_line else "-"
    total_hours = sum((meeting["end"] - meeting["start"]) for meeting in course.get("meetings", [])) / 60
    return f"""
    <div style="display:grid;grid-template-columns:0.8fr 0.8fr 1fr 1.8fr;gap:0.35rem;margin:0.35rem 0 0.3rem 0;">
      <div class="meta-box"><span class="meta-label">교수</span><span class="meta-value">{course['professor'] or '-'}</span></div>
      <div class="meta-box"><span class="meta-label">학년</span><span class="meta-value">{grade_text}</span></div>
      <div class="meta-box"><span class="meta-label">학점·시수</span><span class="meta-value">{course['credits']}학점 / {total_hours:.1f}시간</span></div>
      <div class="meta-box"><span class="meta-label">시간·장소</span><span class="meta-value">{time_text}<br>{location_text}</span></div>
    </div>
    """


def minute_to_text(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def timetable_bounds(courses: list[dict]) -> tuple[int, int]:
    starts = [int(meeting["start"]) for course in courses for meeting in course.get("meetings", [])]
    ends = [int(meeting["end"]) for course in courses for meeting in course.get("meetings", [])]
    if not starts or not ends:
        return 9 * 60, 18 * 60
    start = min(9 * 60, min(starts))
    end = max(18 * 60, max(ends))
    return (start // 30) * 30, ((end + 29) // 30) * 30


def course_color(course_id: str) -> str:
    palette = [
        "#e7f0ff",
        "#e8f6ee",
        "#fff3d6",
        "#fdebea",
        "#eef0fb",
        "#e4f4f7",
        "#f7ebf2",
        "#f1f4df",
    ]
    return palette[sum(ord(char) for char in course_id) % len(palette)]


def render_timetable_grid(courses: list[dict], rank: int | str | None = None) -> None:
    start_minute, end_minute = timetable_bounds(courses)
    slot_count = max(1, (end_minute - start_minute) // 30)
    rows = slot_count + 1

    parts = [
        (
            '<div class="timetable-grid" '
            f'style="grid-template-rows:2.25rem repeat({slot_count}, minmax(2.15rem, auto));">'
        ),
        '<div class="time-corner">시간</div>',
    ]
    for day_index, day in enumerate(DAY_ORDER, start=2):
        parts.append(f'<div class="day-header" style="grid-column:{day_index};grid-row:1;">{day}</div>')

    for slot in range(slot_count):
        minute = start_minute + slot * 30
        row = slot + 2
        if minute % 60 == 0:
            parts.append(
                f'<div class="time-label" style="grid-column:1;grid-row:{row};">{minute_to_text(minute)}</div>'
            )
        for day_index in range(2, len(DAY_ORDER) + 2):
            parts.append(
                f'<div class="time-cell" style="grid-column:{day_index};grid-row:{row};"></div>'
            )

    for course in courses:
        # Group meetings of this course by day to merge consecutive classes
        meetings_by_day = {}
        for m in course.get("meetings", []):
            day = m.get("day")
            if day not in DAY_ORDER:
                continue
            meetings_by_day.setdefault(day, []).append(m)

        for day, day_meetings in meetings_by_day.items():
            calculated = []
            for m in day_meetings:
                start = int(m["start"])
                end = int(m["end"])
                row_start = max(2, ((start - start_minute) // 30) + 2)
                row_end = min(rows + 1, ((end - start_minute + 29) // 30) + 2)
                if row_end <= row_start:
                    row_end = row_start + 1
                calculated.append({
                    "start": start,
                    "end": end,
                    "row_start": row_start,
                    "row_end": row_end,
                    "location": m.get("location") or "",
                })

            calculated.sort(key=lambda x: x["row_start"])

            merged = []
            for item in calculated:
                if not merged:
                    merged.append(item)
                else:
                    last = merged[-1]
                    # If consecutive / overlapping in row indexes
                    if item["row_start"] <= last["row_end"]:
                        last["row_end"] = max(last["row_end"], item["row_end"])
                        last["end"] = max(last["end"], item["end"])
                        last_loc = last["location"]
                        item_loc = item["location"]
                        if item_loc and item_loc != last_loc:
                            if last_loc:
                                last["location"] = f"{last_loc} / {item_loc}"
                            else:
                                last["location"] = item_loc
                    else:
                        merged.append(item)

            for m in merged:
                row_start = m["row_start"]
                row_end = m["row_end"]
                start = m["start"]
                end = m["end"]
                column = DAY_ORDER.index(day) + 2
                color = course_color(course["course_id"])
                professor = escape(str(course.get("professor") or "-"))
                name = escape(str(course.get("name") or ""))
                course_id = escape(str(course.get("course_id") or ""))
                location = escape(str(m["location"]))
                time_text = f"{minute_to_text(start)}-{minute_to_text(end)}"

                # X 버튼 추가 (rank가 지정되었을 때만)
                delete_btn_html = ""
                if rank is not None:
                    safe_course_id = re.sub(r"[^a-zA-Z0-9_-]", "_", str(course["course_id"]))
                    label = f"remove_course_{rank}_{safe_course_id}"
                    delete_btn_html = f'<span class="lecture-delete-btn" data-label="{label}" title="강의 제외">X</span>'

                parts.append(
                    (
                        '<div class="lecture-square" '
                        f'style="grid-column:{column};grid-row:{row_start}/{row_end};background:{color};" '
                        f'title="{name} {time_text}">'
                        f'{delete_btn_html}'
                        f'<strong>{name}</strong>'
                        f'<span>{professor} · {time_text}</span>'
                        f'<small>{course_id}{f" · {location}" if location else ""}</small>'
                        "</div>"
                    )
                )

    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def earliest_start_by_day(candidate: dict) -> dict[str, int]:
    starts: dict[str, int] = {}
    for course in candidate.get("courses", []):
        for meeting in course.get("meetings", []):
            day = meeting["day"]
            start = int(meeting["start"])
            if day not in starts or start < starts[day]:
                # 요일별 첫 수업 시간만 후보 요약에 표시한다.
                starts[day] = start
    return starts


def render_timetable(candidate: dict, alternative_groups: list[set[str]]) -> dict | None:
    removed_key = f"removed_candidate_{candidate['rank']}"
    removed_ids = set(st.session_state.get(removed_key, set()))
    courses = [course for course in candidate.get("courses", []) if course["course_id"] not in removed_ids]
    course_ids = {course["course_id"] for course in courses}

    satisfied_groups = sum(1 for group in alternative_groups if group.intersection(course_ids))
    day_starts = earliest_start_by_day({"courses": courses})
    start_summary = " · ".join(
        f"{day} {minute_to_text(day_starts[day])}" if day in day_starts else f"{day} -"
        for day in DAY_ORDER
    )
    st.subheader(f"후보 {candidate['rank']}")
    st.markdown(
        f"""
        점수 `{candidate['score']:.1f}` | 학점 `{candidate['total_credits']:.1f}` |
        공강일 `{candidate['free_days']}`일 | 애매한 공강 `{candidate['gap_count']}`개 | 그룹 `{satisfied_groups}/{len(alternative_groups)}`
        """
    )
    st.caption(f"요일별 첫 수업: {start_summary}")
    render_timetable_grid(courses, rank=candidate['rank'])

    # 실제로는 CSS에 의해 화면에 보이지 않는 (hidden) 버튼들을 렌더링합니다.
    # 이 버튼들은 각 블록 안의 HTML X 버튼이 자바스크립트로 클릭할 대상입니다.
    if courses:
        for course in courses:
            safe_course_id = re.sub(r"[^a-zA-Z0-9_-]", "_", str(course["course_id"]))
            label = f"remove_course_{candidate['rank']}_{safe_course_id}"
            if st.button(
                label,
                key=label,
            ):
                removed_ids.add(course["course_id"])
                st.session_state[removed_key] = removed_ids
                update_bucket(course["course_id"], "excluded")
                st.rerun()

    # 이벤트 위임(Event Delegation)을 사용하여 React의 DOM 요소 재사용 시 리스너 소실 문제를 해결합니다.
    # 또한 iframe 재현 시점마다 기존 리스너를 정리(Clean up)하여 데드 레퍼런스와 중복 등록을 방지합니다.
    js_code = """
    <script>
    (function() {
        const doc = window.parent.document;
        const parentWin = window.parent;
        
        // 이전 실행에서 등록된 리스너가 있다면 정리
        if (parentWin._timetableDeleteListener) {
            doc.removeEventListener('click', parentWin._timetableDeleteListener);
        }
        
        // 새로운 리스너 정의 및 등록
        parentWin._timetableDeleteListener = (e) => {
            const btn = e.target.closest('.lecture-delete-btn');
            if (btn) {
                e.preventDefault();
                e.stopPropagation();
                const label = btn.getAttribute('data-label');
                console.log('JS: Event delegation clicked delete button for label:', label);
                const xpath = `//button[normalize-space()="${label}"]`;
                const hiddenBtn = doc.evaluate(xpath, doc, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                console.log('JS: found hidden button:', hiddenBtn);
                if (hiddenBtn) {
                    hiddenBtn.click();
                }
            }
        };
        
        doc.addEventListener('click', parentWin._timetableDeleteListener);
    })();
    </script>
    """
    st.components.v1.html(js_code, height=0, width=0)

    st.caption("시간표 칸의 X를 누르면 해당 강의가 제외됩니다. 재생성 시 남은 강의는 고정됩니다.")
    if not courses:
        st.caption("삭제할 강의가 없습니다.")

    if st.button("재생성", key=f"regen_candidate_{candidate['rank']}", use_container_width=True):
        return {"locked_ids": set(course_ids), "excluded_ids": set(removed_ids)}
    return None


def has_internal_conflict(courses: list[dict]) -> bool:
    for index, left in enumerate(courses):
        for right in courses[index + 1 :]:
            for a in left["meetings"]:
                for b in right["meetings"]:
                    # 같은 요일에서 두 강의 시간이 겹치면 내부 충돌로 본다.
                    if a["day"] == b["day"] and a["start"] < b["end"] and b["start"] < a["end"]:
                        return True
    return False


def result_frame(results: list[dict]):
    import pandas as pd

    rows = []
    for course in results[:100]:
        # 표 렌더링은 너무 길어지지 않도록 상위 100개만 표시한다.
        rows.append(
            {
                "상태": bucket_label(course["course_id"]),
                "그룹": group_label(course["course_id"]),
                "점수": course["search_score"],
                "과목명": course["name"],
                "과목번호": course["course_id"],
                "이수구분": course["category_label"],
                "교수명": course["professor"],
                "학점": course["credits"],
                "강의시간": course["time_raw"],
                "수강대상": course["target_raw"],
            }
        )
    return pd.DataFrame(rows)


def target_departments(courses: list[dict]) -> list[str]:
    departments = set()
    for course in courses:
        departments.update(extract_target_departments(course["target_raw"]))
    return sorted(departments)


def highlight_target_text(course: dict, filter_state: dict) -> str:
    text = course.get("target_raw", "") or "수강대상 정보 없음"
    highlights = []
    
    target_grades = filter_state.get("target_grades", [])
    target_departments = filter_state.get("target_departments", [])
    hide_foreign_only = filter_state.get("hide_foreign_only", False)
    target_include_regex = filter_state.get("target_include_regex", "")

    # 현재 필터와 일치한 수강대상 토큰만 강조 대상으로 모은다.
    for grade in target_grades:
        if grade in text:
            highlights.append(grade)
    for dept in target_departments:
        if dept in text or is_open_department_target(text):
            highlights.append(dept if dept in text else "전체 허용")
    if hide_foreign_only and has_foreign_marker(text):
        highlights.append("외국인/교환학생")
    if target_include_regex:
        try:
            for match in re.finditer(target_include_regex, text):
                highlights.append(match.group(0))
        except re.error:
            pass
    unique = []
    for item in highlights:
        if item and item not in unique:
            unique.append(item)
    rendered = text
    for item in sorted(unique, key=len, reverse=True):
        # 긴 토큰부터 치환해 짧은 단어가 먼저 겹쳐 표시되는 문제를 줄인다.
        rendered = rendered.replace(item, f"<mark>{item}</mark>")
    return rendered


def target_badges(course: dict) -> list[str]:
    text = course["target_raw"]
    parts: list[str] = []
    if "전체학년" in text:
        parts.append("전체학년")
    elif "전체" in text:
        parts.append("전체")
    parts.extend([grade for grade in ["1학년", "2학년", "3학년", "4학년"] if grade in text])
    parts.extend(sorted(extract_target_departments(text)))
    parts.extend(sorted(extract_excluded_departments(text)))
    for token in ["대상외수강제한", "순수외국인입학생", "교환학생", "외국인", "중국국적학생"]:
        if token in text:
            parts.append(token)
    unique: list[str] = []
    for part in parts:
        if part and part not in unique:
            unique.append(part)
    return unique[:6]


def matched_target_pills(course: dict, filter_state: dict) -> list[str]:
    pills: list[str] = []
    text = course.get("target_raw", "")
    target_grades = filter_state.get("target_grades", [])
    target_departments = filter_state.get("target_departments", [])
    target_include_regex = filter_state.get("target_include_regex", "")

    for grade in target_grades:
        if grade in text or ("전체학년" in text and grade.endswith("학년")):
            pills.append(grade)
    for dept in target_departments:
        if dept in text:
            pills.append(dept)
    if target_include_regex:
        try:
            pills.extend(match.group(0) for match in re.finditer(target_include_regex, text))
        except re.error:
            pass
    unique: list[str] = []
    for pill in pills:
        if pill and pill not in unique:
            unique.append(pill)
    return unique[:6]


def matched_rule_text(course: dict, filter_state: dict) -> str:
    matched: list[str] = []
    text = course.get("target_raw", "")
    target_grades = filter_state.get("target_grades", [])
    target_departments = filter_state.get("target_departments", [])
    target_include_regex = filter_state.get("target_include_regex", "")

    for grade in target_grades:
        if grade in text or ("전체학년" in text and grade.endswith("학년")):
            matched.append(grade)
    for dept in target_departments:
        if dept in text:
            matched.append(dept)
        elif is_open_department_target(text):
            matched.append("전체/전체학년")
    if target_include_regex and regex_match(text, target_include_regex):
        matched.append("정규식 포함")
    unique: list[str] = []
    for item in matched:
        if item and item not in unique:
            unique.append(item)
    return ", ".join(unique)


def render_pills(pills: list[str], highlight: list[str] | None = None) -> str:
    highlight = highlight or []
    chunks = []
    for pill in pills:
        css = "pill highlight" if pill in highlight else "pill"
        chunks.append(f'<span class="{css}">{pill}</span>')
    return "".join(chunks)
