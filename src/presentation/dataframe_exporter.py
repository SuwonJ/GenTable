from __future__ import annotations

from src.domain.models import DAY_ORDER


def timetable_to_frame(courses: list[dict]):
    import pandas as pd

    starts = [meeting["start"] for course in courses for meeting in course["meetings"]]
    ends = [meeting["end"] for course in courses for meeting in course["meetings"]]
    if not starts or not ends:
        # 표시할 강의가 없을 때도 화면 표 컬럼은 유지한다.
        return pd.DataFrame(columns=["시간"] + DAY_ORDER)

    # 실제 강의가 있는 시간 범위만 행으로 만든다.
    min_hour = min(starts) // 60
    max_hour = (max(ends) + 59) // 60
    rows = []
    for hour in range(min_hour, max_hour):
        row = {"시간": f"{hour:02d}:00"}
        for day in DAY_ORDER:
            # 요일별 빈 칸을 먼저 만든 뒤 강의명으로 채운다.
            row[day] = ""
        rows.append(row)

    for course in courses:
        for meeting in course["meetings"]:
            # 30분 단위 강의도 한 시간 칸 전체에 보이도록 올림 처리한다.
            start_hour = meeting["start"] // 60
            end_hour = (meeting["end"] + 59) // 60
            for hour in range(start_hour, end_hour):
                row = next(item for item in rows if item["시간"] == f"{hour:02d}:00")
                # 셀에는 사용자가 구분하기 쉬운 과목명과 교수명을 함께 표시한다.
                row[meeting["day"]] = f"{course['name']}\n{course['professor']}"

    return pd.DataFrame(rows)
