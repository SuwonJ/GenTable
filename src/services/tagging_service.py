"""LLM 기반 과목 태깅 서비스.

대학 과목 데이터를 Gemini API로 태깅하고 결과를 캐싱합니다.
태깅 결과는 커스텀 기준(criteria_service)과 클러스터링(clustering_service)의
공유 기반으로 사용됩니다.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_PATH = Path("sourcedata/course_tags.json")
BATCH_SIZE = 25
MAX_RETRIES = 3
RETRY_BASE_DELAY = 30  # 초

# Cache I/O

def load_tag_cache() -> dict[str, list[str]]:
    """캐시 파일에서 태그 데이터를 로드합니다."""
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("태그 캐시 로드 실패, 새로 생성합니다: %s", e)
    return {}


def save_tag_cache(tags: dict[str, list[str]]) -> None:
    """태그 데이터를 캐시 파일에 저장합니다."""
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(tags, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("태그 캐시 저장 실패 (배포 환경 권한 오류 등): %s", e)


# LLM Tagging

_TAGGING_PROMPT = """\
아래 대학 과목들에 태그를 붙여주세요.
각 과목에 1~4개의 **한국어 태그**를 부여합니다.
태그는 과목의 학문 분야, 핵심 기술, 성격을 간결하게 나타내야 합니다.

태그 예시:
- "미적분학및연습" → ["수학", "이론"]
- "자료구조" → ["프로그래밍", "CS기초", "알고리즘"]
- "영어커뮤니케이션" → ["영어", "소통"]
- "경영학원론" → ["경영", "이론"]
- "체육1" → ["체육", "실기"]
- "한국사" → ["역사", "인문학"]
- "선형대수학" → ["수학", "이론"]
- "운영체제" → ["프로그래밍", "시스템", "CS심화"]
- "글쓰기" → ["글쓰기", "인문학"]
- "확률과통계" → ["수학", "통계", "이론"]
- "인공지능" → ["AI", "프로그래밍", "CS심화"]

과목 목록:
{courses_json}

**JSON만 응답하세요**. 형식: {{"과목ID": ["태그1", "태그2"], ...}}
"""


def _build_tagging_prompt(courses: list[dict[str, str]]) -> str:
    """태깅 요청 프롬프트를 구성합니다."""
    items = []
    for c in courses:
        items.append({
            "id": c["id"],
            "name": c["name"],
            "category": c.get("category", ""),
            "area": c.get("area", ""),
        })
    return _TAGGING_PROMPT.format(courses_json=json.dumps(items, ensure_ascii=False))


def _extract_json(text: str) -> dict:
    """LLM 응답에서 JSON을 추출합니다. 코드 블록도 처리."""
    # markdown 코드 블록 제거
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.strip()
    return json.loads(cleaned)


def _call_gemini_with_retry(client, model_name: str, prompt: str) -> str:
    """Rate limit 자동 재시도로 Gemini API를 호출합니다."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.2,
                },
            )
            return response.text
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                wait = RETRY_BASE_DELAY * (attempt + 1)
                logger.warning(
                    "Rate limit (시도 %d/%d), %d초 대기 후 재시도...",
                    attempt + 1, MAX_RETRIES, wait,
                )
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Gemini API {MAX_RETRIES}회 재시도 후에도 실패")


def tag_courses_batch(
    courses: list[dict[str, str]],
    api_key: str,
    *,
    model_name: str = "gemini-2.5-flash",
    progress_callback=None,
) -> dict[str, list[str]]:
    """과목 리스트를 배치로 LLM에 태깅 요청합니다.

    Parameters
    ----------
    courses : list[dict]
        태깅할 과목 목록. 각 dict는 id, name, category, area 키를 가짐.
    api_key : str
        Gemini API 키.
    model_name : str
        사용할 Gemini 모델명.
    progress_callback : callable, optional
        진행률 콜백. (current, total) 형태로 호출됨.

    Returns
    -------
    dict[str, list[str]]
        과목 ID → 태그 리스트 매핑.
    """
    from google import genai

    client = genai.Client(api_key=api_key)

    result: dict[str, list[str]] = {}
    total = len(courses)

    for i in range(0, total, BATCH_SIZE):
        batch = courses[i : i + BATCH_SIZE]
        prompt = _build_tagging_prompt(batch)

        try:
            text = _call_gemini_with_retry(client, model_name, prompt)
            parsed = _extract_json(text)
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    if isinstance(v, list):
                        result[k] = [str(tag) for tag in v]
        except Exception as e:
            logger.error("태깅 배치 %d 실패: %s", i // BATCH_SIZE, e)
            # 실패한 배치의 과목에 빈 태그 할당
            for c in batch:
                result.setdefault(c["id"], [])

        if progress_callback:
            progress_callback(min(i + BATCH_SIZE, total), total)

    return result


# Public API

def _catalog_to_tagging_input(catalog: dict) -> list[dict[str, str]]:
    """카탈로그 dict를 태깅 입력 형식으로 변환합니다."""
    items = []
    for cid, course in catalog.items():
        items.append({
            "id": str(cid),
            "name": course.get("name", ""),
            "category": course.get("category_label", course.get("category", "")),
            "area": course.get("area", ""),
        })
    return items


def ensure_tags(
    catalog: dict,
    api_key: str,
    *,
    force: bool = False,
    progress_callback=None,
) -> dict[str, list[str]]:
    """태그가 캐시에 있으면 로드하고, 없으면 LLM으로 태깅합니다.

    Parameters
    ----------
    catalog : dict
        과목 카탈로그 (course_id → course_dict).
    api_key : str
        Gemini API 키.
    force : bool
        True이면 캐시를 무시하고 전체 재태깅.
    progress_callback : callable, optional
        진행률 콜백. (current, total) 형태로 호출됨.

    Returns
    -------
    dict[str, list[str]]
        과목 ID → 태그 리스트 매핑.
    """
    cache = {} if force else load_tag_cache()

    # 아직 태깅되지 않은 과목 또는 빈 태그인 과목 찾기
    all_items = _catalog_to_tagging_input(catalog)
    untagged = [
        item for item in all_items
        if item["id"] not in cache or not cache.get(item["id"])
    ]

    if not untagged:
        logger.info("모든 과목이 이미 태깅됨 (%d개)", len(cache))
        return cache

    logger.info("태깅 필요: %d / %d 과목", len(untagged), len(all_items))

    new_tags = tag_courses_batch(untagged, api_key, progress_callback=progress_callback)

    cache.update(new_tags)
    save_tag_cache(cache)

    logger.info("태깅 완료. 총 %d개 과목 태그 캐시됨", len(cache))
    return cache


def get_all_unique_tags(course_tags: dict[str, list[str]]) -> list[str]:
    """모든 고유 태그를 정렬하여 반환합니다."""
    tags: set[str] = set()
    for tag_list in course_tags.values():
        tags.update(tag_list)
    return sorted(tags)
