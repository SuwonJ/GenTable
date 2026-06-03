"""과목 클러스터링 & 스마트 그룹 추천 서비스.

태그의 Jaccard 유사도를 기반으로 과목 간 유사도를 계산하고,
유사 과목 추천 및 대체 그룹 자동 생성을 지원합니다.

수학적 근거:
  Jaccard Similarity J(A,B) = |A ∩ B| / |A ∪ B|
  - 0 = 완전히 다름, 1 = 완전히 동일
  - 정보 검색(IR)의 정통 집합 유사도 지표
"""

from __future__ import annotations

from collections import defaultdict


# 유사도 계산

def jaccard_similarity(tags_a: set[str], tags_b: set[str]) -> float:
    """두 태그 집합의 Jaccard 유사도를 계산합니다.

    J(A, B) = |A ∩ B| / |A ∪ B|

    Parameters
    ----------
    tags_a, tags_b : set[str]
        비교할 두 태그 집합.

    Returns
    -------
    float
        0.0 ~ 1.0 사이의 유사도.
    """
    if not tags_a and not tags_b:
        return 0.0
    intersection = tags_a & tags_b
    union = tags_a | tags_b
    return len(intersection) / len(union)


def compute_similarity_matrix(
    course_tags: dict[str, list[str]],
) -> dict[str, dict[str, float]]:
    """모든 과목 쌍의 유사도를 계산합니다.

    Returns
    -------
    dict[str, dict[str, float]]
        course_id → {other_id → similarity} 매핑.
    """
    ids = list(course_tags.keys())
    tag_sets = {cid: set(tags) for cid, tags in course_tags.items()}

    matrix: dict[str, dict[str, float]] = defaultdict(dict)

    for i, id_a in enumerate(ids):
        for j in range(i + 1, len(ids)):
            id_b = ids[j]
            sim = jaccard_similarity(tag_sets[id_a], tag_sets[id_b])
            if sim > 0:
                matrix[id_a][id_b] = sim
                matrix[id_b][id_a] = sim

    return dict(matrix)


# 유사 과목 추천

def find_similar_courses(
    course_id: str,
    course_tags: dict[str, list[str]],
    catalog: dict,
    *,
    top_n: int = 5,
    min_similarity: float = 0.25,
) -> list[dict]:
    """특정 과목과 유사한 과목을 추천합니다.

    Parameters
    ----------
    course_id : str
        기준 과목 ID.
    course_tags : dict
        전체 과목 태그 매핑.
    catalog : dict
        과목 카탈로그 (course_id → course_dict).
    top_n : int
        반환할 최대 추천 수.
    min_similarity : float
        최소 유사도 임계값.

    Returns
    -------
    list[dict]
        유사 과목 정보 리스트. 각 dict는:
        - course_id: str
        - name: str
        - similarity: float
        - shared_tags: list[str]
        - course: dict (원본 과목 데이터)
    """
    if course_id not in course_tags:
        return []

    target_tags = set(course_tags[course_id])
    if not target_tags:
        return []

    similarities = []
    for other_id, other_tag_list in course_tags.items():
        if other_id == course_id:
            continue
        if other_id not in catalog:
            continue

        other_tags = set(other_tag_list)
        sim = jaccard_similarity(target_tags, other_tags)

        if sim >= min_similarity:
            shared = sorted(target_tags & other_tags)
            similarities.append({
                "course_id": other_id,
                "name": catalog[other_id].get("name", catalog[other_id].get("과목명", "")),
                "similarity": round(sim, 3),
                "shared_tags": shared,
                "course": catalog[other_id],
            })

    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    return similarities[:top_n]


# 스마트 그룹 추천

def suggest_alternative_groups(
    course_tags: dict[str, list[str]],
    catalog: dict,
    *,
    min_group_size: int = 2,
    max_group_size: int = 5,
    similarity_threshold: float = 0.5,
) -> list[dict]:
    """태그 유사도 기반으로 대체 그룹을 자동 제안합니다.

    높은 유사도를 가진 과목들을 클러스터링하여 그룹을 형성합니다.
    탐욕(greedy) 방식으로 가장 유사한 쌍부터 그룹에 추가합니다.

    Parameters
    ----------
    course_tags : dict
        전체 과목 태그 매핑.
    catalog : dict
        과목 카탈로그.
    min_group_size : int
        최소 그룹 크기.
    max_group_size : int
        최대 그룹 크기.
    similarity_threshold : float
        그룹 형성 최소 유사도.

    Returns
    -------
    list[dict]
        제안 그룹 리스트. 각 dict는:
        - courses: list[str] (과목 ID 리스트)
        - names: list[str] (과목명 리스트)
        - common_tags: list[str] (공통 태그)
        - avg_similarity: float (그룹 내 평균 유사도)
    """
    tag_sets = {cid: set(tags) for cid, tags in course_tags.items() if tags}

    # 유사도가 높은 쌍 수집
    pairs: list[tuple[float, str, str]] = []
    ids = [cid for cid in tag_sets if cid in catalog]

    for i, id_a in enumerate(ids):
        for j in range(i + 1, len(ids)):
            id_b = ids[j]
            sim = jaccard_similarity(tag_sets[id_a], tag_sets[id_b])
            if sim >= similarity_threshold:
                pairs.append((sim, id_a, id_b))

    pairs.sort(reverse=True)

    # 탐욕적 그룹 형성
    assigned: set[str] = set()
    groups: list[dict] = []

    for sim, id_a, id_b in pairs:
        if id_a in assigned or id_b in assigned:
            continue

        group_ids = [id_a, id_b]
        assigned.add(id_a)
        assigned.add(id_b)

        # 그룹 확장: 두 과목 모두와 유사한 과목 추가
        group_tags = tag_sets[id_a] & tag_sets[id_b]

        for other_id in ids:
            if other_id in assigned or len(group_ids) >= max_group_size:
                break
            other_tags = tag_sets.get(other_id, set())
            # 그룹 내 모든 과목과의 평균 유사도 확인
            avg_sim = sum(
                jaccard_similarity(tag_sets[gid], other_tags) for gid in group_ids
            ) / len(group_ids)
            if avg_sim >= similarity_threshold:
                group_ids.append(other_id)
                assigned.add(other_id)
                group_tags &= other_tags

        if len(group_ids) >= min_group_size:
            # 그룹 내 평균 유사도 계산
            pair_sims = []
            for i, ga in enumerate(group_ids):
                for j in range(i + 1, len(group_ids)):
                    gb = group_ids[j]
                    pair_sims.append(jaccard_similarity(tag_sets[ga], tag_sets[gb]))
            avg_similarity = sum(pair_sims) / len(pair_sims) if pair_sims else 0

            groups.append({
                "courses": group_ids,
                "names": [catalog[cid].get("name", catalog[cid].get("과목명", cid)) for cid in group_ids],
                "common_tags": sorted(group_tags),
                "avg_similarity": round(avg_similarity, 3),
            })

    groups.sort(key=lambda g: g["avg_similarity"], reverse=True)
    return groups


# 태그 통계

def get_tag_statistics(course_tags: dict[str, list[str]]) -> dict[str, int]:
    """태그별 과목 수 통계를 반환합니다.

    Returns
    -------
    dict[str, int]
        태그 → 해당 태그를 가진 과목 수.
    """
    stats: dict[str, int] = defaultdict(int)
    for tag_list in course_tags.values():
        for tag in tag_list:
            stats[tag] += 1
    return dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))


def get_courses_by_tag(
    tag: str,
    course_tags: dict[str, list[str]],
    catalog: dict,
) -> list[dict]:
    """특정 태그를 가진 모든 과목을 반환합니다."""
    result = []
    for cid, tags in course_tags.items():
        if tag in tags and cid in catalog:
            result.append(catalog[cid])
    return result
