"""자연어 커스텀 스코어링 기준 서비스.

사용자의 자연어 요청("점심시간 비워줘", "수학 싫어")을 구조화된
스코어링 기준으로 변환하고, 시간표 후보에 대해 점수를 계산합니다.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

logger = logging.getLogger(__name__)

# Data Model

@dataclass(frozen=True)
class CustomCriterion:
    """하나의 커스텀 스코어링 기준.

    Attributes
    ----------
    type : str
        기준 타입 (free_time_block, penalize_tag 등).
    label : str
        사용자 친화적 레이블 (UI 표시용).
    params : dict
        타입별 파라미터.
    weight : float
        스코어 반영 가중치 (기본값 30).
    """

    type: str
    label: str
    params: dict
    weight: float = 30.0

    def to_dict(self) -> dict:
        """직렬화용 dict 반환."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CustomCriterion:
        """dict에서 복원."""
        return cls(
            type=data["type"],
            label=data["label"],
            params=data["params"],
            weight=data.get("weight", 30.0),
        )


# 기준 타입 정의

CRITERION_TYPES = {
    "free_time_block": {"icon": "🕐"},
    "avoid_time_range": {"icon": "🚫"},
    "prefer_time_range": {"icon": "⏰"},
    "max_consecutive": {"icon": "⏱️"},
    "penalize_tag": {"icon": "👎"},
    "boost_tag": {"icon": "👍"},
}


# LLM 파싱

_PARSE_PROMPT = """\
당신은 대학 시간표 생성기의 기준 파서입니다.
사용자의 자연어 요청을 아래 기준 타입 중 **정확히 하나**로 변환하세요.

## 사용 가능한 과목 태그
{available_tags}

## 기준 타입

1. **free_time_block** — 특정 시간대를 비워둠
   params: {{"days": ["월","화",...], "start": "HH:MM", "end": "HH:MM"}}

2. **avoid_time_range** — 특정 시간대 수업 회피
   params: {{"days": ["월","화",...], "start": "HH:MM", "end": "HH:MM"}}

3. **prefer_time_range** — 특정 시간대에만 수업 선호
   params: {{"days": ["월","화",...], "start": "HH:MM", "end": "HH:MM"}}

4. **max_consecutive** — 연강 시간 제한
   params: {{"max_minutes": 정수}}

5. **penalize_tag** — 특정 태그 과목 회피 (싫어하는 분야)
   params: {{"tag": "태그명"}}

6. **boost_tag** — 특정 태그 과목 선호 (좋아하는 분야)
   params: {{"tag": "태그명"}}

## 규칙
- days를 특별히 지정하지 않으면 모든 요일: ["월","화","수","목","금"]
- 시간은 24시간제 HH:MM 형식
- 점심시간 = 보통 12:00~13:00
- tag는 반드시 위의 "사용 가능한 과목 태그" 중에서 선택
- label은 사용자 친화적인 한국어 설명 (이모지 포함)

## 예시

입력: "점심시간 비워줘"
출력: {{"type":"free_time_block","label":"🕐 점심시간 확보 (12:00-13:00)","params":{{"days":["월","화","수","목","금"],"start":"12:00","end":"13:00"}}}}

입력: "수학 싫어"
출력: {{"type":"penalize_tag","label":"👎 수학 과목 회피","params":{{"tag":"수학"}}}}

입력: "화목은 오후에만 수업"
출력: {{"type":"prefer_time_range","label":"⏰ 화목 오후만 수업 (13:00-21:00)","params":{{"days":["화","목"],"start":"13:00","end":"21:00"}}}}

입력: "연강 2시간 넘기지 마"
출력: {{"type":"max_consecutive","label":"⏱️ 연강 2시간 제한","params":{{"max_minutes":120}}}}

입력: "프로그래밍 수업 많이 넣어줘"
출력: {{"type":"boost_tag","label":"👍 프로그래밍 과목 선호","params":{{"tag":"프로그래밍"}}}}

## 사용자 입력
"{user_input}"

**JSON만 응답하세요.**
"""


from src.services.tagging_service import _extract_json


def parse_criterion(
    user_input: str,
    api_key: str,
    available_tags: list[str],
    *,
    model_name: str = "gemini-2.5-flash",
) -> CustomCriterion:
    """자연어 입력을 구조화된 기준으로 변환합니다.

    Parameters
    ----------
    user_input : str
        사용자의 자연어 요청.
    api_key : str
        Gemini API 키.
    available_tags : list[str]
        사용 가능한 과목 태그 목록.

    Returns
    -------
    CustomCriterion
        파싱된 스코어링 기준.

    Raises
    ------
    ValueError
        파싱 실패 시.
    """
    import time
    from google import genai

    client = genai.Client(api_key=api_key)

    prompt = _PARSE_PROMPT.format(
        available_tags=", ".join(available_tags) if available_tags else "(태깅 미완료)",
        user_input=user_input,
    )

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.1,
                },
            )
            parsed = _extract_json(response.text)
            break
        except Exception as e:
            error_str = str(e)
            if ("429" in error_str or "RESOURCE_EXHAUSTED" in error_str) and attempt < 2:
                time.sleep(30 * (attempt + 1))
                continue
            raise ValueError(f"LLM 파싱 실패: {e}") from e

    ctype = parsed.get("type", "")
    if ctype not in CRITERION_TYPES:
        raise ValueError(f"알 수 없는 기준 타입: {ctype}")

    return CustomCriterion(
        type=ctype,
        label=parsed.get("label", f"{CRITERION_TYPES[ctype]['icon']} {user_input}"),
        params=parsed.get("params", {}),
        weight=parsed.get("weight", 30.0),
    )


# 기준 평가

from src.ingestion import to_minutes as _time_to_minutes


def _get_daily_slots(courses: list[dict]) -> dict[str, list[dict]]:
    """요일별 수업 슬롯 분류."""
    daily: dict[str, list[dict]] = {}
    for c in courses:
        for m in c.get("meetings", []):
            day = m["day"]
            daily.setdefault(day, []).append(m)
    return daily


def _eval_free_time_block(criterion: CustomCriterion, courses: list[dict]) -> float:
    """지정 시간대가 비어있으면 보너스, 겹치면 페널티."""
    days = criterion.params.get("days", ["월", "화", "수", "목", "금"])
    start = _time_to_minutes(criterion.params["start"])
    end = _time_to_minutes(criterion.params["end"])

    violations = 0

    for day in days:
        for c in courses:
            for m in c.get("meetings", []):
                if m["day"] == day and m["start"] < end and m["end"] > start:
                    violations += 1

    if violations == 0:
        return criterion.weight  # 완전히 비었으면 보너스
    return -criterion.weight * violations  # 겹칠 때마다 페널티


def _eval_avoid_time_range(criterion: CustomCriterion, courses: list[dict]) -> float:
    """지정 시간대에 수업이 있으면 페널티."""
    days = criterion.params.get("days", ["월", "화", "수", "목", "금"])
    start = _time_to_minutes(criterion.params["start"])
    end = _time_to_minutes(criterion.params["end"])

    penalty = 0
    for c in courses:
        for m in c.get("meetings", []):
            if m["day"] in days and m["start"] < end and m["end"] > start:
                penalty += 1

    return -criterion.weight * penalty


def _eval_prefer_time_range(criterion: CustomCriterion, courses: list[dict]) -> float:
    """지정 시간대 밖에 수업이 있으면 페널티."""
    days = criterion.params.get("days", ["월", "화", "수", "목", "금"])
    start = _time_to_minutes(criterion.params["start"])
    end = _time_to_minutes(criterion.params["end"])

    outside_count = 0
    for c in courses:
        for m in c.get("meetings", []):
            if m["day"] in days:
                if m["start"] < start or m["end"] > end:
                    outside_count += 1

    return -criterion.weight * outside_count


def _eval_max_consecutive(criterion: CustomCriterion, courses: list[dict]) -> float:
    """연강이 제한 시간을 초과하면 페널티."""
    max_minutes = criterion.params.get("max_minutes", 180)
    daily = _get_daily_slots(courses)
    total_penalty = 0.0

    for day, slots in daily.items():
        sorted_slots = sorted(slots, key=lambda s: s["start"])
        consecutive = 0

        for i, slot in enumerate(sorted_slots):
            duration = slot["end"] - slot["start"]
            if i == 0:
                consecutive = duration
            else:
                gap = slot["start"] - sorted_slots[i - 1]["end"]
                if gap <= 15:  # 15분 이내 간격은 연강으로 취급
                    consecutive += duration
                else:
                    consecutive = duration

            if consecutive > max_minutes:
                excess = consecutive - max_minutes
                total_penalty += excess / 60.0

    return -criterion.weight * total_penalty


def _eval_penalize_tag(
    criterion: CustomCriterion,
    courses: list[dict],
    course_tags: dict[str, list[str]],
) -> float:
    """특정 태그를 가진 과목 수에 비례하여 페널티."""
    tag = criterion.params.get("tag", "")
    if not tag:
        return 0.0

    count = 0
    for c in courses:
        cid = str(c.get("course_id", ""))
        tags = course_tags.get(cid, [])
        if tag in tags:
            count += 1

    return -criterion.weight * count


def _eval_boost_tag(
    criterion: CustomCriterion,
    courses: list[dict],
    course_tags: dict[str, list[str]],
) -> float:
    """특정 태그를 가진 과목 수에 비례하여 보너스."""
    tag = criterion.params.get("tag", "")
    if not tag:
        return 0.0

    count = 0
    for c in courses:
        cid = str(c.get("course_id", ""))
        tags = course_tags.get(cid, [])
        if tag in tags:
            count += 1

    return criterion.weight * count


_EVALUATORS = {
    "free_time_block": _eval_free_time_block,
    "avoid_time_range": _eval_avoid_time_range,
    "prefer_time_range": _eval_prefer_time_range,
    "max_consecutive": _eval_max_consecutive,
    "penalize_tag": _eval_penalize_tag,
    "boost_tag": _eval_boost_tag,
}


def evaluate_criterion(
    criterion: CustomCriterion,
    courses: list[dict],
    course_tags: dict[str, list[str]] | None = None,
) -> float:
    """단일 기준에 대한 점수를 계산합니다.

    Parameters
    ----------
    criterion : CustomCriterion
        평가할 기준.
    courses : list[dict]
        시간표 내 과목 리스트 (raw dict).
    course_tags : dict, optional
        과목 ID → 태그 매핑 (태그 기반 기준에 필요).

    Returns
    -------
    float
        기준에 따른 보너스(양수) 또는 페널티(음수).
    """
    evaluator = _EVALUATORS.get(criterion.type)
    if evaluator is None:
        logger.warning("알 수 없는 기준 타입: %s", criterion.type)
        return 0.0

    # 태그 기반 기준은 course_tags 필요
    if criterion.type in ("penalize_tag", "boost_tag"):
        return evaluator(criterion, courses, course_tags or {})
    return evaluator(criterion, courses)


def evaluate_all_criteria(
    criteria: list[CustomCriterion],
    courses: list[dict],
    course_tags: dict[str, list[str]] | None = None,
) -> float:
    """모든 커스텀 기준의 점수 합계를 반환합니다."""
    return sum(evaluate_criterion(c, courses, course_tags) for c in criteria)
